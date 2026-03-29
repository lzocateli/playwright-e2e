"""Plugin e fixtures pytest para integração VPN com WireGuard/Mullvad."""

from __future__ import annotations

import logging

import pytest

from vpn.vpn_manager import VPNManager

logger = logging.getLogger(__name__)


class VPNPlugin:
    """Plugin pytest que gerencia ciclo de vida da VPN."""

    def __init__(self, config: pytest.Config) -> None:
        self._config = config
        self._manager = VPNManager()
        self._rotate_mode = config.getoption("--vpn-rotate", default="off")
        self._strict_mode = config.getoption("--vpn-strict", default=False)
        self._current_ip_info: dict = {}
        self._test_vpn_context: dict[str, dict[str, str]] = {}

    def _set_metadata(self, key: str, value: str) -> None:
        metadata = getattr(self._config, "_metadata", None)
        if isinstance(metadata, dict):
            metadata[key] = value

    @staticmethod
    def _is_mullvad_exit(ip_info: dict) -> bool:
        value = ip_info.get("mullvad_exit_ip")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes"}
        return False

    def _enforce_vpn_strict(self, ip_info: dict, *, context: str) -> None:
        if not self._strict_mode:
            return

        is_mullvad = self._is_mullvad_exit(ip_info)
        ip_value = ip_info.get("ip", "desconhecido")

        if not is_mullvad:
            message = (
                "VPN strict mode: saída não confirmada como Mullvad "
                f"({context}). IP atual: {ip_value}. "
                "Verifique conectividade do túnel e rotação."
            )
            if context == "sessionstart":
                raise pytest.UsageError(message)
            pytest.fail(message, pytrace=False)

    def _record_current_test_context(self, item: pytest.Item) -> None:
        location = self._manager.current_location or "desconhecido"
        ip_value = self._current_ip_info.get("ip", "desconhecido")
        mullvad = self._is_mullvad_exit(self._current_ip_info)
        self._test_vpn_context[item.nodeid] = {
            "location": location,
            "ip": str(ip_value),
            "mullvad": "true" if mullvad else "false",
        }

    # ------------------------------------------------------------------
    # Hooks de sessão
    # ------------------------------------------------------------------

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: pytest.Session) -> None:
        """Conecta VPN no início da sessão."""
        self._set_metadata("VPN Enabled", "true")
        self._set_metadata("VPN Rotate", self._rotate_mode)
        self._set_metadata("VPN Strict", "true" if self._strict_mode else "false")

        locations = self._manager.get_available_locations()
        if not locations:
            logger.warning("VPN: nenhum .conf encontrado — testes rodarão sem VPN")
            self._set_metadata("VPN Enabled", "false")
            self._set_metadata("VPN Status", "sem configs (*.conf)")
            return

        self._manager.connect()
        ip_info = self._manager.get_current_ip()
        self._current_ip_info = ip_info
        self._enforce_vpn_strict(ip_info, context="sessionstart")
        self._set_metadata(
            "VPN Session Location", self._manager.current_location or "desconhecido"
        )
        self._set_metadata("VPN Session IP", str(ip_info.get("ip", "desconhecido")))
        self._set_metadata(
            "VPN Mullvad Exit",
            "true" if self._is_mullvad_exit(ip_info) else "false",
        )
        logger.info(
            "VPN sessão iniciada — Local: %s | IP: %s",
            self._manager.current_location,
            ip_info.get("ip", "desconhecido"),
        )

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        """Desconecta VPN no final da sessão."""
        self._set_metadata(
            "VPN Last Location", self._manager.current_location or "desconhecido"
        )
        self._set_metadata(
            "VPN Last IP", str(self._current_ip_info.get("ip", "desconhecido"))
        )
        self._manager.disconnect()

    # ------------------------------------------------------------------
    # Hooks por teste (rotação)
    # ------------------------------------------------------------------

    @pytest.hookimpl
    def pytest_runtest_setup(self, item: pytest.Item) -> None:
        """Rotaciona VPN antes de cada teste, se configurado."""
        if self._rotate_mode == "per-test" and self._manager.current_location:
            old = self._manager.current_location
            new_loc = self._manager.rotate()
            ip_info = self._manager.get_current_ip()
            self._current_ip_info = ip_info
            self._enforce_vpn_strict(ip_info, context="per-test rotation")
            logger.info(
                "VPN rotação: %s → %s | IP: %s",
                old,
                new_loc,
                ip_info.get("ip", "desconhecido"),
            )

        self._record_current_test_context(item)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo):
        """Inclui contexto da VPN no detalhe de cada teste no report.html."""
        outcome = yield
        report = outcome.get_result()

        if report.when != "call":
            return

        context = self._test_vpn_context.get(item.nodeid)
        if not context:
            return

        report.sections.append(
            (
                "VPN",
                (
                    f"Local: {context['location']}\n"
                    f"IP: {context['ip']}\n"
                    f"Mullvad Exit: {context['mullvad']}"
                ),
            )
        )

    # ------------------------------------------------------------------
    # Fixtures (registradas via plugin)
    # ------------------------------------------------------------------

    @pytest.fixture(scope="session")
    def vpn_manager(self) -> VPNManager:
        """Instância do VPNManager (session-scoped)."""
        return self._manager

    @pytest.fixture
    def vpn_session(self, vpn_manager: VPNManager):
        """Fixture que garante VPN conectada durante o teste."""
        if not vpn_manager.current_location:
            vpn_manager.connect()
        yield vpn_manager
        # Não desconecta — será gerenciado por session hooks

    @pytest.fixture
    def vpn_rotate(self, vpn_manager: VPNManager):
        """Fixture que rotaciona VPN antes do teste."""
        vpn_manager.rotate()
        yield vpn_manager
