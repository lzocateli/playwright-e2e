"""Fixtures compartilhadas para testes E2E com Playwright.

Inclui:
- Configuração de browser context (viewport, locale, vídeo)
- Fixtures de sleep/delay para simular comportamento real de usuário
- CLI options: --base-url, --human-speed, --enable-vpn, --vpn-rotate
"""

from __future__ import annotations

import random
import time
from typing import Generator

import pytest
from playwright.sync_api import Page, BrowserContext


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("e2e", "Opções de testes E2E")
    # --base-url já é registrado pelo pytest-playwright / pytest-base-url
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


# ---------------------------------------------------------------------------
# Speed multipliers
# ---------------------------------------------------------------------------

SPEED_MULTIPLIERS = {
    "slow": 2.0,
    "normal": 1.0,
    "fast": 0.3,
}


# ---------------------------------------------------------------------------
# Fixtures básicas
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def speed_multiplier(request: pytest.FixtureRequest) -> float:
    """Multiplicador de velocidade baseado em --human-speed."""
    speed = request.config.getoption("--human-speed")
    return SPEED_MULTIPLIERS[speed]


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Configura o browser context com viewport, locale e gravação de vídeo."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "pt-BR",
        "timezone_id": "America/Sao_Paulo",
        "record_video_dir": "reports/videos",
        "record_video_size": {"width": 1280, "height": 720},
    }


# ---------------------------------------------------------------------------
# Fixtures de delay / sleep
# ---------------------------------------------------------------------------


@pytest.fixture
def human_delay(speed_multiplier: float):
    """Retorna uma função para aplicar sleep com duração aleatória.

    Uso:
        human_delay()                    # 2-8s (leitura rápida)
        human_delay(min_s=10, max_s=30)  # leitura de artigo
        human_delay(min_s=1, max_s=3)    # entre cliques
    """

    def _delay(min_s: float = 2.0, max_s: float = 8.0) -> float:
        actual_min = min_s * speed_multiplier
        actual_max = max_s * speed_multiplier
        duration = random.uniform(actual_min, actual_max)
        time.sleep(duration)
        return duration

    return _delay


class SlowPage:
    """Wrapper de Page que adiciona delays automáticos após ações comuns."""

    def __init__(self, page: Page, speed_multiplier: float) -> None:
        self._page = page
        self._speed = speed_multiplier

    def _sleep(self, min_s: float, max_s: float) -> None:
        time.sleep(random.uniform(min_s * self._speed, max_s * self._speed))

    def goto(self, url: str, **kwargs) -> None:
        self._page.goto(url, **kwargs)
        self._sleep(3.0, 8.0)

    def click(self, selector: str, **kwargs) -> None:
        self._page.click(selector, **kwargs)
        self._sleep(1.0, 4.0)

    def scroll_down(self, pixels: int = 500) -> None:
        self._page.mouse.wheel(0, pixels)
        self._sleep(2.0, 5.0)

    def scroll_to_bottom(self, step: int = 400, pause_min: float = 1.0, pause_max: float = 3.0) -> None:
        """Scroll progressivo até o final da página, simulando leitura."""
        prev_height = 0
        while True:
            self._page.mouse.wheel(0, step)
            self._sleep(pause_min, pause_max)
            current_height = self._page.evaluate("window.scrollY")
            total_height = self._page.evaluate("document.body.scrollHeight - window.innerHeight")
            if current_height >= total_height or current_height == prev_height:
                break
            prev_height = current_height

    def fill(self, selector: str, value: str, **kwargs) -> None:
        self._page.fill(selector, value, **kwargs)
        self._sleep(0.5, 2.0)

    def wait_reading(self, min_s: float = 15.0, max_s: float = 45.0) -> None:
        """Simula o tempo de leitura de um artigo."""
        self._sleep(min_s, max_s)

    @property
    def page(self) -> Page:
        """Acesso direto à Page do Playwright para operações não-wrappeadas."""
        return self._page

    def __getattr__(self, name: str):
        """Delega atributos não-definidos para a Page original."""
        return getattr(self._page, name)


@pytest.fixture
def slow_page(page: Page, speed_multiplier: float) -> SlowPage:
    """Page com delays automáticos para simular comportamento humano."""
    return SlowPage(page, speed_multiplier)


# ---------------------------------------------------------------------------
# VPN integration (carrega fixtures de vpn/ se --enable-vpn ativo)
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Registra o plugin de VPN se --enable-vpn estiver ativo."""
    if config.getoption("--enable-vpn", default=False):
        from vpn.conftest_vpn import VPNPlugin
        config.pluginmanager.register(VPNPlugin(config), "vpn_plugin")
