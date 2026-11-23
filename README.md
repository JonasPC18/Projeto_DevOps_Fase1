# DevOps na Prática: fases 1 e 2

Uma API de tarefas serve de base para demonstrar integração e entrega contínua. O projeto usa Python, SQLite, Docker, Terraform e GitHub Actions. Na fase 2, Docker Compose reúne a API, o Prometheus e o Grafana.

**Repositório:** https://github.com/JonasPC18/Projeto_DevOps_Fase1

A fase 1 e seus resultados estão preservados em [docs/planejamento.md](docs/planejamento.md), [docs/evidencias-ci.md](docs/evidencias-ci.md) e [docs/fase1-readme.md](docs/fase1-readme.md).

## O que a fase 2 acrescenta

- Pipeline com testes, validação de IaC, análise de segurança, publicação no GHCR e deploy por digest.
- 36 testes Python, incluindo métricas, logs e a política de bloqueio de vulnerabilidades.
- Scripts de implantação e rollback com verificação de saúde e smoke test.
- Métricas em `/metrics`, identificação do commit em `/version` e logs estruturados em JSON.
- Dashboard provisionado no Grafana e regras de alerta no Prometheus.
- Demonstração automática de persistência, rollback e disparo/resolução de um alerta.

A [aba Actions](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions) mostra o resultado de cada execução. O [relatório da fase 2](docs/fase2.md) explica as decisões, os limites e os passos da demonstração.

A fase 2 foi validada em [uma execução completa aprovada](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/45024861048), em 22/11/2026. As [evidências](docs/evidencias-fase2.md) incluem a imagem publicada, os testes de recuperação e os resultados de segurança.

## Executar os testes

Com Python 3.12 ou mais recente:

```bash
python -m compileall -q app.py tests scripts
python -m unittest discover -s tests -v
```

A aplicação não usa dependências Python externas. Para rodar sem Docker, execute `python app.py`. A API fica em http://127.0.0.1:8000.

## Entrega contínua

O arquivo [.github/workflows/ci.yml](.github/workflows/ci.yml) tem três jobs:

1. **Testes e infraestrutura:** valida Python, scripts, Compose e Terraform. Cria e remove um ambiente de teste com IaC.
2. **Segurança e publicação:** após o primeiro job, constrói a imagem do commit, procura segredos e vulnerabilidades, gera a SBOM e publica a mesma imagem no GHCR.
3. **Entrega e demonstração monitorada:** baixa a imagem aprovada pelo digest e usa Compose para executar a demonstração completa.

Pushes e pull requests passam pelo CI. A publicação e a entrega ocorrem somente em `main`, após os testes, e também podem ser acionadas manualmente na aba Actions. Pull requests não publicam imagens.

O ambiente `demonstracao` é temporário e termina com a limpeza do runner. A imagem permanece no GHCR. Isso demonstra a entrega de um pacote versionado e a implantação automatizada sem contratar um servidor. Uma instalação permanente depende de um host Docker próprio.

Os artifacts `ci-<SHA>`, `seguranca-<SHA>` e `entrega-<SHA>` guardam os relatórios por 30 dias. O workflow usa SHA fixo nas ações e limita `packages: write` ao job de publicação. O token do GitHub é temporário e não fica nos arquivos.

## Executar o mesmo deploy em um host Docker

Pré-requisitos: Linux ou WSL, Docker Engine com Compose v2, Python 3, Bash e `flock`. Para o conjunto API, Prometheus e Grafana, considere inicialmente 2 CPUs, 2 GB de RAM e 3 GB livres. É uma estimativa para o laboratório.

```bash
git clone https://github.com/JonasPC18/Projeto_DevOps_Fase1.git
cd Projeto_DevOps_Fase1
# Copie a referencia ghcr.io/...@sha256:... da execucao aprovada.
bash scripts/deploy.sh IMAGEM_POR_DIGEST
```

Se o pacote GHCR estiver privado, faça `docker login ghcr.io` com uma credencial que tenha acesso de leitura ao pacote. Não coloque tokens no código ou em argumentos públicos. No workflow, essa autenticação já usa o `GITHUB_TOKEN`.

Para experimentar uma imagem construída localmente:

```bash
docker build --build-arg APP_VERSION=local -t devops-tarefas:local .
DEPLOY_SKIP_PULL=1 bash scripts/deploy.sh devops-tarefas:local
```

Endereços locais:

| Serviço | Endereço |
| --- | --- |
| API | http://127.0.0.1:8000/health |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 |

O usuário do Grafana é `admin`. A senha aleatória fica em `.secrets/grafana_admin_password`, fora do Git e dos relatórios. Consulte esse arquivo apenas no seu computador. A senha inicial persiste no volume do Grafana. Para mudar portas, copie `.env.example` para `.env` e edite os valores.

Depois de duas entregas aprovadas com imagens diferentes, o rollback manual usa a versão anterior:

```bash
bash scripts/rollback.sh
```

Se uma implantação falhar na saúde ou no smoke test, o script tenta restaurar a imagem anterior, preserva o volume e retorna erro. No primeiro deploy ainda não existe uma versão anterior.

## Logs, métricas e limpeza

```bash
export APP_IMAGE="$(cat .deploy/devops-fase2/current-image)"
docker compose logs --follow api
docker compose ps
# Para encerrar os servicos mantendo os volumes:
docker compose down
```

O dashboard **DevOps - API de tarefas** mostra disponibilidade, requisições, erros 5xx e latência p95. O alerta `ApiIndisponivel` exige 15 segundos de falha após a observação pelo Prometheus. O laboratório não envia notificações por e-mail ou chat.

**`docker compose down --volumes` remove os dados do laboratório.** O workflow usa essa opção apenas no runner temporário. Reiniciar ou atualizar o contêiner mantém o volume SQLite.

## Segurança e limites

O Trivy bloqueia segredos detectados e vulnerabilidades HIGH/CRITICAL que tenham correção disponível. Achados sem correção e de menor severidade continuam registrados no relatório completo. Passar nessa política não significa ausência de vulnerabilidades.

Os serviços publicam portas apenas em `127.0.0.1`. A API roda sem root, com raiz somente leitura, capabilities removidas e limites de recursos. Os logs não registram corpo da requisição nem query string.

Este ambiente é didático, com uma instância e SQLite. Docker Compose coordena os serviços em um único host. A proteção de `main`, aprovação humana para produção, TLS, autenticação da API, backups externos e alta disponibilidade são evoluções futuras. O histórico da fase 1 explica como executar o laboratório Terraform separadamente, evitando usar a mesma porta ao mesmo tempo.
