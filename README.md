# playwright-e2e

Ferramenta genérica de testes E2E com [Playwright](https://playwright.dev/) + [pytest](https://pytest.org/), rodando em container [Docker](https://docs.docker.com/get-docker/) ou [Podman](https://podman.io/) rootless.

## Funcionalidades

- **Multi-browser**: Chromium, Firefox e WebKit (selecionado aleatoriamente se não especificado)
- **Simulação humana**: delays configuráveis entre ações (`slow_page`, `human_delay`)
- **VPN integrada**: Mullvad/WireGuard para simular conexões de locais diferentes
- **Rotação de VPN**: por teste, por sessão, ou desligado
- **Rotação de artigos**: atualiza automaticamente os posts testados via sitemap
- **Relatórios**: HTML com vídeos gravados de cada teste
- **Container**: Docker ou Podman, com bind mounts — sem rebuild para mudanças no código
- **Multiplataforma**: Linux, macOS e Windows nativo (sem WSL2)

## Estrutura

```text
playwright-e2e/
├── pyproject.toml              # Dependências, entry points e configuração pytest (uv)
├── Containerfile               # Imagem com Playwright + WireGuard
├── src/
│   ├── e2e/
│   │   ├── run_e2e.py          # Programa principal: executa os testes via container
│   │   └── rotate_posts.py     # Rotação automática de artigos via sitemap
│   └── vpn/
│       ├── vpn_manager.py      # Classe VPNManager (connect/disconnect/rotate)
│       └── conftest_vpn.py     # Plugin pytest para VPN
├── tests/
│   ├── conftest.py             # Fixtures: slow_page, human_delay, browser context
│   ├── test_blog_navigation.py # Navegação no blog com simulação de leitura
│   ├── test_seo_live.py        # Verificações SEO em produção
│   └── test_sample_generic.py  # Template genérico para novos roteiros
├── vpn/
│   └── configs/                # Arquivos .conf WireGuard (gitignored)
└── reports/                    # Relatórios HTML + vídeos (gitignored)
```

## Programas

### `uv run e2e` — Executor de testes

Wrapper multiplataforma que gerencia o ciclo completo de execução:

1. Detecta automaticamente `docker` ou `podman` (docker tem prioridade)
2. Baixa a imagem `lzocateli/playwright-e2e:v0.1.0` do registry na primeira execução; se não existir no registry, faz o build local a partir do `Containerfile`
3. Monta `tests/`, `src/e2e/`, `src/vpn/` e `vpn/configs/` como bind volumes — qualquer alteração local é refletida imediatamente, sem necessidade de `--rebuild`
4. Rotaciona artigos do blog (opcional, via `--rotate-posts`)
5. Executa `pytest` dentro do container com os parâmetros configurados
6. Exibe o caminho do relatório e abre automaticamente (se `--open-report` ou `--open-first-video`)

### `uv run rotate-posts` — Rotação de artigos

Utilitário para diversificar os artigos testados a cada execução:

1. Busca `sitemap.xml` no site configurado e extrai URLs de `/posts/`
2. Lê `BLOG_POSTS` e `BLOG_POSTS_HIST` do arquivo `tests/test_blog_navigation.py`
3. Move `BLOG_POSTS` atual para `BLOG_POSTS_HIST` (acumula histórico)
4. Seleciona aleatoriamente N artigos novos (que ainda não estão no histórico)
5. Grava os novos `BLOG_POSTS` e `BLOG_POSTS_HIST` no arquivo de teste
6. Quando todos os artigos já estiverem no histórico, recicla os mais antigos automaticamente

Use `--dry-run` para ver o que mudaria sem alterar o arquivo.

> **Fluxo recomendado**: `uv run e2e --rotate-posts --base-url https://seusite.com` — rotaciona e testa em uma única invocação.

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/) — gerenciador de pacotes e task runner (requerido)
- [Docker](https://docs.docker.com/get-docker/) ou [Podman](https://podman.io/) — container runtime
- **Opcional**: Conta [Mullvad VPN](https://mullvad.net/) com configs WireGuard em `vpn/configs/`

> `uv` gerencia o Python e todas as dependências automaticamente. Não é necessário instalar Python, browsers ou outras dependências manualmente.
> O código-fonte é montado via bind volume no runtime — qualquer alteração local em testes ou fixtures é refletida imediatamente, sem necessidade de `--rebuild`.

## Instalação do projeto

```bash
git clone https://github.com/lzocateli/playwright-e2e.git
cd playwright-e2e
uv sync
```

## Instalando uv

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Após instalar, adicione ao PATH se necessário:

```bash
# Adicione ao ~/.bashrc, ~/.zshrc ou ~/.profile
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

Via package manager:

```bash
brew install uv          # macOS (Homebrew)
sudo apt-get install uv  # Ubuntu/Debian
sudo dnf install uv      # Fedora/RHEL
sudo pacman -S uv        # Arch
```

### Windows (nativo)

```powershell
# Via winget
winget install --id=astral-sh.uv -e

# Via Scoop
scoop install uv

# Ou via PowerShell (instalador oficial)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Verificar instalação

```bash
uv --version
```

## Execução

```bash
# Básico — sem VPN, velocidade normal, browser aleatório
uv run e2e --base-url https://zocate.li

# Com simulação humana lenta
uv run e2e --base-url https://zocate.li --human-speed slow

# Browser específico
uv run e2e --base-url https://zocate.li --browser chromium

# Com VPN (requer configs em vpn/configs/)
uv run e2e --base-url https://zocate.li --enable-vpn

# VPN com rotação por teste + velocidade lenta
uv run e2e --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed slow

# VPN estrita (falha se saída não for Mullvad)
uv run e2e --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --vpn-strict

# Reconstruir imagem (após atualização do Containerfile)
uv run e2e --rebuild --base-url https://zocate.li

# Abrir relatório automaticamente ao finalizar
uv run e2e --open-report --base-url https://zocate.li

# Abrir o primeiro vídeo (.webm) ao finalizar
uv run e2e --open-first-video --base-url https://zocate.li

# Rotacionar posts do blog antes dos testes
uv run e2e --base-url https://zocate.li --rotate-posts

# Rotacionar posts com range customizado
uv run e2e --base-url https://zocate.li --rotate-posts --min-posts 2 --max-posts 5

# Preview da rotação (sem alterar arquivo de teste)
uv run e2e --base-url https://zocate.li --rotate-posts --dry-run-rotate

# Rotacionar + limpar histórico
uv run e2e --base-url https://zocate.li --rotate-posts --reset-hist

# Passar argumentos extras ao pytest (após --)
uv run e2e --base-url https://zocate.li -- -k test_home

# Execução completa (VPN + rotação + relatório + vídeo)
uv run e2e --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed normal --vpn-strict --open-report --open-first-video --rotate-posts -- tests/test_blog_navigation.py
```

## Opções CLI (`uv run e2e`)

| Opção | Valores | Default | Descrição |
|---|---|---|---|
| `--base-url` | URL | `http://host.containers.internal:1313` | URL base do site a testar |
| `--browser` | `chromium`, `firefox`, `webkit` | aleatório | Browser específico |
| `--human-speed` | `slow`, `normal`, `fast` | `normal` | Intensidade dos delays humanos |
| `--enable-vpn` | flag | desligado | Ativa conexão VPN WireGuard |
| `--vpn-rotate` | `per-test`, `per-session`, `off` | `off` | Quando rotacionar VPN |
| `--vpn-strict` | flag | desligado | Falha se `mullvad_exit_ip` não for verdadeiro |
| `--rebuild` | flag | desligado | Remove e reconstrói a imagem antes de executar |
| `--open-report` | flag | desligado | Abre `reports/report.html` ao finalizar |
| `--open-first-video` | flag | desligado | Abre o primeiro `.webm` de `reports/videos` |
| `--rotate-posts` | flag | desligado | Rotaciona artigos do blog antes dos testes |
| `--min-posts` | inteiro | `3` | Posts mínimos a selecionar (com `--rotate-posts`) |
| `--max-posts` | inteiro | `6` | Posts máximos a selecionar (com `--rotate-posts`) |
| `--reset-hist` | flag | desligado | Limpa histórico de posts (com `--rotate-posts`) |
| `--dry-run-rotate` | flag | desligado | Preview da rotação sem alterar arquivo |
| `--` | — | — | Tudo após `--` é passado diretamente ao pytest |

### Multiplicadores de velocidade

| Speed | Multiplicador | Delay padrão (2-8s) | Resultado |
|---|---|---|---|
| `slow` | 2.0x | 4-16s | Simula leitura atenta |
| `normal` | 1.0x | 2-8s | Navegação natural |
| `fast` | 0.3x | 0.6-2.4s | Teste rápido |

## Rotação de artigos (`uv run rotate-posts`)

```bash
# Ver o que mudaria (sem alterar arquivo)
uv run rotate-posts --dry-run

# Rotação padrão (3-6 artigos novos)
uv run rotate-posts

# Range customizado
uv run rotate-posts --min-posts 3 --max-posts 6

# Site diferente do default
uv run rotate-posts --base-url https://zocate.li

# Todos os parâmetros
uv run rotate-posts --base-url https://zocate.li --min-posts 3 --max-posts 6 --test-file tests/test_blog_navigation.py

# Limpar histórico e começar do zero
uv run rotate-posts --reset-hist
```

### Opções CLI (`uv run rotate-posts`)

| Opção | Valores | Default | Descrição |
|---|---|---|---|
| `--base-url` | URL | `https://zocate.li` | URL base do site (para buscar `sitemap.xml`) |
| `--min-posts` | inteiro | `3` | Mínimo de artigos a selecionar |
| `--max-posts` | inteiro | `6` | Máximo de artigos a selecionar |
| `--dry-run` | flag | desligado | Exibe o que mudaria sem alterar o arquivo |
| `--reset-hist` | flag | desligado | Limpa `BLOG_POSTS_HIST` antes de rotacionar |
| `--test-file` | caminho | auto-detectado | Caminho para `test_blog_navigation.py` |

## Fixtures disponíveis

### `slow_page`

Page com delays automáticos:

```python
def test_exemplo(slow_page, base_url):
    slow_page.goto(base_url)          # + sleep 3-8s
    slow_page.click("a.link")         # + sleep 1-4s
    slow_page.scroll_down(500)        # + sleep 2-5s
    slow_page.scroll_to_bottom()      # scroll progressivo com pausas
    slow_page.wait_reading()          # sleep 15-45s (simulando leitura)
    slow_page.fill("input", "texto")  # + sleep 0.5-2s
    slow_page.page.title()            # acesso direto ao Page original
```

### `human_delay`

Função para delays manuais:

```python
def test_exemplo(human_delay):
    human_delay()                      # 2-8s (default)
    human_delay(min_s=10, max_s=30)    # leitura longa
    human_delay(min_s=1, max_s=3)      # entre cliques
```

### `base_url`

URL base configurável via `--base-url`.

## Setup VPN (Mullvad/WireGuard)

### 1. Criar conta no Mullvad

1. Acesse [https://mullvad.net/en/account/create](https://mullvad.net/en/account/create)
2. O Mullvad gera um **número de conta de 16 dígitos** (sem email/senha) — **anote esse número**, é sua única forma de login
3. Adicione tempo à conta (€5/mês — aceita cartão, cripto, PayPal e até cash por carta)

### 2. Gerar configs WireGuard

1. Faça login em [https://mullvad.net/en/account/login](https://mullvad.net/en/account/login) com seu número de 16 dígitos
2. Acesse o gerador de configs: [https://mullvad.net/en/account/wireguard-config](https://mullvad.net/en/account/wireguard-config)
3. **Select one or multiple exit locations** — selecione país, cidade e servidor:
   - Primeiro dropdown: **Country** (ex: Brazil)
   - Segundo dropdown: **City** (ex: All cities ou uma cidade específica)
   - Terceiro dropdown: **Server** (ex: All servers ou um servidor específico)
4. **Advanced settings** — mantenha os padrões:
   - **Multihop**: desmarcado
   - **Server connection protocol**: **IPv4**
   - **Tunnel traffic**: **Both**
   - **Custom port**: `51820` (padrão)
   - **Enable kill switch (Linux only)**: desmarcado (o container cuida do isolamento)
5. **Configure Content Blocking** — clique **None** (sem bloqueio, para não interferir nos testes)
6. Clique **Download zip archive** — baixa um `.zip` com os `.conf` de todos os servidores da localização selecionada

Repita os passos 3-6 para cada país/localização desejada.

#### Localizações configuradas

Selecione cada país/cidade no dropdown e baixe o zip:

| Zip baixado | País / Cidade | Servidores gerados |
|---|---|---|
| `mullvad_wireguard_linux_br_all.zip` | 🇧🇷 Brazil (all) | `br-sao-wg-*.conf` |
| `mullvad_wireguard_linux_us_nyc.zip` | 🇺🇸 USA — New York | `us-nyc-wg-*.conf` |
| `mullvad_wireguard_linux_us_dal.zip` | 🇺🇸 USA — Dallas | `us-dal-wg-*.conf` |
| `mullvad_wireguard_linux_ar_bue.zip` | 🇦🇷 Argentina — Buenos Aires | `ar-bue-wg-*.conf` |
| `mullvad_wireguard_linux_cl_scl.zip` | 🇨🇱 Chile — Santiago | `cl-scl-wg-*.conf` |
| `mullvad_wireguard_linux_co_bog.zip` | 🇨🇴 Colombia — Bogotá | `co-bog-wg-*.conf` |
| `mullvad_wireguard_linux_pe_lim.zip` | 🇵🇪 Peru — Lima | `pe-lim-wg-*.conf` |
| `mullvad_wireguard_linux_pt_lis.zip` | 🇵🇹 Portugal — Lisboa | `pt-lis-wg-*.conf` |

> **Dica**: O zip vem com vários `.conf` (um por servidor do país). Você pode manter todos ou escolher apenas alguns. O `VPNManager` rotaciona automaticamente entre todos os `.conf` disponíveis na pasta.
>
> Se for rodar WireGuard em múltiplos dispositivos, gere uma chave separada para cada um. Usar a mesma chave em dispositivos diferentes causa problemas de conectividade.

### 3. Extrair os `.conf` para o projeto

```powershell
# Windows — extrair os zips baixados e mover os .conf para vpn/configs/
mkdir -Force vpn\configs

# Extrair cada zip (Expand-Archive não aceita wildcard, precisa de loop)
Get-ChildItem ~\Downloads\mullvad_wireguard_*.zip | ForEach-Object {
    Expand-Archive $_.FullName -DestinationPath ~\Downloads\mullvad_wg_temp -Force
}
Move-Item ~\Downloads\mullvad_wg_temp\*.conf vpn\configs\
Remove-Item ~\Downloads\mullvad_wg_temp -Recurse

# Verificar
Get-ChildItem vpn\configs\*.conf
```

```bash
# Linux — extrair os zips e mover os .conf para vpn/configs/
mkdir -p vpn/configs
cd ~/Downloads
for zip in mullvad_wireguard_*.zip; do unzip -o "$zip" -d vpn_temp; done
mv vpn_temp/*.conf /caminho/para/playwright-e2e/vpn/configs/
rm -rf vpn_temp

# Verificar
ls vpn/configs/*.conf
```

### 4. Rodar testes com VPN

```bash
uv run e2e --base-url https://zocate.li --enable-vpn --vpn-rotate per-test

# Verificar nos logs: "VPN sessão iniciada — Local: br-sao | IP: x.x.x.x"
```

## Criando novos roteiros de teste

1. Copie `tests/test_sample_generic.py` como base
2. Renomeie para `tests/test_<seu_cenario>.py`
3. Use as fixtures `slow_page` e `human_delay`
4. Execute via container:

   ```bash
   uv run e2e --base-url https://seusite.com -- tests/test_<seu_cenario>.py
   ```

Exemplo mínimo:

```python
def test_meu_cenario(slow_page, base_url, human_delay):
    slow_page.goto(base_url)
    slow_page.scroll_to_bottom()
    human_delay(min_s=5, max_s=15)
    assert slow_page.page.title()
```

## Evidências

Após execução, confira em `reports/`:

- `report.html` — Relatório HTML interativo
- `videos/` — Gravação de cada teste (.webm)

Quando VPN está ativa, o relatório também inclui contexto da VPN por teste:

- Local (`.conf`) usado no teste
- IP observado
- Indicador `Mullvad Exit` (`true`/`false`)

> **Importante**: para ver a lista completa de testes (pass/fail/skipped), abra o `report.html` no navegador do sistema.
> O preview interno do VS Code pode desabilitar scripts e ocultar a tabela de resultados.

## Troubleshooting

| Problema | Solução |
|---|---|
| `wg-quick: command not found` | Reconstruir imagem: `uv run e2e --rebuild` |
| VPN sem conectar no Podman | Verificar `--cap-add=NET_ADMIN` e `--sysctl` nos logs |
| Browser timeout | Aumentar timeout: `-- --timeout 60000` |
| Imagem desatualizada | Usar `uv run e2e --rebuild` |
| Vídeos não gravados | Confirmar que `reports/videos/` foi criado após execução |
| Alterações em testes não refletidas | O bind volume monta o código do host automaticamente — `--rebuild` não é necessário para mudanças em `tests/` ou `src/` |
| `sd-bus call: Permission denied` no build (WSL2) | Ver seção abaixo |
| Container runtime não encontrado | Instalar Docker ou Podman; no Windows, Docker Desktop é recomendado |

### Build falha com `sd-bus call: Permission denied` no WSL2

Ocorre quando o WSL2 não tem systemd ativo. O Podman tenta usar o cgroup manager `systemd`, não encontra sessão disponível e o `crun` falha ao criar o container de build.

**Solução permanente** — habilitar systemd no WSL2:

```bash
sudo nano /etc/wsl.conf
```

Adicione (ou edite):

```ini
[boot]
systemd=true
```

Reinicie a distro no PowerShell do Windows:

```powershell
wsl --shutdown
```

Abra o WSL novamente e confirme:

```bash
systemctl --no-pager status
# State: running  →  OK
```

**Workaround imediato** (sem precisar reiniciar) — faça o build manualmente forçando `cgroupfs`:

```bash
BUILDAH_ISOLATION=chroot podman build --cgroup-manager=cgroupfs -t lzocateli/playwright-e2e:v0.1.0 -f Containerfile .
```

Após o build, `uv run e2e` detecta que a imagem já existe e executa normalmente.

### `docker save` falha com `reference does not exist`

Se o erro acontecer, a tag informada no `docker save` não existe localmente.

No Windows, liste as imagens disponíveis:

```powershell
docker images | Select-String "playwright-e2e|playwright"
```

Se existir apenas a imagem `vsc-playwright-e2e-...:latest`, crie a tag esperada pelo script:

```powershell
docker tag vsc-playwright-e2e-2965a087e0d801ef3f18cf67c9158520f27478a6b7f7191e2f14f6dbf9b67699:latest lzocateli/playwright-e2e:v0.1.0
```

Salve o `.tar` no Windows:

```powershell
docker save -o C:\Users\lzoca\projetos\playwright-e2e\playwright-e2e.tar lzocateli/playwright-e2e:v0.1.0
```

No WSL, carregue no Podman:

```bash
ls -lh /mnt/c/Users/lzoca/projetos/playwright-e2e/playwright-e2e.tar
podman load -i /mnt/c/Users/lzoca/projetos/playwright-e2e/playwright-e2e.tar
podman tag localhost/v0.1.0:latest lzocateli/playwright-e2e:v0.1.0
```

Depois execute normalmente:

```bash
uv run e2e --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed normal -- tests/test_blog_navigation.py
```

## Tutorial: Publicar imagens no Docker Hub (Windows)

Este tutorial usa o **Docker Desktop** no Windows para criar cópias das imagens e publicá-las no seu Docker Hub.

### 1. Login no Docker Hub

```powershell
docker login
```

### 2. Copiar a imagem base da Microsoft

```powershell
docker pull mcr.microsoft.com/playwright/python:v1.49.0-noble
docker tag mcr.microsoft.com/playwright/python:v1.49.0-noble lzocateli/playwright:v1.49.0-noble
docker push lzocateli/playwright:v1.49.0-noble
```

### 3. Construir e enviar a imagem customizada (playwright-e2e)

Essa é a imagem que `uv run e2e` executa.

```powershell
cd C:\Users\lzoca\projetos\playwright-e2e

docker build -f Containerfile -t lzocateli/playwright-e2e:v0.1.0 .
docker push lzocateli/playwright-e2e:v0.1.0
```

### 4. Verificar no Docker Hub

```powershell
# Listar as imagens locais
docker images | Select-String "playwright"

# Testar a imagem do Docker Hub (pull limpo)
docker rmi lzocateli/playwright-e2e:v0.1.0 
docker run --rm lzocateli/playwright-e2e:v0.1.0 --co -q
```

### 5. Usar a imagem do Docker Hub no Proxmox

No servidor Proxmox, use a imagem do seu Docker Hub em vez de build local:

```bash
# Pull da sua imagem (uma vez)
podman pull docker.io/lzocateli/playwright-e2e:v0.1.0

# Rodar diretamente (sem build)
podman run --rm \
  -v ./reports:/app/reports:Z \
  -v ./tests:/app/tests:ro,Z \
  -v ./src/e2e:/app/src/e2e:ro,Z \
  -v ./src/vpn:/app/src/vpn:ro,Z \
  -v ./vpn/configs:/app/vpn/configs:ro,Z \
  docker.io/lzocateli/playwright-e2e:v0.1.0 \
  --base-url https://zocate.li
```

### Resumo das imagens

| Imagem | Origem | Descrição |
|---|---|---|
| `mcr.microsoft.com/playwright/python:v1.49.0-noble` | Microsoft | Base: Ubuntu 24.04 + Python + browsers |
| `lzocateli/playwright:v1.49.0-noble` | Docker Hub | Cópia da imagem base Microsoft |
| `lzocateli/playwright-e2e:v0.1.0` | Build do Containerfile | Imagem completa com VPN + uv (usa `lzocateli/playwright` como base) |

### Atualizando versões

```powershell
# Nova versão da base Microsoft (ex: v1.50.0)
docker pull mcr.microsoft.com/playwright/python:v1.50.0-noble
docker tag mcr.microsoft.com/playwright/python:v1.50.0-noble lzocateli/playwright:v1.50.0-noble
docker push lzocateli/playwright:v1.50.0-noble

# Nova versão do projeto (atualizar FROM no Containerfile também)
docker build -f Containerfile -t lzocateli/playwright-e2e:v0.2.0 .
docker push lzocateli/playwright-e2e:v0.2.0
```

## Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).

## Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).
