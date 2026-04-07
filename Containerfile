# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# playwright-e2e: Imagem para testes E2E com Playwright + WireGuard VPN
# ---------------------------------------------------------------------------
# Base: Cópia da imagem Microsoft Playwright hospedada no Docker Hub
FROM lzocateli/playwright:v1.49.0-noble

# WireGuard tools (wg-quick) + utilitários de rede/DNS + curl (verificação de IP)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    iproute2 \
    resolvconf \
    iptables \
    wireguard-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv (gerenciador Python rápido)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copiar definição de projeto e instalar dependências (cached no build)
COPY pyproject.toml .python-version ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Código-fonte NÃO é copiado — montado via bind volume no runtime.
# Isso elimina drift entre host e container e dispensa rebuild para mudanças de código.
ENV PYTHONPATH=/app

# Diretórios para bind mounts
RUN mkdir -p /app/reports /app/tests /app/vpn /app/vpn/configs

# Instalar browsers do Playwright
RUN uv run playwright install --with-deps chromium firefox webkit

# Entrypoint: rodar testes via uv
ENTRYPOINT ["uv", "run", "pytest", "--confcutdir=/app"]
CMD ["--base-url=http://host.containers.internal:1313"]
