"""Configuração global de pytest — registra custom options e plugins VPN."""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Registra custom options para testes E2E."""
    group = parser.getgroup("e2e", "Opções de testes E2E")

    group.addoption(
        "--human-speed",
        choices=["slow", "normal", "fast"],
        default="normal",
        help="Intensidade dos delays entre ações (default: normal)",
    )
    group.addoption(
        "--enable-vpn",
        action="store_true",
        default=False,
        help="Ativar conexão VPN via WireGuard antes dos testes",
    )
    group.addoption(
        "--vpn-rotate",
        choices=["per-test", "per-session", "off"],
        default="off",
        help="Rotação de VPN: per-test, per-session, ou off (default: off)",
    )
    group.addoption(
        "--vpn-strict",
        action="store_true",
        default=False,
        help=(
            "Falha a execução se a saída não for Mullvad "
            "(valida mullvad_exit_ip no início da sessão e após rotações)"
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    """Registra o plugin de VPN se --enable-vpn estiver ativo."""
    if config.getoption("--enable-vpn", default=False):
        import sys

        _src = str(Path(__file__).resolve().parent / "src")
        if _src not in sys.path:
            sys.path.insert(0, _src)

        from vpn.conftest_vpn import VPNPlugin

        configs_dir = Path(str(config.rootdir)) / "vpn" / "configs"
        config.pluginmanager.register(
            VPNPlugin(config, configs_dir=configs_dir), "vpn_plugin"
        )
