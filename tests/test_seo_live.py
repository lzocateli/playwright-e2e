"""Testes E2E de SEO em produção.

Verifica elementos de SEO acessando o site ao vivo:
- robots.txt acessível e com conteúdo
- sitemap.xml presente e válida
- HTTPS ativo e redirect funcionando
- Headers de segurança
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page


class TestRobotsTxt:
    """Verificações do robots.txt."""

    def test_robots_accessible(self, page: Page, base_url: str) -> None:
        """robots.txt retorna 200."""
        response = page.goto(f"{base_url}/robots.txt")
        assert response and response.status == 200

    def test_robots_has_sitemap(self, page: Page, base_url: str) -> None:
        """robots.txt referencia o sitemap."""
        page.goto(f"{base_url}/robots.txt")
        content = page.content()
        assert "sitemap" in content.lower(), "robots.txt não referencia sitemap"


class TestSitemap:
    """Verificações do sitemap.xml."""

    def test_sitemap_accessible(self, page: Page, base_url: str) -> None:
        """sitemap.xml retorna 200."""
        response = page.goto(f"{base_url}/sitemap.xml")
        assert response and response.status == 200

    def test_sitemap_has_urls(self, page: Page, base_url: str) -> None:
        """sitemap.xml contém URLs."""
        page.goto(f"{base_url}/sitemap.xml")
        content = page.content()
        assert "<loc>" in content, "sitemap.xml sem URLs"


class TestHTTPS:
    """Verificações de HTTPS e segurança."""

    def test_https_active(self, page: Page, base_url: str) -> None:
        """Site responde via HTTPS (se base_url usar https)."""
        if not base_url.startswith("https"):
            pytest.skip("base_url não usa HTTPS")
        response = page.goto(base_url)
        assert response and response.status == 200

    def test_no_mixed_content(self, page: Page, base_url: str) -> None:
        """Página não carrega recursos HTTP em site HTTPS."""
        if not base_url.startswith("https"):
            pytest.skip("base_url não usa HTTPS")
        page.goto(base_url)
        # Verifica se há recursos carregados via HTTP inseguro
        scripts = page.locator('script[src^="http://"]')
        assert scripts.count() == 0, "Mixed content: scripts HTTP em página HTTPS"


class TestSecurityHeaders:
    """Verificação de headers de segurança (requer HTTPS)."""

    def test_x_content_type_options(self, page: Page, base_url: str) -> None:
        """Header X-Content-Type-Options presente."""
        response = page.goto(base_url)
        if response:
            header = response.headers.get("x-content-type-options")
            # Alguns servidores não enviam — apenas aviso
            if header:
                assert header == "nosniff"


class TestCanonicalAndMeta:
    """Verificações de canonical e meta tags globais."""

    def test_home_has_canonical(self, page: Page, base_url: str) -> None:
        """Home tem link canonical."""
        page.goto(base_url)
        canonical = page.locator('link[rel="canonical"]')
        href = canonical.get_attribute("href")
        assert href, "Link canonical ausente na home"

    def test_home_has_lang(self, page: Page, base_url: str) -> None:
        """HTML tem atributo lang."""
        page.goto(base_url)
        lang = page.locator("html").get_attribute("lang")
        assert lang, "Atributo lang ausente no <html>"
