"""Executa testes E2E com Playwright via Docker ou Podman.

Wrapper multiplataforma (Linux, macOS, Windows) que substitui run-e2e.sh.
Detecta automaticamente docker ou podman e gerencia pull/build da imagem.
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

VERSION = "0.1.0"
PROGRAM = "e2e"
IMAGE_NAME = "lzocateli/playwright-e2e:v0.1.0"
CONTAINER_NAME = "e2e-runner"

# Raiz do projeto: src/e2e/run_e2e.py → parents[2] = raiz do projeto
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def detect_runtime() -> str | None:
    """Detecta docker ou podman (docker tem prioridade)."""
    if shutil.which("docker"):
        return "docker"
    if shutil.which("podman"):
        return "podman"
    return None


def check_dependencies(args: argparse.Namespace, container_rt: str | None) -> None:
    """Valida pré-requisitos antes de executar."""
    missing = False

    if container_rt is None:
        print(
            "❌ Nenhum container runtime encontrado (docker ou podman)", file=sys.stderr
        )
        print("   Docker: https://docs.docker.com/get-docker/", file=sys.stderr)
        print("   Podman: https://podman.io/docs/installation", file=sys.stderr)
        missing = True

    if not (_PROJECT_ROOT / "Containerfile").is_file():
        print(f"❌ Containerfile não encontrado em: {_PROJECT_ROOT}", file=sys.stderr)
        missing = True

    if not (_PROJECT_ROOT / "tests").is_dir():
        print(
            f"❌ Diretório de testes não encontrado: {_PROJECT_ROOT / 'tests'}",
            file=sys.stderr,
        )
        missing = True

    if args.rotate_posts and not shutil.which("uv"):
        print("❌ 'uv' não encontrado (requerido para --rotate-posts)", file=sys.stderr)
        print("   Instale em: https://docs.astral.sh/uv/", file=sys.stderr)
        missing = True

    if missing:
        print("", file=sys.stderr)
        print(
            "Abortado. Corrija as dependências acima antes de executar.",
            file=sys.stderr,
        )
        print(f"Use '{PROGRAM} --help' para detalhes.", file=sys.stderr)
        sys.exit(1)


def image_exists(container_rt: str) -> bool:
    """Verifica se a imagem já existe localmente."""
    if container_rt == "docker":
        result = subprocess.run(
            ["docker", "image", "inspect", IMAGE_NAME],
            capture_output=True,
        )
    else:
        result = subprocess.run(
            ["podman", "image", "exists", IMAGE_NAME],
            capture_output=True,
        )
    return result.returncode == 0


def execute_rotate_posts(args: argparse.Namespace) -> None:
    """Rotaciona posts do blog chamando o entry point rotate-posts."""
    print("🔄 Rotacionando posts do blog...")
    cmd = [
        "uv",
        "run",
        "rotate-posts",
        f"--base-url={args.base_url}",
        f"--min-posts={args.min_posts}",
        f"--max-posts={args.max_posts}",
    ]
    if args.reset_hist:
        cmd.append("--reset-hist")
    if args.dry_run_rotate:
        cmd.append("--dry-run")

    result = subprocess.run(cmd, cwd=str(_PROJECT_ROOT))
    if result.returncode != 0:
        print("❌ Erro ao rotacionar posts", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run_rotate:
        print("✅ Posts rotacionados com sucesso")


def _mount(src: Path, dst: str, readonly: bool = False) -> str:
    """Formata argumento de bind mount usando posix path (compatível com Docker Desktop no Windows)."""
    flag = ":ro" if readonly else ""
    return f"{src.as_posix()}:{dst}{flag}"


def build_pytest_args(args: argparse.Namespace, browser: str) -> list[str]:
    """Constrói a lista de argumentos para o pytest."""
    pytest_args = [
        f"--base-url={args.base_url}",
        f"--human-speed={args.human_speed}",
        "--browser",
        browser,
    ]
    if args.enable_vpn:
        pytest_args += ["--enable-vpn", f"--vpn-rotate={args.vpn_rotate}"]
        if args.vpn_strict:
            pytest_args.append("--vpn-strict")
    pytest_args += args.extra_pytest_args
    return pytest_args


def build_container_args(args: argparse.Namespace, container_rt: str) -> list[str]:
    """Constrói a lista de argumentos para docker/podman run."""
    container_args = ["run", "--rm", "--name", CONTAINER_NAME]

    # Podman no Linux usa slirp4netns; no macOS/Windows usa VM própria com bridge
    if container_rt == "podman" and sys.platform == "linux":
        container_args += ["--network", "slirp4netns"]

    # Bind mounts: código montado em runtime, sem necessidade de rebuild
    container_args += [
        "-v",
        _mount(_PROJECT_ROOT / "reports", "/app/reports"),
        "-v",
        _mount(_PROJECT_ROOT / "tests", "/app/tests", readonly=True),
        "-v",
        _mount(_PROJECT_ROOT / "src" / "e2e", "/app/src/e2e", readonly=True),
        "-v",
        _mount(_PROJECT_ROOT / "src" / "vpn", "/app/src/vpn", readonly=True),
        "-v",
        _mount(_PROJECT_ROOT / "vpn" / "configs", "/app/vpn/configs", readonly=True),
    ]

    if args.enable_vpn:
        vpn_configs = _PROJECT_ROOT / "vpn" / "configs"
        if not vpn_configs.is_dir() or not list(vpn_configs.glob("*.conf")):
            print(
                f"❌ VPN habilitada mas nenhum .conf encontrado em: {vpn_configs}",
                file=sys.stderr,
            )
            print(
                "   Gerar em: https://mullvad.net/account/wireguard-config",
                file=sys.stderr,
            )
            print(f"   Use '{PROGRAM} --help' para detalhes.", file=sys.stderr)
            sys.exit(1)
        print("🔐 VPN habilitada — adicionando NET_ADMIN + sysctl")
        container_args += [
            "--cap-add=NET_ADMIN",
            "--sysctl",
            "net.ipv4.conf.all.src_valid_mark=1",
        ]

    return container_args


def open_path(path: Path) -> None:
    """Abre um arquivo com o programa padrão do sistema operacional."""
    if not path.exists():
        print(f"⚠️  Arquivo não encontrado: {path}")
        return
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as exc:
        print(f"⚠️  Não foi possível abrir automaticamente: {path} — {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(f"""\
            {PROGRAM} v{VERSION}

            Wrapper para executar testes E2E com Playwright via Docker ou Podman.
            Baixa a imagem publicada automaticamente (se necessário) e executa os testes
            dentro do container com suporte a VPN, simulação humana e multi-browser.
            Se a imagem não estiver disponível no registry, faz o build local.

            O script detecta automaticamente docker ou podman (nesta ordem).

            ──────────────────────────────────────────────────────────────
            SINTAXE
            ──────────────────────────────────────────────────────────────
              uv run {PROGRAM} [opcoes] [-- pytest-args]
              uv run {PROGRAM} -h | --help                Esta mensagem

            ──────────────────────────────────────────────────────────────
            EXEMPLOS
            ──────────────────────────────────────────────────────────────
              uv run {PROGRAM}                                    Básico, sem VPN
              uv run {PROGRAM} --base-url https://zocate.li       Site em produção
              uv run {PROGRAM} --enable-vpn --human-speed slow    VPN + delays longos
              uv run {PROGRAM} --enable-vpn --vpn-rotate per-test Rotação VPN por teste
              uv run {PROGRAM} --enable-vpn --vpn-strict          Falha se saída não for Mullvad
              uv run {PROGRAM} --browser chromium                 Browser específico
              uv run {PROGRAM} --rebuild --base-url https://z.li  Reconstrói imagem
              uv run {PROGRAM} --open-report                      Abre relatório ao finalizar
              uv run {PROGRAM} --open-first-video                 Abre o primeiro .webm
              uv run {PROGRAM} --rotate-posts                     Rotaciona posts antes dos testes
              uv run {PROGRAM} --rotate-posts --dry-run-rotate    Preview da rotação sem aplicar
              uv run {PROGRAM} -- -k test_home                    Filtra testes pytest

            ──────────────────────────────────────────────────────────────
            OPCOES
            ──────────────────────────────────────────────────────────────
              --base-url URL       URL do site a testar
                                   Default: http://host.containers.internal:1313
              --browser BROWSER    chromium | firefox | webkit
                                   Default: aleatório (escolhido automaticamente)
              --human-speed SPEED  slow (2x) | normal (1x) | fast (0.3x)
                                   Default: normal
              --enable-vpn         Ativa VPN WireGuard (requer configs em vpn/configs/)
              --vpn-rotate MODE    per-test | per-session | off (default: off)
              --vpn-strict         Falha se a saída não for Mullvad
              --rebuild            Remove e reconstrói a imagem antes de executar
              --open-report        Abre reports/report.html ao finalizar
              --open-first-video   Abre o primeiro .webm em reports/videos ao finalizar
              --rotate-posts       Rotaciona artigos do blog antes dos testes
              --min-posts N        Posts mínimos a selecionar (default: 3)
              --max-posts N        Posts máximos a selecionar (default: 6)
              --reset-hist         Limpa BLOG_POSTS_HIST (requer --rotate-posts)
              --dry-run-rotate     Preview da rotação sem alterar arquivo (requer --rotate-posts)
              --                   Tudo após '--' é passado diretamente ao pytest
        """),
    )
    parser.add_argument(
        "--base-url",
        default="http://host.containers.internal:1313",
        help="URL do site a testar (default: http://host.containers.internal:1313)",
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default=None,
        help="Browser a usar (default: aleatório)",
    )
    parser.add_argument(
        "--human-speed",
        choices=["slow", "normal", "fast"],
        default="normal",
        help="Intensidade dos delays (default: normal)",
    )
    parser.add_argument(
        "--enable-vpn",
        action="store_true",
        help="Ativa VPN WireGuard",
    )
    parser.add_argument(
        "--vpn-rotate",
        choices=["per-test", "per-session", "off"],
        default="off",
        help="Rotação de VPN (default: off)",
    )
    parser.add_argument(
        "--vpn-strict",
        action="store_true",
        help="Falha se a saída não for Mullvad",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Remove e reconstrói a imagem antes de executar",
    )
    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Abre reports/report.html ao finalizar",
    )
    parser.add_argument(
        "--open-first-video",
        action="store_true",
        help="Abre o primeiro .webm em reports/videos ao finalizar",
    )
    parser.add_argument(
        "--rotate-posts",
        action="store_true",
        help="Rotaciona artigos do blog antes dos testes (requer uv)",
    )
    parser.add_argument(
        "--min-posts",
        type=int,
        default=3,
        help="Posts mínimos a selecionar (default: 3)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=6,
        help="Posts máximos a selecionar (default: 6)",
    )
    parser.add_argument(
        "--reset-hist",
        action="store_true",
        help="Limpa BLOG_POSTS_HIST antes de rotacionar (requer --rotate-posts)",
    )
    parser.add_argument(
        "--dry-run-rotate",
        action="store_true",
        help="Preview da rotação sem alterar arquivo (requer --rotate-posts)",
    )
    parser.add_argument(
        "extra_pytest_args",
        nargs=argparse.REMAINDER,
        help="Argumentos adicionais passados diretamente ao pytest (após --)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Strip leading '--' separator vindo de `uv run e2e -- -k test_home`
    if args.extra_pytest_args and args.extra_pytest_args[0] == "--":
        args.extra_pytest_args = args.extra_pytest_args[1:]

    container_rt = detect_runtime()
    print(f"⚙️  Container runtime: {container_rt or 'não encontrado'}")

    check_dependencies(args, container_rt)

    # --rebuild: remove imagem primeiro
    if args.rebuild:
        print(f"🔨 Removendo imagem {IMAGE_NAME} ...")
        subprocess.run([container_rt, "rmi", "-f", IMAGE_NAME], capture_output=True)
        print(f"🔨 Reconstruindo imagem local {IMAGE_NAME} ...")
        subprocess.run(
            [
                container_rt,
                "build",
                "-t",
                IMAGE_NAME,
                "-f",
                str(_PROJECT_ROOT / "Containerfile"),
                str(_PROJECT_ROOT),
            ],
            check=True,
        )
    elif not image_exists(container_rt):
        print(f"📥 Baixando imagem {IMAGE_NAME} ...")
        result = subprocess.run([container_rt, "pull", IMAGE_NAME])
        if result.returncode != 0:
            print(
                f"🔨 Imagem não encontrada no registry; construindo localmente {IMAGE_NAME} ..."
            )
            subprocess.run(
                [
                    container_rt,
                    "build",
                    "-t",
                    IMAGE_NAME,
                    "-f",
                    str(_PROJECT_ROOT / "Containerfile"),
                    str(_PROJECT_ROOT),
                ],
                check=True,
            )

    # Rotacionar posts antes dos testes
    if args.rotate_posts:
        execute_rotate_posts(args)
        print()

    # Selecionar browser
    browser = args.browser or random.choice(["chromium", "firefox", "webkit"])

    pytest_args = build_pytest_args(args, browser)
    container_args = build_container_args(args, container_rt)

    print("🚀 Executando testes E2E...")
    print(f"   Runtime:        {container_rt}")
    print(f"   URL:            {args.base_url}")
    print(f"   Speed:          {args.human_speed}")
    print(f"   VPN:            {args.enable_vpn} (rotate: {args.vpn_rotate})")
    print(f"   VPN strict:     {args.vpn_strict}")
    print(f"   Browser:        {browser}")
    print(f"   Rotate posts:   {args.rotate_posts} (dry-run: {args.dry_run_rotate})")
    print()

    subprocess.run(
        [container_rt] + container_args + [IMAGE_NAME] + pytest_args,
        check=False,
    )

    print()
    print(f"📊 Relatório: {_PROJECT_ROOT / 'reports' / 'report.html'}")
    print(f"🎬 Vídeos:    {_PROJECT_ROOT / 'reports' / 'videos'}")

    if args.open_report:
        open_path(_PROJECT_ROOT / "reports" / "report.html")

    if args.open_first_video:
        videos_dir = _PROJECT_ROOT / "reports" / "videos"
        first_video = (
            next(videos_dir.glob("*.webm"), None) if videos_dir.is_dir() else None
        )
        if first_video:
            open_path(first_video)
        else:
            print(f"⚠️  Nenhum .webm encontrado em: {videos_dir}")


if __name__ == "__main__":
    main()
