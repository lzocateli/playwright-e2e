"""Rotaciona artigos do blog para testes E2E.

Lê o sitemap.xml, seleciona aleatoriamente artigos novos para BLOG_POSTS
e move os já testados para BLOG_POSTS_HIST em test_blog_navigation.py.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import textwrap
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

VERSION = "0.1.0"
PROGRAM = "rotate-posts"

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
POSTS_PATTERN = re.compile(r"^(# [^\n]*\n)?BLOG_POSTS\s*=\s*\[([^\]]*)\]", re.MULTILINE)
HIST_PATTERN = re.compile(
    r"^(# [^\n]*\n)?BLOG_POSTS_HIST\s*=\s*\[([^\]]*)\]", re.MULTILINE
)
URL_IN_LIST = re.compile(r'"([^"]+)"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(f"""\
            {PROGRAM} v{VERSION}

            Rotaciona artigos do blog para testes E2E com Playwright.
            Lê o sitemap.xml, seleciona aleatoriamente artigos novos para
            BLOG_POSTS e move os já testados para BLOG_POSTS_HIST em
            tests/test_blog_navigation.py.

            ──────────────────────────────────────────────────────────────
            SINTAXE
            ──────────────────────────────────────────────────────────────
              uv run {PROGRAM} [opcoes]
              uv run {PROGRAM} -h | --help           Esta mensagem

            ──────────────────────────────────────────────────────────────
            EXEMPLOS
            ──────────────────────────────────────────────────────────────
              uv run {PROGRAM}                                    Rotação padrão (3-6 posts)
              uv run {PROGRAM} --dry-run                          Mostra o que mudaria
              uv run {PROGRAM} --base-url https://zocate.li       Site em produção
              uv run {PROGRAM} --min-posts 2 --max-posts 4        Range customizado
              uv run {PROGRAM} --reset-hist                       Limpa histórico
              uv run {PROGRAM} --test-file meu/test_blog.py       Arquivo de teste customizado

            ──────────────────────────────────────────────────────────────
            FLUXO
            ──────────────────────────────────────────────────────────────
              1. Busca {{base_url}}/sitemap.xml e extrai URLs de /posts/
              2. Lê BLOG_POSTS e BLOG_POSTS_HIST do arquivo de teste
              3. Move BLOG_POSTS atual → BLOG_POSTS_HIST (acumula)
              4. Seleciona aleatoriamente N artigos novos (nunca testados)
              5. Grava novos BLOG_POSTS e BLOG_POSTS_HIST no arquivo
              Quando todos os artigos já estiverem no histórico,
              recicla os mais antigos automaticamente.

            ──────────────────────────────────────────────────────────────
            ARQUIVO DE TESTE
            ──────────────────────────────────────────────────────────────
              Por padrão, o script detecta automaticamente o arquivo
              tests/test_blog_navigation.py relativo à raiz do projeto.
              Use --test-file para apontar para outro arquivo.
              O arquivo deve conter as variáveis BLOG_POSTS e BLOG_POSTS_HIST
              como listas Python com strings entre aspas duplas.
        """),
    )
    parser.add_argument(
        "--base-url",
        default="https://zocate.li",
        help="URL base do site (default: https://zocate.li)",
    )
    parser.add_argument(
        "--min-posts",
        type=int,
        default=3,
        help="Mínimo de artigos a selecionar (default: 3)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=6,
        help="Máximo de artigos a selecionar (default: 6)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exibe o que mudaria sem alterar o arquivo",
    )
    parser.add_argument(
        "--reset-hist",
        action="store_true",
        help="Limpa BLOG_POSTS_HIST antes de rotacionar",
    )
    parser.add_argument(
        "--test-file",
        type=Path,
        default=None,
        metavar="CAMINHO",
        help="Caminho para o arquivo de teste com BLOG_POSTS/BLOG_POSTS_HIST "
        "(default: tests/test_blog_navigation.py relativo à raiz do projeto)",
    )

    args = parser.parse_args()

    if args.min_posts < 1:
        parser.error("--min-posts deve ser >= 1")
    if args.max_posts < args.min_posts:
        parser.error("--max-posts deve ser >= --min-posts")

    return args


def resolve_test_file(override: Path | None) -> Path:
    """Resolve o caminho para test_blog_navigation.py."""
    if override:
        path = override
    else:
        # src/e2e/rotate_posts.py → parents[2] = raiz do projeto
        project_root = Path(__file__).resolve().parents[2]
        path = project_root / "tests" / "test_blog_navigation.py"

    if not path.is_file():
        print(f"❌ Arquivo não encontrado: {path}", file=sys.stderr)
        sys.exit(1)

    return path


def fetch_sitemap(base_url: str) -> list[str]:
    """Busca sitemap.xml e retorna paths de posts (/posts/...)."""
    url = f"{base_url.rstrip('/')}/sitemap.xml"
    print(f"📡 Buscando sitemap: {url}")

    try:
        req = Request(url, headers={"User-Agent": f"{PROGRAM}/{VERSION}"})  # noqa: S310
        with urlopen(req, timeout=15) as resp:  # noqa: S310
            xml_data = resp.read()
    except URLError as exc:
        print(f"❌ Erro ao buscar sitemap: {exc}", file=sys.stderr)
        sys.exit(1)

    root = ET.fromstring(xml_data)  # noqa: S314
    base_parsed = urlparse(base_url)
    posts: list[str] = []

    for loc_el in root.findall(".//sm:url/sm:loc", SITEMAP_NS):
        loc = (loc_el.text or "").strip()
        if "/posts/" not in loc:
            continue
        parsed = urlparse(loc)
        path = parsed.path
        if not path.endswith("/"):
            path += "/"
        posts.append(path)

    print(f"🔍 Encontrados {len(posts)} artigos no sitemap")
    return posts


def extract_list(content: str, pattern: re.Pattern[str]) -> list[str]:
    """Extrai URLs de uma lista Python no arquivo fonte."""
    match = pattern.search(content)
    if not match:
        return []
    block = match.group(2)
    return URL_IN_LIST.findall(block)


def format_python_list(urls: list[str], comment: str) -> str:
    """Formata uma lista Python com uma URL por linha."""
    if not urls:
        return f"[\n    # {comment}\n]"

    items = ",\n".join(f'    "{u}"' for u in urls)
    return f"[\n    # {comment}\n{items},\n]"


def replace_list(
    content: str, pattern: re.Pattern[str], new_list: str, var_prefix: str
) -> str:
    """Substitui o bloco de lista no conteúdo do arquivo."""
    match = pattern.search(content)
    if not match:
        print(f"❌ Não encontrei {var_prefix} no arquivo", file=sys.stderr)
        sys.exit(1)

    full_start = match.start()
    full_end = match.end()

    return content[:full_start] + f"{var_prefix} = {new_list}" + content[full_end:]


def main() -> None:
    args = parse_args()

    test_file = resolve_test_file(args.test_file)

    # 1. Fetch sitemap
    sitemap_posts = fetch_sitemap(args.base_url)
    if not sitemap_posts:
        print("❌ Nenhum artigo encontrado no sitemap.", file=sys.stderr)
        sys.exit(1)

    # 2. Ler estado atual
    content = test_file.read_text(encoding="utf-8")
    current_posts = extract_list(content, POSTS_PATTERN)
    current_hist = extract_list(content, HIST_PATTERN)

    print(f"   BLOG_POSTS atual:      {len(current_posts)} artigos")
    print(f"   BLOG_POSTS_HIST atual: {len(current_hist)} artigos")

    # 3. Reset histórico se pedido
    if args.reset_hist:
        print("🗑️  Limpando histórico (--reset-hist)")
        current_hist = []

    # 4. Calcular novo histórico (antigos + atuais)
    new_hist_set: dict[str, None] = {}
    for u in current_hist:
        new_hist_set[u] = None
    for u in current_posts:
        new_hist_set[u] = None
    new_hist = list(new_hist_set.keys())

    # 5. Pool de candidatos
    hist_set = set(new_hist)
    pool = [p for p in sitemap_posts if p not in hist_set]

    if len(pool) < args.min_posts:
        remaining = args.min_posts - len(pool)
        print(
            f"⚠️  Pool insuficiente ({len(pool)} disponíveis, mínimo {args.min_posts}). "
            f"Reciclando {remaining} do histórico."
        )
        recyclable = [h for h in reversed(new_hist) if h not in pool]
        recycled = recyclable[:remaining]
        pool.extend(recycled)
        # Remove reciclados do histórico para evitar duplicata
        recycled_set = set(recycled)
        new_hist = [h for h in new_hist if h not in recycled_set]

    if not pool:
        print("❌ Nenhum artigo disponível para seleção.", file=sys.stderr)
        sys.exit(1)

    # 6. Selecionar aleatoriamente
    count = random.randint(args.min_posts, min(args.max_posts, len(pool)))
    selected = random.sample(pool, count)

    print(f"\n🎲 Selecionados {len(selected)} artigos:")
    for p in selected:
        print(f"   • {p}")

    # 7. Formatar novas listas
    today = date.today().isoformat()
    new_posts_str = format_python_list(
        selected, f"Selecionados aleatoriamente em {today} via {PROGRAM}"
    )
    new_hist_str = format_python_list(
        new_hist, f"Atualizado em {today} via {PROGRAM} ({len(new_hist)} artigos)"
    )

    # 8. Substituir no conteúdo
    new_content = replace_list(content, POSTS_PATTERN, new_posts_str, "BLOG_POSTS")
    new_content = replace_list(
        new_content, HIST_PATTERN, new_hist_str, "BLOG_POSTS_HIST"
    )

    # 9. Dry-run ou gravar
    if args.dry_run:
        print("\n📋 Dry-run — alterações que seriam feitas:\n")
        print("── BLOG_POSTS (novo) ──")
        print(f"BLOG_POSTS = {new_posts_str}")
        print(f"\n── BLOG_POSTS_HIST (novo, {len(new_hist)} itens) ──")
        print(f"BLOG_POSTS_HIST = {new_hist_str}")
        print(f"\n⚠️  Nenhum arquivo alterado (--dry-run)")
    else:
        test_file.write_text(new_content, encoding="utf-8")
        print(f"\n✏️  Arquivo atualizado: {test_file}")
        print(f"   BLOG_POSTS:      {len(selected)} artigos (novos)")
        print(f"   BLOG_POSTS_HIST: {len(new_hist)} artigos (acumulado)")
        print("✅ Rotação concluída!")


if __name__ == "__main__":
    main()
