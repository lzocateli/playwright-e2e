# playwright-e2e

Ferramenta genérica de testes E2E com [Playwright](https://playwright.dev/) + [pytest](https://pytest.org/), rodando em container [Podman](https://podman.io/) rootless.

## Funcionalidades

- **Multi-browser**: Chromium, Firefox e WebKit
- **Simulação humana**: delays configuráveis entre ações (`slow_page`, `human_delay`)
- **VPN integrada**: Mullvad/WireGuard para simular conexões de locais diferentes
- **Rotação de VPN**: por teste, por sessão, ou desligado
- **Relatórios**: HTML com vídeos gravados de cada teste
- **Container Podman**: rootless, com bind mounts para testes e evidências

## Estrutura

```text
playwright-e2e/
├── pyproject.toml           # Dependências (uv)
├── conftest.py              # Fixtures: slow_page, human_delay, browser context
├── Containerfile            # Imagem com Playwright + WireGuard
├── run-e2e.sh               # Script wrapper Podman
├── rotate-posts.py          # Rotação automática de artigos via sitemap
├── vpn/
│   ├── vpn_manager.py       # Classe VPNManager (connect/disconnect/rotate)
│   ├── conftest_vpn.py      # Plugin pytest para VPN
│   └── configs/             # Arquivos .conf WireGuard (gitignored)
├── tests/
│   ├── test_blog_navigation.py   # Navegação no blog com simulação de leitura
│   ├── test_seo_live.py          # Verificações SEO em produção
│   └── test_sample_generic.py    # Template genérico para novos roteiros
└── reports/                 # Relatórios HTML + vídeos (gitignored)
```

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) ou [Podman](https://podman.io/) (rootless)
- **Windows**: [WSL2](https://learn.microsoft.com/pt-br/windows/wsl/install) com Docker Desktop ou Podman instalado dentro da distro
- **Opcional**: Conta [Mullvad VPN](https://mullvad.net/) (para testes com VPN)
- **Opcional**: [uv](https://docs.astral.sh/uv/) (para usar `--rotate-posts`)

> **Nota**: Nenhuma instalação local de Python, browsers ou dependências é necessária.
> O código-fonte (testes, fixtures, VPN manager) é montado via bind volume no runtime — não é copiado para dentro da imagem.
> Qualquer alteração local em testes ou fixtures é refletida imediatamente, sem necessidade de `--rebuild`.

### Execução no Windows (WSL2)

O script `run-e2e.sh` requer bash. No Windows, execute de dentro do WSL2:

```bash
# Abra o terminal WSL2 e navegue até o projeto
cd /mnt/c/Users/<seu-usuario>/projetos/playwright-e2e

# Execução normal
./run-e2e.sh --base-url https://zocate.li

# Execução completa (VPN + rotação + relatório + vídeo)
./run-e2e.sh --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed normal --vpn-strict --open-report --open-first-video --rotate-posts -- tests/test_blog_navigation.py

# Ou via PowerShell (invocando WSL):
# wsl bash ./run-e2e.sh --base-url https://zocate.li
```

> **PowerShell/CMD nativos** não executam `.sh` diretamente. Use sempre WSL2 como shell.
> Tudo roda dentro do container.
> **Imagem executada pelo script**: `lzocateli/playwright-e2e:v0.1.0`.
> Na primeira execução, o `run-e2e.sh` tenta baixar essa imagem do Docker Hub; se ela não existir no registry, faz o build local a partir do `Containerfile`.

## Instalando uv (opcional)

`uv` é necessário apenas se você pretende usar o flag `--rotate-posts` no `run-e2e.sh` para rotacionar automaticamente artigos do blog antes dos testes.

### Linux

**Opção 1: Instalador oficial (recomendado)**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Após instalar, adicione `uv` ao `$PATH`:

```bash
# Adicione esta linha ao ~/.bashrc, ~/.zshrc ou ~/.profile
export PATH="$HOME/.local/bin:$PATH"

# Aplique imediatamente
source ~/.bashrc  # ou ~/.zshrc
```

Verifique a instalação:

```bash
uv --version
```

**Opção 2: Via package manager (se disponível na distro)**

```bash
# Ubuntu/Debian
sudo apt-get install uv

# Fedora/RHEL
sudo dnf install uv

# Arch
sudo pacman -S uv

# Homebrew (macOS e Linux)
brew install uv
```

### macOS

```bash
# Via Homebrew (recomendado)
brew install uv

# Ou via instalador oficial
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

### Windows (WSL2)

Dentro do WSL2, execute o mesmo comando do Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

Ou via package manager:

```bash
# Apt (Ubuntu/Debian no WSL)
sudo apt-get install uv

# Scoop (PowerShell nativo do Windows)
scoop install uv
```

### Verificar instalação

```bash
uv --version
uv python --version
```

## Execução

```bash
# Dar permissão de execução (uma vez)
chmod +x run-e2e.sh

# Básico — sem VPN, velocidade normal
./run-e2e.sh --base-url https://zocate.li

# Com simulação humana lenta
./run-e2e.sh --base-url https://zocate.li --human-speed slow

# Com VPN (requer configs em vpn/configs/)
./run-e2e.sh --base-url https://zocate.li --enable-vpn

# VPN com rotação por teste + velocidade lenta
./run-e2e.sh --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed slow

# VPN estrita (falha se saída não for Mullvad)
./run-e2e.sh --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --vpn-strict

# Browser específico
./run-e2e.sh --base-url https://zocate.li --browser chromium

# Reconstruir imagem
./run-e2e.sh --rebuild --base-url https://zocate.li

# Abrir relatório automaticamente ao finalizar
./run-e2e.sh --open-report --base-url https://zocate.li

# Abrir automaticamente o primeiro vídeo (.webm)
./run-e2e.sh --open-first-video --base-url https://zocate.li

# Rotacionar posts do blog antes dos testes (requer uv)
./run-e2e.sh --base-url https://zocate.li --rotate-posts

# Rotacionar posts com range customizado
./run-e2e.sh --base-url https://zocate.li --rotate-posts --min-posts 2 --max-posts 5

# Preview da rotação (sem alterar arquivo de teste)
./run-e2e.sh --base-url https://zocate.li --rotate-posts --dry-run-rotate

# Rotacionar + limpar histórico
./run-e2e.sh --base-url https://zocate.li --rotate-posts --reset-hist

# Execução com todos os parametros
./run-e2e.sh --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed normal --vpn-strict --open-report --open-first-video --rotate-posts -- tests/test_blog_navigation.py
```

## Rotação automática de artigos

O script `rotate-posts.py` lê o `sitemap.xml` do blog, seleciona aleatoriamente artigos novos para `BLOG_POSTS` e move os já testados para `BLOG_POSTS_HIST` em `tests/test_blog_navigation.py`.

```bash
# Ver o que mudaria (sem alterar arquivo)
uv run rotate-posts.py --dry-run

# Rotação padrão (3-6 artigos novos)
uv run rotate-posts.py

# Range customizado
uv run rotate-posts.py --min-posts 3 --max-posts 6

# Site diferente
uv run rotate-posts.py --base-url https://zocate.li

# Todos os parametros
uv run rotate-posts.py --base-url https://zocate.li --min-posts 3 --max-posts 6 --test-file tests/test_blog_navigation.py

# Limpar histórico e começar do zero
uv run rotate-posts.py --reset-hist
```

### Opções CLI (rotate-posts.py)

| Opção | Valores | Default | Descrição |
|---|---|---|---|
| `--base-url` | URL | `https://zocate.li` | URL base do site (para buscar sitemap.xml) |
| `--min-posts` | inteiro | `3` | Mínimo de artigos a selecionar |
| `--max-posts` | inteiro | `6` | Máximo de artigos a selecionar |
| `--dry-run` | flag | desligado | Exibe o que mudaria sem alterar o arquivo |
| `--reset-hist` | flag | desligado | Limpa `BLOG_POSTS_HIST` antes de rotacionar |
| `--test-file` | caminho | auto-detectado | Caminho para `test_blog_navigation.py` |

> **Fluxo recomendado**: Execute `uv run rotate-posts.py` antes de `run-e2e.sh` para testar artigos diferentes a cada execução.
> Quando todos os artigos do sitemap já estiverem no histórico, o script recicla os mais antigos automaticamente.

## Opções CLI (pytest)

| Opção | Valores | Default | Descrição |
|---|---|---|---|
| `--base-url` | URL | `http://localhost:1313` | URL base do site a testar |
| `--human-speed` | `slow`, `normal`, `fast` | `normal` | Intensidade dos delays humanos |
| `--enable-vpn` | flag | desligado | Ativa conexão VPN WireGuard |
| `--vpn-rotate` | `per-test`, `per-session`, `off` | `off` | Quando rotacionar VPN |
| `--vpn-strict` | flag | desligado | Falha a execução se `mullvad_exit_ip` não for verdadeiro |
| `--browser` | `chromium`, `firefox`, `webkit` | aleatório | Browser específico (se omitido, escolhido aleatoriamente) |
| `--open-report` | flag | desligado | Abre `reports/report.html` automaticamente ao finalizar |
| `--open-first-video` | flag | desligado | Abre o primeiro `.webm` de `reports/videos` automaticamente |
| `--rotate-posts` | flag | desligado | Rotaciona artigos do blog antes dos testes (requer `uv`) |
| `--min-posts` | inteiro | `3` | Posts mínimos a selecionar (usado com `--rotate-posts`) |
| `--max-posts` | inteiro | `6` | Posts máximos a selecionar (usado com `--rotate-posts`) |
| `--reset-hist` | flag | desligado | Limpa histórico de posts antes de rotacionar (usado com `--rotate-posts`) |
| `--dry-run-rotate` | flag | desligado | Preview da rotação sem alterar arquivo (usado com `--rotate-posts`) |

### Multiplicadores de velocidade

| Speed | Multiplicador | Delay padrão (2-8s) | Resultado |
|---|---|---|---|
| `slow` | 2.0x | 4-16s | Simula leitura atenta |
| `normal` | 1.0x | 2-8s | Navegação natural |
| `fast` | 0.3x | 0.6-2.4s | Teste rápido |

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
# Container com VPN (necessita NET_ADMIN)
./run-e2e.sh --base-url https://zocate.li --enable-vpn --vpn-rotate per-test

# Verificar nos logs: "VPN sessão iniciada — Local: br-sao | IP: x.x.x.x"
```

## Criando novos roteiros de teste

1. Copie `tests/test_sample_generic.py` como base
2. Renomeie para `tests/test_<seu_cenario>.py`
3. Use as fixtures `slow_page` e `human_delay`
4. Rode via container:

   ```bash
   ./run-e2e.sh --base-url https://seusite.com -- tests/test_<seu_cenario>.py
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
| `wg-quick: command not found` | Reconstruir imagem: `./run-e2e.sh --rebuild` |
| VPN sem conectar no Podman | Verificar `--cap-add=NET_ADMIN` e `--sysctl` |
| Browser timeout | Aumentar timeout: `--timeout 60000` |
| Imagem desatualizada | Usar `./run-e2e.sh --rebuild` |
| Vídeos não gravados | Confirmar diretório `reports/videos/` montado |
| Alterações em testes não refletidas | Verificar se `--rebuild` não é necessário (bind volume já monta código do host); confirmar que o container usa a versão mais recente da imagem |
| `sd-bus call: Permission denied` no build (WSL2) | Ver seção abaixo |

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

Após o build, o `run-e2e.sh` detecta que a imagem já existe e executa normalmente.

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

No WSL, valide o arquivo e carregue no Podman:

```bash
ls -lh /mnt/c/Users/lzoca/projetos/playwright-e2e/playwright-e2e.tar
podman load -i /mnt/c/Users/lzoca/projetos/playwright-e2e/playwright-e2e.tar
podman tag localhost/v0.1.0:latest lzocateli/playwright-e2e:v0.1.0
```

Depois execute normalmente:

```bash
./run-e2e.sh --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed normal -- tests/test_blog_navigation.py
```

## Tutorial: Publicar imagens no Docker Hub (Windows)

Este tutorial usa o **Docker Desktop** no Windows para criar cópias das imagens e publicá-las no seu Docker Hub.

### 1. Login no Docker Hub

```powershell
docker login
```

### 2. Copiar a imagem base da Microsoft

Baixar, tagear como `lzocateli/playwright` e enviar:

```powershell
# Baixar a imagem da Microsoft
docker pull mcr.microsoft.com/playwright/python:v1.49.0-noble

# Tagear com o nome lzocateli/playwright
docker tag mcr.microsoft.com/playwright/python:v1.49.0-noble lzocateli/playwright:v1.49.0-noble

# Enviar para o Docker Hub
docker push lzocateli/playwright:v1.49.0-noble
```

### 3. Construir e enviar a imagem customizada (playwright-e2e)

Essa e a imagem que o `run-e2e.sh` executa.

```powershell
# Navegar até o diretório do projeto
cd C:\Users\lzoca\projetos\playwright-e2e

# Construir a imagem a partir do Containerfile
docker build -f Containerfile -t lzocateli/playwright-e2e:v0.1.0 .

# Enviar para o Docker Hub
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
  docker.io/lzocateli/playwright-e2e:v0.1.0 \
  --base-url https://zocate.li
```

### Resumo das imagens

| Imagem | Origem | Descrição |
|---|---|---|
| `mcr.microsoft.com/playwright/python:v1.49.0-noble` | Microsoft | Base original: Ubuntu 24.04 + Python + browsers |
| `lzocateli/playwright:v1.49.0-noble` | Docker Hub | Cópia da imagem base Microsoft |
| `lzocateli/playwright-e2e:v0.1.0` | Build do Containerfile | Imagem completa com testes + VPN + uv (usa `lzocateli/playwright` como base) |

- Copiar os arquivos para wsl2

```bash
mkdir -p /home/lzocateli/projs/playwright-e2e/vpn/configs
cp -r /mnt/c/Users/lzoca/projetos/playwright-e2e/vpn/configs/* /home/lzocateli/projs/playwright-e2e/vpn/configs/

# Exemplo de execução real
./run-e2e.sh --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed normal --vpn-strict --open-report --open-first-video --rotate-posts -- tests/test_blog_navigation.py
```

### Atualizando versões

Quando atualizar o Playwright ou o projeto:

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
