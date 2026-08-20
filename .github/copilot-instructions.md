# GitHub Copilot Instructions

## Ambiente local e aliases containerizados

- O console padrão do workspace no Windows é PowerShell 7 (`pwsh`), nunca Windows PowerShell 5.1 (`powershell.exe`).
- O profile padrão importa `D:\OneDrive - zocateli\ProfileZocateli\profile.shared.ps1`. Não use `-NoProfile` quando a operação depender dos aliases interativos.
- Antes de concluir que uma ferramenta não está instalada ou tentar instalá-la, execute `Get-Command <nome>` no PowerShell 7.
- Os aliases abaixo executam a ferramenta em `lzocateli/devops:ubuntu-22.04` pelo Docker, em vez de chamar um binário local:

| Alias | Ferramenta no container |
| --- | --- |
| `gh` | GitHub CLI |
| `copilot` | GitHub Copilot via `gh copilot` |
| `ghswitch` | troca da conta ativa do GitHub CLI |
| `terraform` | Terraform |
| `jq` | jq |
| `az` | Azure CLI |
| `ng` | Angular CLI |
| `node` | Node.js |
| `npm` | npm |
| `sqlcmd` | sqlcmd |

- Esses aliases são conveniências do terminal interativo. Scripts, tarefas automatizadas e CI não devem depender do profile pessoal; nesses casos, declare explicitamente o executável ou container utilizado.