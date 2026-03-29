"""Testes E2E de navegação no blog zocate.li.

Simula um usuário real navegando pelo blog:
- Visita a home, rola a página, lê títulos
- Clica em posts, lê artigos (scroll progressivo + tempo de leitura)
- Navega por links internos, volta, visita outro post
"""

from __future__ import annotations

import pytest

# URLs de posts para parametrizar (adicione ou altere conforme necessário)
BLOG_POSTS = [
    # Últimos 4 artigos (março 2026)
    "/posts/2026/deno-bun-nodejs-comparativo-node-modules-angular/",
    "/posts/2026/efcore-bulkextensions-operacoes-massa-dotnet/",
    "/posts/2026/uv-python-gerenciador-pacotes-comparativo-csharp/",
    "/posts/2026/ia-llm-rag-agents-mcp-guia-profissional/",
]


class TestBlogHome:
    """Testes de navegação na página inicial."""

    def test_home_loads(self, slow_page, base_url: str) -> None:
        """Home carrega sem erros e tem título."""
        slow_page.goto(base_url)
        assert slow_page.page.title(), "Página inicial sem título"

    def test_home_has_posts(self, slow_page, base_url: str) -> None:
        """Home lista posts do blog."""
        slow_page.goto(base_url)
        slow_page.scroll_down(300)
        articles = slow_page.page.locator("article").count()
        assert articles > 0, "Nenhum post encontrado na home"

    def test_home_scroll_and_read(self, slow_page, base_url: str, human_delay) -> None:
        """Simula scroll pela home como um usuário real."""
        slow_page.goto(base_url)
        slow_page.scroll_to_bottom(step=350, pause_min=1.5, pause_max=4.0)
        human_delay(min_s=3, max_s=8)


class TestBlogPostNavigation:
    """Testes de navegação em posts individuais."""

    @pytest.mark.parametrize("post_path", BLOG_POSTS)
    def test_post_loads(self, slow_page, base_url: str, post_path: str) -> None:
        """Post carrega e tem título h1."""
        slow_page.goto(f"{base_url}{post_path}")
        h1 = slow_page.page.locator("h1").first
        assert h1.is_visible(), f"Post {post_path} sem h1 visível"

    @pytest.mark.parametrize("post_path", BLOG_POSTS)
    def test_post_read_simulation(
        self, slow_page, base_url: str, post_path: str, human_delay
    ) -> None:
        """Simula a leitura completa de um post."""
        slow_page.goto(f"{base_url}{post_path}")

        # Scroll progressivo simulando leitura
        slow_page.scroll_to_bottom(step=300, pause_min=2.0, pause_max=6.0)

        # Tempo de leitura geral
        slow_page.wait_reading(min_s=10, max_s=25)

    def test_navigate_between_posts(
        self, slow_page, base_url: str, human_delay
    ) -> None:
        """Navega da home para um post, volta, navega para outro."""
        slow_page.goto(base_url)
        human_delay(min_s=2, max_s=5)

        # Clica no primeiro post visível
        first_link = slow_page.page.locator("article a").first
        if first_link.is_visible():
            slow_page.click("article a >> nth=0")
            human_delay(min_s=5, max_s=15)

            # Volta para home
            slow_page.page.go_back()
            human_delay(min_s=2, max_s=4)


class TestBlogMetaTags:
    """Verifica meta tags básicas durante navegação."""

    def test_home_meta_description(self, slow_page, base_url: str) -> None:
        """Home tem meta description."""
        slow_page.goto(base_url)
        meta = slow_page.page.locator('meta[name="description"]')
        content = meta.get_attribute("content")
        assert content and len(content) > 10, "Meta description ausente ou curta"

    @pytest.mark.parametrize("post_path", BLOG_POSTS)
    def test_post_og_tags(self, slow_page, base_url: str, post_path: str) -> None:
        """Posts têm Open Graph tags."""
        slow_page.goto(f"{base_url}{post_path}")
        og_title = slow_page.page.locator('meta[property="og:title"]')
        assert og_title.get_attribute("content"), f"og:title ausente em {post_path}"

    def test_no_broken_images(self, slow_page, base_url: str) -> None:
        """Verifica que imagens na home carregam sem erro."""
        slow_page.goto(base_url)
        images = slow_page.page.locator("img")
        count = images.count()
        broken_images: list[str] = []

        for i in range(min(count, 10)):  # Verifica até 10 imagens
            img = images.nth(i)
            src = img.get_attribute("src")
            if src:
                loaded_ok = img.evaluate("""
                    (el) => {
                        el.scrollIntoView({ block: "center", inline: "nearest" });

                        return new Promise((resolve) => {
                            const isOk = () => el.complete && el.naturalWidth > 0;

                            if (el.complete) {
                                resolve(isOk());
                                return;
                            }

                            const timer = setTimeout(() => resolve(isOk()), 7000);

                            el.addEventListener(
                                "load",
                                () => {
                                    clearTimeout(timer);
                                    resolve(isOk());
                                },
                                { once: true }
                            );

                            el.addEventListener(
                                "error",
                                () => {
                                    clearTimeout(timer);
                                    resolve(false);
                                },
                                { once: true }
                            );
                        });
                    }
                    """)

                if not loaded_ok:
                    current_src = img.get_attribute("currentSrc") or src
                    broken_images.append(current_src)

        assert (
            not broken_images
        ), "Imagens quebradas encontradas na home:\n" + "\n".join(
            f"- {url}" for url in broken_images
        )
