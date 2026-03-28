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

- [Podman](https://podman.io/) (rootless)
- **Opcional**: Conta [Mullvad VPN](https://mullvad.net/) (para testes com VPN)

> **Nota**: Nenhuma instalação local de Python, browsers ou dependências é necessária.
> Tudo roda dentro do container.

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

# Browser específico
./run-e2e.sh --base-url https://zocate.li --browser chromium

# Reconstruir imagem
./run-e2e.sh --rebuild --base-url https://zocate.li
```

## Opções CLI (pytest)

| Opção | Valores | Default | Descrição |
|---|---|---|---|
| `--base-url` | URL | `http://localhost:1313` | URL base do site a testar |
| `--human-speed` | `slow`, `normal`, `fast` | `normal` | Intensidade dos delays humanos |
| `--enable-vpn` | flag | desligado | Ativa conexão VPN WireGuard |
| `--vpn-rotate` | `per-test`, `per-session`, `off` | `off` | Quando rotacionar VPN |
| `--browser` | `chromium`, `firefox`, `webkit` | todos | Browser específico |

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

## Troubleshooting

| Problema | Solução |
|---|---|
| `wg-quick: command not found` | Reconstruir imagem: `./run-e2e.sh --rebuild` |
| VPN sem conectar no Podman | Verificar `--cap-add=NET_ADMIN` e `--sysctl` |
| Browser timeout | Aumentar timeout: `--timeout 60000` |
| Imagem desatualizada | Usar `./run-e2e.sh --rebuild` |
| Vídeos não gravados | Confirmar diretório `reports/videos/` montado |
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
BUILDAH_ISOLATION=chroot podman build --cgroup-manager=cgroupfs -t playwright-e2e -f Containerfile .
```

Após o build, o `run-e2e.sh` detecta que a imagem já existe e executa normalmente.

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
./run-e2e.sh --base-url https://zocate.li --enable-vpn --vpn-rotate per-test --human-speed normal -- tests/test_blog_navigation.py
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
