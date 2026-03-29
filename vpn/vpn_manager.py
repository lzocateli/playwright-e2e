"""VPN Manager para conexão WireGuard/Mullvad durante testes E2E.

Gerencia conexões WireGuard usando wg-quick, com suporte a:
- Conexão a locais específicos ou aleatórios
- Rotação de VPN entre testes
- Verificação de IP público via Mullvad API
"""

from __future__ import annotations

import json
import logging
import random
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Timeout para operações de rede (segundos)
_CMD_TIMEOUT = 15
_IP_CHECK_TIMEOUT = 10


class VPNManager:
    """Gerencia conexões WireGuard para testes E2E."""

    def __init__(self, configs_dir: str | Path | None = None) -> None:
        self._configs_dir = Path(configs_dir or Path(__file__).parent / "configs")
        self._current_conf: Path | None = None
        self._interface: str | None = None

    # ------------------------------------------------------------------
    # Propriedades
    # ------------------------------------------------------------------

    @property
    def current_location(self) -> str | None:
        """Nome do local conectado (stem do .conf), ou None."""
        return self._current_conf.stem if self._current_conf else None

    def get_available_locations(self) -> list[str]:
        """Lista nomes dos .conf disponíveis em configs_dir."""
        if not self._configs_dir.exists():
            return []
        return sorted(p.stem for p in self._configs_dir.glob("*.conf"))

    # ------------------------------------------------------------------
    # Conexão / Desconexão
    # ------------------------------------------------------------------

    def connect(self, location: str | None = None) -> str:
        """Conecta via WireGuard. Se location=None, escolhe aleatório.

        Args:
            location: Nome do local (sem .conf) ou None para aleatório.

        Returns:
            Nome do local conectado.

        Raises:
            FileNotFoundError: Se o .conf não existir.
            RuntimeError: Se wg-quick falhar.
        """
        if self._current_conf:
            self.disconnect()

        available = self.get_available_locations()
        if not available:
            raise FileNotFoundError(
                f"Nenhum .conf encontrado em {self._configs_dir}. "
                "Baixe configs WireGuard de https://mullvad.net/account/wireguard-config"
            )

        if location is None:
            location = random.choice(available)
        elif location not in available:
            raise FileNotFoundError(
                f"Config '{location}.conf' não encontrada em {self._configs_dir}. "
                f"Disponíveis: {', '.join(available)}"
            )

        conf_path = self._configs_dir / f"{location}.conf"
        self._interface = location

        logger.info("VPN: conectando a %s ...", location)
        self._run_wg_quick("up", conf_path)
        self._current_conf = conf_path
        logger.info("VPN: conectado a %s", location)

        return location

    def disconnect(self) -> None:
        """Desconecta a VPN ativa."""
        if not self._current_conf:
            return

        location = self.current_location
        logger.info("VPN: desconectando de %s ...", location)
        try:
            self._run_wg_quick("down", self._current_conf)
        except RuntimeError:
            logger.warning(
                "VPN: falha ao desconectar de %s (pode já estar down)", location
            )
        finally:
            self._current_conf = None
            self._interface = None
            logger.info("VPN: desconectado")

    def rotate(self) -> str:
        """Desconecta e reconecta a um local diferente do atual.

        Returns:
            Nome do novo local conectado.
        """
        available = self.get_available_locations()
        current = self.current_location

        if current and len(available) > 1:
            candidates = [loc for loc in available if loc != current]
        else:
            candidates = available

        self.disconnect()
        return self.connect(random.choice(candidates) if candidates else None)

    # ------------------------------------------------------------------
    # Verificação de IP
    # ------------------------------------------------------------------

    def get_current_ip(self) -> dict:
        """Consulta IP público via Mullvad API.

        Returns:
            Dict com ip, country, city, mullvad_exit_ip, etc.
        """
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "--max-time",
                    str(_IP_CHECK_TIMEOUT),
                    "https://am.i.mullvad.net/json",
                ],
                capture_output=True,
                text=True,
                timeout=_IP_CHECK_TIMEOUT + 5,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                logger.info(
                    "VPN IP: %s (%s, %s) — Mullvad: %s",
                    data.get("ip"),
                    data.get("country"),
                    data.get("city"),
                    data.get("mullvad_exit_ip"),
                )
                return data
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            logger.warning("VPN: falha ao verificar IP — %s", exc)

        return {}

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    @staticmethod
    def _run_wg_quick(action: str, conf_path: Path) -> None:
        """Executa wg-quick up/down.

        Em ambientes sem systemd/resolvconf funcional (ex.: WSL2 + podman rootless),
        o wg-quick pode falhar ao aplicar DNS. Nesse caso, tenta novamente removendo
        diretivas `DNS = ...` do .conf.
        """
        cmd = ["wg-quick", action, str(conf_path)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_CMD_TIMEOUT,
            check=False,
        )
        if result.returncode == 0:
            return

        stderr = (result.stderr or "").strip()
        can_retry_without_dns = action == "up" and (
            "resolvconf" in stderr or "sd_bus_open_system" in stderr
        )

        if can_retry_without_dns:
            logger.info(
                "VPN: wg-quick não conseguiu aplicar DNS via resolvconf (%s). "
                "Aplicando fallback sem diretiva DNS (esperado em WSL2/Podman rootless).",
                conf_path.name,
            )
            temp_conf = VPNManager._create_temp_conf_without_dns(conf_path)
            retry_cmd = ["wg-quick", action, str(temp_conf)]
            retry = subprocess.run(
                retry_cmd,
                capture_output=True,
                text=True,
                timeout=_CMD_TIMEOUT,
                check=False,
            )
            if retry.returncode == 0:
                logger.info(
                    "VPN: fallback sem DNS aplicado com sucesso para %s.",
                    conf_path.name,
                )
                return
            raise RuntimeError(
                f"wg-quick {action} falhou (rc={retry.returncode}): {(retry.stderr or '').strip()}"
            )

        raise RuntimeError(
            f"wg-quick {action} falhou (rc={result.returncode}): {stderr}"
        )

    @staticmethod
    def _create_temp_conf_without_dns(conf_path: Path) -> Path:
        """Cria cópia temporária do .conf removendo linhas DNS=... (case-insensitive).

        Mantém o mesmo nome-base do arquivo para preservar o nome da interface WireGuard.
        """
        source_lines = conf_path.read_text(encoding="utf-8").splitlines()
        filtered_lines = [
            line for line in source_lines if not line.strip().lower().startswith("dns")
        ]

        temp_dir = Path(tempfile.mkdtemp(prefix="wg-no-dns-"))
        temp_conf = temp_dir / conf_path.name
        temp_conf.write_text("\n".join(filtered_lines) + "\n", encoding="utf-8")
        return temp_conf
