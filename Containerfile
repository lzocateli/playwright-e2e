# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# playwright-e2e: Imagem para testes E2E com Playwright + WireGuard VPN
# ---------------------------------------------------------------------------
# Base: Cópia da imagem Microsoft Playwright hospedada no Docker Hub
FROM lzocateli/playwright:v1.49.0-noble

# WireGuard tools (wg-quick) + curl (verificação de IP)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       wireguard-tools \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv (gerenciador Python rápido)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copiar definição de projeto e instalar dependências
COPY pyproject.toml .python-version ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copiar código da aplicação
COPY conftest.py ./
COPY vpn/ ./vpn/
COPY tests/ ./tests/

# Diretórios para bind mounts
RUN mkdir -p /app/reports /app/vpn/configs

# Instalar browsers do Playwright
RUN uv run playwright install --with-deps chromium firefox webkit

# Entrypoint: rodar testes via uv
ENTRYPOINT ["uv", "run", "pytest"]
CMD ["--base-url=http://host.containers.internal:1313"]
