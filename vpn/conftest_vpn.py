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

    # ------------------------------------------------------------------
    # Hooks de sessão
    # ------------------------------------------------------------------

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: pytest.Session) -> None:
        """Conecta VPN no início da sessão."""
        locations = self._manager.get_available_locations()
        if not locations:
            logger.warning("VPN: nenhum .conf encontrado — testes rodarão sem VPN")
            return

        self._manager.connect()
        ip_info = self._manager.get_current_ip()
        logger.info(
            "VPN sessão iniciada — Local: %s | IP: %s",
            self._manager.current_location,
            ip_info.get("ip", "desconhecido"),
        )

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        """Desconecta VPN no final da sessão."""
        self._manager.disconnect()

    # ------------------------------------------------------------------
    # Hooks por teste (rotação)
    # ------------------------------------------------------------------

    @pytest.hookimpl(hookimpl=True)
    def pytest_runtest_setup(self, item: pytest.Item) -> None:
        """Rotaciona VPN antes de cada teste, se configurado."""
        if self._rotate_mode == "per-test" and self._manager.current_location:
            old = self._manager.current_location
            new_loc = self._manager.rotate()
            ip_info = self._manager.get_current_ip()
            logger.info(
                "VPN rotação: %s → %s | IP: %s",
                old, new_loc, ip_info.get("ip", "desconhecido"),
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
