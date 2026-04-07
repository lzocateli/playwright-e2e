#!/usr/bin/env bash
set -euo pipefail

VERSION="0.1.0"
PROGRAM="run-e2e.sh"

usage() {
    cat <<USAGE
${PROGRAM} v${VERSION}

Wrapper para executar testes E2E com Playwright via Docker ou Podman.
Baixa a imagem publicada automaticamente (se necessario) e executa os testes
dentro do container com suporte a VPN, simulacao humana e multi-browser.
Se a imagem nao estiver disponivel no registry, faz o build local.

O script detecta automaticamente docker ou podman (nesta ordem).

SINTAXE:
  ${PROGRAM} [opcoes] [-- pytest-args]
  ${PROGRAM} -h | --help                        Esta mensagem

EXEMPLOS:
  ${PROGRAM}                                    Basico, sem VPN
  ${PROGRAM} --base-url https://zocate.li       Site em producao
  ${PROGRAM} --enable-vpn --human-speed slow    VPN + delays longos
  ${PROGRAM} --enable-vpn --vpn-rotate per-test Rotacao VPN por teste
  ${PROGRAM} --enable-vpn --vpn-strict          Falha se saída não for Mullvad
  ${PROGRAM} --browser chromium                 Browser especifico
  ${PROGRAM} --rebuild --base-url https://z.li  Reconstroi imagem
  ${PROGRAM} --open-report --base-url https://z.li Abre relatorio ao finalizar
  ${PROGRAM} --open-first-video --base-url https://z.li Abre o primeiro .webm
  ${PROGRAM} --rotate-posts                     Rotaciona posts antes dos testes
  ${PROGRAM} --rotate-posts --min-posts 2 --max-posts 5 Posts customizados
  ${PROGRAM} --rotate-posts --dry-run-rotate    Preview da rotacao sem aplicar
  ${PROGRAM} -- -k test_home                    Filtra testes pytest

──────────────────────────────────────────────────────────────
OPCOES
──────────────────────────────────────────────────────────────
  --base-url URL       URL do site a testar
                       Default: http://host.containers.internal:1313
  --browser BROWSER    chromium | firefox | webkit
                       Default: aleatorio (escolhido automaticamente)
  --human-speed SPEED  slow (2x) | normal (1x) | fast (0.3x)
                       Default: normal
  --enable-vpn         Ativa VPN WireGuard (requer configs em vpn/configs/)
                       Adiciona --cap-add=NET_ADMIN ao container
  --vpn-rotate MODE    per-test | per-session | off
                       Default: off
  --vpn-strict         Falha se a saída não for Mullvad
  --rebuild            Remove e reconstroi a imagem antes de executar
  --open-report        Abre reports/report.html ao finalizar
  --open-first-video   Abre o primeiro .webm em reports/videos ao finalizar
  --rotate-posts       Rotaciona artigos do blog antes dos testes
                       Requer 'uv' instalado no host
  --min-posts N        Posts minimos a selecionar (default: 3)
                       So usado com --rotate-posts
  --max-posts N        Posts maximos a selecionar (default: 6)
                       Deve ser >= --min-posts
  --reset-hist         Limpa BLOG_POSTS_HIST antes de rotacionar
                       Requer --rotate-posts
  --dry-run-rotate     Preview da rotacao sem alterar o arquivo de teste
                       Requer --rotate-posts
  --                   Tudo apos '--' e passado diretamente ao pytest

──────────────────────────────────────────────────────────────
IMAGEM
──────────────────────────────────────────────────────────────
  Nome:       lzocateli/playwright-e2e:v0.1.0
  Base:       lzocateli/playwright (copia de mcr.microsoft.com/playwright/python)
  Pull:       Automatico na primeira execucao
  Build:      Automatico apenas se a imagem nao estiver disponivel no registry
  Containerfile no diretorio do script

──────────────────────────────────────────────────────────────
BIND MOUNTS
──────────────────────────────────────────────────────────────
  ./reports             → /app/reports       (relatorios HTML + videos)
  ./tests               → /app/tests        (roteiros pytest, read-only)
  ./vpn/configs         → /app/vpn/configs   (configs WireGuard, com --enable-vpn)

──────────────────────────────────────────────────────────────
VPN (Mullvad/WireGuard)
──────────────────────────────────────────────────────────────
  Requer arquivos .conf em vpn/configs/ (gitignored).
  Gerar em: https://mullvad.net/account/wireguard-config
  Nomear:   br-sao.conf, us-nyc.conf, de-fra.conf, etc.
  Quando --enable-vpn esta ativo:
    - Container engine recebe --cap-add=NET_ADMIN e sysctl
    - VPNManager conecta automaticamente antes dos testes
    - --vpn-rotate per-test rotaciona IP a cada teste

──────────────────────────────────────────────────────────────
DEPENDENCIAS
──────────────────────────────────────────────────────────────
  docker | podman      Container engine (ao menos um)
                       Docker: https://docs.docker.com/get-docker/
                       Podman: https://podman.io/docs/installation
                       Deteccao: docker tem prioridade; se ausente, usa podman
  uv                   UV package manager (somente se --rotate-posts)
                       https://docs.astral.sh/uv/
  Containerfile        Deve existir no diretorio do script
  tests/               Diretorio com roteiros pytest
  vpn/configs/*.conf   Configs WireGuard (somente se --enable-vpn)
                       Gerar em: https://mullvad.net/account/wireguard-config
  rotate-posts.py      Script de rotacao (somente se --rotate-posts)

──────────────────────────────────────────────────────────────
EVIDENCIAS
──────────────────────────────────────────────────────────────
  reports/report.html   Relatorio HTML interativo
  reports/videos/       Gravacao .webm de cada teste

USAGE
    exit 0
}

# Parse --help antes de tudo
case "${1:-}" in
    -h|--help) usage ;;
esac

execute_rotate_posts() {
    echo "🔄 Rotacionando posts do blog..."
    
    set +e
    local rotate_cmd=(uv run rotate-posts.py)
    rotate_cmd+=(--base-url="$BASE_URL")
    rotate_cmd+=(--min-posts="$MIN_POSTS")
    rotate_cmd+=(--max-posts="$MAX_POSTS")
    
    if [[ "$RESET_HIST" == true ]]; then
        rotate_cmd+=(--reset-hist)
    fi
    
    if [[ "$DRY_RUN_ROTATE" == true ]]; then
        rotate_cmd+=(--dry-run)
    fi
    
    rotate_cmd+=(--test-file="$SCRIPT_DIR/tests/test_blog_navigation.py")
    
    if ! "${rotate_cmd[@]}"; then
        echo "❌ Erro ao rotacionar posts" >&2
        set -e
        return 1
    fi
    
    set -e
    if [[ "$DRY_RUN_ROTATE" != true ]]; then
        echo "✅ Posts rotacionados com sucesso"
    fi
}


IMAGE_NAME="lzocateli/playwright-e2e:v0.1.0"
CONTAINER_NAME="e2e-runner"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detectar container runtime (docker tem prioridade)
if command -v docker &>/dev/null; then
    CONTAINER_RT="docker"
elif command -v podman &>/dev/null; then
    CONTAINER_RT="podman"
else
    CONTAINER_RT=""
fi

# Verificacao de dependencias
check_dependencies() {
    local missing=0

    if [ -z "$CONTAINER_RT" ]; then
        echo "❌ Nenhum container runtime encontrado (docker ou podman)" >&2
        echo "   Docker: https://docs.docker.com/get-docker/" >&2
        echo "   Podman: https://podman.io/docs/installation" >&2
        missing=1
    fi

    if [ ! -f "$SCRIPT_DIR/Containerfile" ]; then
        echo "❌ Containerfile nao encontrado em: $SCRIPT_DIR" >&2
        missing=1
    fi

    if [ ! -d "$SCRIPT_DIR/tests" ]; then
        echo "❌ Diretorio de testes nao encontrado: $SCRIPT_DIR/tests/" >&2
        missing=1
    fi

    if [[ "$ROTATE_POSTS" == true ]]; then
        if ! command -v uv &>/dev/null; then
            echo "❌ 'uv' nao encontrado (requerido para --rotate-posts)" >&2
            echo "   Instale em: https://docs.astral.sh/uv/" >&2
            missing=1
        fi
    fi

    if [ $missing -ne 0 ]; then
        echo "" >&2
        echo "Abortado. Corrija as dependencias acima antes de executar." >&2
        echo "Use '${PROGRAM} --help' para detalhes." >&2
        exit 1
    fi
}

echo "⚙️  Container runtime: $CONTAINER_RT"

BASE_URL="http://host.containers.internal:1313"
BROWSER=""
HUMAN_SPEED="normal"
ENABLE_VPN=false
VPN_ROTATE="off"
VPN_STRICT=false
FORCE_REBUILD=false
OPEN_REPORT=false
OPEN_FIRST_VIDEO=false
ROTATE_POSTS=false
MIN_POSTS=3
MAX_POSTS=6
RESET_HIST=false
DRY_RUN_ROTATE=false
EXTRA_PYTEST_ARGS=()

check_dependencies

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-url)     BASE_URL="$2"; shift 2 ;;
        --browser)      BROWSER="$2"; shift 2 ;;
        --human-speed)  HUMAN_SPEED="$2"; shift 2 ;;
        --enable-vpn)   ENABLE_VPN=true; shift ;;
        --vpn-rotate)   VPN_ROTATE="$2"; shift 2 ;;
        --vpn-strict)   VPN_STRICT=true; shift ;;
        --rebuild)
            FORCE_REBUILD=true
            $CONTAINER_RT rmi -f "$IMAGE_NAME" 2>/dev/null || true
            shift
            ;;
        --open-report)  OPEN_REPORT=true; shift ;;
        --open-first-video) OPEN_FIRST_VIDEO=true; shift ;;
        --rotate-posts) ROTATE_POSTS=true; shift ;;
        --min-posts)    MIN_POSTS="$2"; shift 2 ;;
        --max-posts)    MAX_POSTS="$2"; shift 2 ;;
        --reset-hist)   RESET_HIST=true; shift ;;
        --dry-run-rotate) DRY_RUN_ROTATE=true; shift ;;
        --)             shift; EXTRA_PYTEST_ARGS+=("$@"); break ;;
        *)              EXTRA_PYTEST_ARGS+=("$1"); shift ;;
    esac
done

# Pull/build da imagem (se nao existir)
image_exists() {
    if [ "$CONTAINER_RT" = "docker" ]; then
        docker image inspect "$IMAGE_NAME" &>/dev/null
    else
        podman image exists "$IMAGE_NAME"
    fi
}

if [[ "$FORCE_REBUILD" == true ]]; then
    echo "🔨 Reconstruindo imagem local $IMAGE_NAME ..."
    $CONTAINER_RT build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Containerfile" "$SCRIPT_DIR"
elif ! image_exists; then
    echo "📥 Baixando imagem $IMAGE_NAME ..."
    if ! $CONTAINER_RT pull "$IMAGE_NAME"; then
        echo "🔨 Imagem nao encontrada no registry; construindo localmente $IMAGE_NAME ..."
        $CONTAINER_RT build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Containerfile" "$SCRIPT_DIR"
    fi
fi

# Montar argumentos do pytest
PYTEST_ARGS=(
    "--base-url=$BASE_URL"
    "--human-speed=$HUMAN_SPEED"
)

# Selecionar browser aleatoriamente se nenhum foi especificado
if [[ -z "$BROWSER" ]]; then
    _BROWSERS=(chromium firefox webkit)
    BROWSER="${_BROWSERS[$((RANDOM % ${#_BROWSERS[@]}))]}"
fi

PYTEST_ARGS+=("--browser" "$BROWSER")

if [[ "$ENABLE_VPN" == true ]]; then
    PYTEST_ARGS+=("--enable-vpn" "--vpn-rotate=$VPN_ROTATE")
    if [[ "$VPN_STRICT" == true ]]; then
        PYTEST_ARGS+=("--vpn-strict")
    fi
fi

PYTEST_ARGS+=("${EXTRA_PYTEST_ARGS[@]}")

# Montar argumentos do container runtime
CONTAINER_ARGS=(
    run --rm
    --name "$CONTAINER_NAME"
)

# Podman usa slirp4netns; Docker usa bridge por padrao
if [ "$CONTAINER_RT" = "podman" ]; then
    CONTAINER_ARGS+=(--network slirp4netns)
fi

# Bind volume total: código-fonte montado do host (sem COPY na imagem).
# Flags :Z removidas para compatibilidade cross-platform (Docker Desktop / WSL2).
CONTAINER_ARGS+=(
    -v "$SCRIPT_DIR/reports:/app/reports"
    -v "$SCRIPT_DIR/tests:/app/tests:ro"
    -v "$SCRIPT_DIR/conftest.py:/app/conftest.py:ro"
    -v "$SCRIPT_DIR/vpn/__init__.py:/app/vpn/__init__.py:ro"
    -v "$SCRIPT_DIR/vpn/vpn_manager.py:/app/vpn/vpn_manager.py:ro"
    -v "$SCRIPT_DIR/vpn/conftest_vpn.py:/app/vpn/conftest_vpn.py:ro"
    -v "$SCRIPT_DIR/vpn/configs:/app/vpn/configs:ro"
)

if [[ "$ENABLE_VPN" == true ]]; then
    if [ ! -d "$SCRIPT_DIR/vpn/configs" ] || [ -z "$(ls -A "$SCRIPT_DIR/vpn/configs/"*.conf 2>/dev/null)" ]; then
        echo "❌ VPN habilitada mas nenhum .conf encontrado em: $SCRIPT_DIR/vpn/configs/" >&2
        echo "   Gerar em: https://mullvad.net/account/wireguard-config" >&2
        echo "   Use '${PROGRAM} --help' para detalhes." >&2
        exit 1
    fi
    echo "🔐 VPN habilitada — adicionando NET_ADMIN + sysctl"
    CONTAINER_ARGS+=(
        --cap-add=NET_ADMIN
        --sysctl net.ipv4.conf.all.src_valid_mark=1
    )
fi

# Executar
echo "🚀 Executando testes E2E..."
echo "   Runtime:        $CONTAINER_RT"
echo "   URL:            $BASE_URL"
echo "   Speed:          $HUMAN_SPEED"
echo "   VPN:            $ENABLE_VPN (rotate: $VPN_ROTATE)"
echo "   VPN strict:     $VPN_STRICT"
echo "   Browser:        $BROWSER"
echo "   Rotate posts:   $ROTATE_POSTS (dry-run: $DRY_RUN_ROTATE)"
echo ""

if [[ "$ROTATE_POSTS" == true ]]; then
    execute_rotate_posts
fi

echo ""

$CONTAINER_RT "${CONTAINER_ARGS[@]}" "$IMAGE_NAME" "${PYTEST_ARGS[@]}"

echo ""
echo "📊 Relatório: $SCRIPT_DIR/reports/report.html"
echo "🎬 Vídeos:    $SCRIPT_DIR/reports/videos"

if [[ "$OPEN_REPORT" == true ]]; then
    REPORT_PATH="$SCRIPT_DIR/reports/report.html"

    if [[ -f "$REPORT_PATH" ]]; then
        if command -v xdg-open &>/dev/null; then
            xdg-open "$REPORT_PATH" >/dev/null 2>&1 || true
        elif command -v wslview &>/dev/null; then
            wslview "$REPORT_PATH" >/dev/null 2>&1 || true
        elif command -v powershell.exe &>/dev/null && command -v wslpath &>/dev/null; then
            WIN_REPORT_PATH="$(wslpath -w "$REPORT_PATH")"
            powershell.exe -NoProfile -Command "Start-Process -FilePath '$WIN_REPORT_PATH'" >/dev/null 2>&1 || true
        else
            echo "⚠️  Nao foi possivel abrir automaticamente. Abra manualmente: $REPORT_PATH"
        fi
    else
        echo "⚠️  Relatorio nao encontrado em: $REPORT_PATH"
    fi
fi

if [[ "$OPEN_FIRST_VIDEO" == true ]]; then
    VIDEOS_PATH="$SCRIPT_DIR/reports/videos"
    FIRST_VIDEO=""

    if [[ -d "$VIDEOS_PATH" ]]; then
        for video in "$VIDEOS_PATH"/*.webm; do
            if [[ -f "$video" ]]; then
                FIRST_VIDEO="$video"
                break
            fi
        done
    fi

    if [[ -n "$FIRST_VIDEO" ]]; then
        if command -v xdg-open &>/dev/null; then
            xdg-open "$FIRST_VIDEO" >/dev/null 2>&1 || true
        elif command -v wslview &>/dev/null; then
            wslview "$FIRST_VIDEO" >/dev/null 2>&1 || true
        elif command -v powershell.exe &>/dev/null && command -v wslpath &>/dev/null; then
            WIN_VIDEO_PATH="$(wslpath -w "$FIRST_VIDEO")"
            powershell.exe -NoProfile -Command "Start-Process -FilePath '$WIN_VIDEO_PATH'" >/dev/null 2>&1 || true
        else
            echo "⚠️  Nao foi possivel abrir automaticamente o primeiro vídeo. Abra manualmente: $FIRST_VIDEO"
        fi
    else
        echo "⚠️  Nenhum .webm encontrado em: $VIDEOS_PATH"
    fi
fi
