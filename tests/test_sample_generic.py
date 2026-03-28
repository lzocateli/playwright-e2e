"""Testes E2E genéricos — template para novos roteiros.

Este arquivo serve como exemplo de como usar as fixtures:
- `slow_page`: Page com delays automáticos
- `human_delay`: Função para sleep manual com duração aleatória
- `base_url`: URL configurável via --base-url

Copie e adapte para criar roteiros para qualquer site.
"""

from __future__ import annotations

import pytest


class TestSampleNavigation:
    """Exemplo: navegar em um site genérico com comportamento humano."""

    def test_page_loads(self, slow_page, base_url: str) -> None:
        """Verifica que a página principal carrega."""
        slow_page.goto(base_url)
        assert slow_page.page.title()

    def test_scroll_and_explore(self, slow_page, base_url: str, human_delay) -> None:
        """Simula um usuário explorando a página."""
        slow_page.goto(base_url)

        # Scroll pela página
        slow_page.scroll_down(500)
        human_delay(min_s=3, max_s=8)

        # Scroll mais
        slow_page.scroll_down(500)
        human_delay(min_s=2, max_s=5)

    def test_click_first_link(self, slow_page, base_url: str, human_delay) -> None:
        """Clica no primeiro link encontrado e verifica navegação."""
        slow_page.goto(base_url)
        human_delay(min_s=2, max_s=5)

        # Tenta clicar no primeiro link no conteúdo principal
        link = slow_page.page.locator("main a, article a, .content a").first
        if link.is_visible():
            href = link.get_attribute("href")
            slow_page.click("main a >> nth=0")
            human_delay(min_s=5, max_s=10)

            # Verifica que navegou (URL mudou ou página carregou)
            assert slow_page.page.url != base_url or href == "#"

    def test_full_reading_session(self, slow_page, base_url: str, human_delay) -> None:
        """Simula uma sessão completa: acessar, ler, navegar, sair."""
        # 1. Acessa o site
        slow_page.goto(base_url)

        # 2. Lê a página inicial (scroll progressivo)
        slow_page.scroll_to_bottom(step=300, pause_min=1.0, pause_max=3.0)

        # 3. "Pensa" antes de decidir o que clicar
        human_delay(min_s=3, max_s=8)

        # 4. Volta ao topo e clica em algo
        slow_page.page.evaluate("window.scrollTo(0, 0)")
        human_delay(min_s=1, max_s=3)


class TestSampleFormInteraction:
    """Exemplo: interação com formulários (adapte os seletores)."""

    @pytest.mark.skip(reason="Adapte os seletores para seu site")
    def test_search_form(self, slow_page, base_url: str, human_delay) -> None:
        """Exemplo de busca em um site."""
        slow_page.goto(base_url)
        human_delay(min_s=2, max_s=4)

        # Adapte o seletor do campo de busca
        slow_page.fill('input[type="search"]', "pytest playwright")
        human_delay(min_s=1, max_s=3)

        # Adapte o seletor do botão de busca
        slow_page.click('button[type="submit"]')
        human_delay(min_s=5, max_s=10)

        # Verifica resultados
        assert slow_page.page.locator(".search-results, .results").count() > 0
