# Fase 1: DevOps na Prática

Este projeto usa uma API de tarefas para colocar em prática o planejamento, a integração contínua e a infraestrutura como código. A aplicação é pequena de propósito: o foco desta fase é deixar o processo de desenvolvimento fácil de repetir e verificar.

**Repositório:** https://github.com/JonasPC18/Projeto_DevOps_Fase1

**Status:** projeto publicado e CI aprovado em 5 de novembro de 2026. A [execução verificada](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/42007711406) passou nos 24 testes Python, nos 4 testes de Terraform e no teste da API em Docker. Também confirmou um plano sem mudanças e removeu o ambiente temporário. Veja o registro em [docs/evidencias-ci.md](docs/evidencias-ci.md) e as próximas execuções na [aba Actions](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions).

## O que está incluído

- API em Python 3.12, usando apenas a biblioteca padrão.
- Banco SQLite para guardar as tarefas.
- 24 testes Python, incluindo integração HTTP.
- Dockerfile com usuário sem privilégios e healthcheck.
- Terraform para criar imagem, rede, volume e contêiner.
- Testes de Terraform com provider simulado.
- Workflow do GitHub Actions com provisionamento temporário e teste da API.
- Planejamento completo em `docs/planejamento.md`.

## Rodar sem Docker

Pré-requisito: Python 3.12. Não há pacotes externos para instalar.

```bash
python app.py
```

A API fica em http://127.0.0.1:8000 e o banco em `data/tasks.db`. No Windows, use `py -3.12` se o comando `python` não estiver disponível.

Em outro terminal, execute:

```bash
python scripts/smoke_test.py http://127.0.0.1:8000
```

## Usar a API

| Método e rota | Função | Corpo JSON |
| --- | --- | --- |
| `GET /health` | Confere a aplicação e o banco | Sem corpo |
| `GET /tasks` | Lista tarefas | Sem corpo |
| `POST /tasks` | Cadastra uma tarefa | `{"title":"Estudar CI"}` |
| `GET /tasks/1` | Consulta uma tarefa | Sem corpo |
| `PATCH /tasks/1` | Conclui ou reabre | `{"done":true}` |
| `DELETE /tasks/1` | Exclui uma tarefa | Sem corpo |

Exemplo em Bash:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Estudar CI"}'
```

O título precisa ter de 1 a 120 caracteres após remover espaços nas pontas. `done` aceita apenas `true` ou `false`. Corpos JSON podem ter até 4096 bytes. Os erros retornam JSON com status 400, 404, 405 ou 503, conforme o caso.

## Rodar os testes

```bash
python -m compileall -q app.py tests scripts
python -m unittest discover -s tests -v
```

Os testes criam bancos temporários e abrem a API em uma porta local disponível. Eles não usam os dados da sua aplicação.

## Criar o ambiente com Terraform

Pré-requisitos: Docker Engine iniciado, Terraform 1.14.6 e internet para baixar a imagem e o provider. O Docker precisa estar disponível ao seu usuário, sem `sudo`.

```bash
docker version
terraform version
terraform -chdir=infra init
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra test
terraform -chdir=infra plan
terraform -chdir=infra apply
python scripts/smoke_test.py http://127.0.0.1:8000
```

O `apply` pede confirmação. Os testes de Terraform usam um provider simulado: eles conferem a configuração, mas não criam contêineres. O `plan` e o `apply` normais usam o Docker real.

O Terraform cria quatro recursos: uma imagem, uma rede, um volume e um contêiner. A imagem é reconstruída quando `app.py` ou o `Dockerfile` muda. O contêiner tem limite de 0,5 CPU e 128 MB de RAM, com 256 MB para o total de RAM e swap. Ele usa raiz somente leitura, usuário sem privilégios e acesso pela porta local 8000. O banco fica no volume.

Para personalizar, copie `infra/terraform.tfvars.example` para `infra/terraform.tfvars`. A porta deve ser um número inteiro entre 1024 e 65535. Use um nome de projeto diferente para manter ambientes separados.

O socket padrão atende ao Docker Engine em Linux. No Docker Desktop, consulte o endpoint com:

```bash
docker context inspect --format '{{.Endpoints.docker.Host}}'
```

Copie o endereço retornado para `docker_host` em `infra/terraform.tfvars`. No Windows, uma opção simples é executar o projeto dentro do WSL com integração do Docker Desktop habilitada. Não exponha o daemon Docker em uma porta TCP sem autenticação.

Para consultar logs:

```bash
docker logs devops-fase1-tarefas
```

Para conferir a convergência, execute `terraform -chdir=infra plan -detailed-exitcode` depois do `apply`. O código 0 indica ausência de mudanças, 2 indica mudanças propostas e 1 indica erro.

Para limpar o laboratório:

```bash
terraform -chdir=infra destroy
```

**O destroy também apaga o volume e as tarefas.** Reiniciar ou substituir apenas o contêiner preserva o volume. Faça cópia dos dados antes de destruir o ambiente se quiser guardá-los.

## O pipeline de CI

O arquivo `.github/workflows/ci.yml` roda em pushes, pull requests para `main` e disparos manuais. Ele usa `ubuntu-24.04`, Python 3.12 e Terraform 1.14.6.

1. Obtém o código e prepara Python.
2. Verifica a sintaxe, executa os testes e gera `app.zip`.
3. Confere a formatação, inicializa e valida o Terraform.
4. Executa os testes da infraestrutura com provider simulado.
5. Planeja e cria um ambiente Docker temporário no runner.
6. Executa o smoke test pela API e confere se um novo plano não propõe mudanças.
7. Coleta os logs, remove o ambiente e guarda os relatórios por sete dias.

Uma falha encerra as etapas normais. A limpeza e a coleta de evidências usam `always()`. O Bash preserva os códigos de erro mesmo nos comandos que usam `tee`. Não há credenciais de nuvem, deploy em produção ou publicação de imagem em registry.

O `GITHUB_TOKEN` tem apenas `contents: read`. As ações usam versões principais estáveis. Para endurecer o fluxo em produção, fixe cada ação por SHA revisado e a imagem Python por digest, com atualizações controladas.

## Trabalhar com o repositório

O repositório é público e está na conta JonasPC18. Para obter o projeto:

```bash
git clone https://github.com/JonasPC18/Projeto_DevOps_Fase1.git
cd Projeto_DevOps_Fase1
```

Crie uma branch curta para cada mudança, envie os commits e abra um pull request para `main`. Confira o check **Testes e infraestrutura** antes de integrar o código.

A aba [Actions](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions) mostra cada execução. O artifact `evidencias-<SHA>` reúne relatórios e o pacote da aplicação por sete dias. Os testes e os comandos completos também estão neste repositório, permitindo reproduzir a verificação depois que o artifact expirar.

A proteção de `main` é uma melhoria planejada. Se for ativada, deve exigir pull request e o check **Testes e infraestrutura**. O YAML sozinho não bloqueia o merge. Essa regra não é apresentada como já configurada.

## Limites desta fase

Este é um laboratório local, sem autenticação de usuários ou TLS. O servidor HTTP da biblioteca padrão atende ao objetivo didático, mas não é uma configuração de produção. A solução usa uma única instância e SQLite, sem alta disponibilidade. Para avançar, o projeto pode adotar um servidor próprio para produção, autenticação, backups, observabilidade e uma etapa de entrega contínua com aprovação.

## Referências

- Mapas das Aulas 1, 2, 3 e 4 enviados na atividade.
- [GitHub Actions: construção e testes com Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).
- [Terraform com Docker](https://developer.hashicorp.com/terraform/tutorials/docker-get-started/docker-build).
- [Provider Docker 4.6.0](https://registry.terraform.io/providers/kreuzwerker/docker/4.6.0/docs).
- [Testes com provider simulado](https://developer.hashicorp.com/terraform/language/tests/mocking).
- [GitHub CLI: criar repositório](https://cli.github.com/manual/gh_repo_create).
