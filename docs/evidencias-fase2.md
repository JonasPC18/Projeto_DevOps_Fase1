# Evidências da fase 2

A execução de **22 de novembro de 2026** concluiu os três jobs com sucesso. Os resultados abaixo se referem a essa execução específica, preservada como referência mesmo após novos commits.

- Repositório: https://github.com/JonasPC18/Projeto_DevOps_Fase1
- Execução: https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/45024861048
- Commit testado: `3b86771142d5fd6c3a89bc778f4e44c03a06cbfe`
- Ambiente: GitHub Actions, runner Ubuntu 24.04 e Docker Compose em um único host.
- Imagem publicada e implantada:

```text
ghcr.io/jonaspc18/projeto_devops_fase1@sha256:1563ab53b32dcaf09fc880e11d35c7c74f44247838cbc46324b0a4feac9f9474
```

## CI e infraestrutura

| Verificação | Resultado observado |
| --- | --- |
| Testes Python | 36 testes passaram em 0,297 s: os 24 originais, 7 de observabilidade e 5 da política de segurança. |
| Terraform | Formatação e validação aprovadas. 4 testes com provider simulado passaram. |
| Provisionamento | 4 recursos criados: imagem, rede, volume e contêiner. |
| API | Smoke test de saúde, criação, listagem, conclusão e exclusão aprovado. |
| Convergência | Novo plan sem mudanças, com código de saída 0. |
| Limpeza | 4 recursos Terraform removidos. |

## Segurança e publicação

O Trivy 0.76.2 não detectou segredos na verificação dos arquivos. A análise da imagem gerou o relatório completo e uma SBOM CycloneDX. A política não encontrou vulnerabilidades HIGH/CRITICAL **com correção disponível** que bloqueassem essa imagem.

| Severidade | Ocorrências por pacote |
| --- | ---: |
| CRITICAL | 0 |
| HIGH | 50 |
| MEDIUM | 74 |
| LOW | 79 |
| UNKNOWN | 7 |

Passar pela política não significa ausência de vulnerabilidades. Os 50 achados HIGH não tinham versão de correção indicada no relatório. Os números representam ocorrências por pacote, não necessariamente CVEs únicas. A análise cobriu a imagem da aplicação; as imagens de Prometheus e Grafana ainda precisam entrar nessa verificação.

## Demonstração real

Os tempos abaixo são acumulados desde o início de `scripts/release_demo.py`. Incluem download/preparação e esperas, e não representam latência da API.

| Tempo acumulado | Etapa | Evidência |
| --- | --- | --- |
| 25,58 s | Deploy | Imagem pelo digest, saúde e smoke test aprovados; /version igual ao commit. |
| 37,83 s | Reinício | Tarefa preservada no SQLite após reiniciar a API. |
| 83,30 s | Rollback automático | Imagem defeituosa recusada; script retornou 1; imagem anterior e dados recuperados. |
| 83,33 s | Monitoramento | Prometheus com up = 1 e dashboard devops-tarefas consultado pela API autenticada do Grafana. |
| 115,49 s | Falha controlada | API parada e alerta ApiIndisponivel em firing. |
| 121,65 s | Recuperação | API disponível e alerta resolvido. |
| 121,78 s | Encerramento | Smoke test final aprovado e 21 eventos JSON de log validados. |

O job depois coletou estado, logs e uso de recursos, removeu os três contêineres, os três volumes e a rede, e encerrou a sessão no registry. A imagem permanece publicada. Nenhum servidor permanente foi provisionado.

Os eventos exatos estão também em [evidencias-fase2.json](evidencias-fase2.json).

## Relatórios da execução

Os artifacts têm retenção de 30 dias e podem exigir login no GitHub. Este resumo permanece no repositório.

- [CI: testes, Terraform e smoke test](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/45024861048/artifacts/14754658106)
- [Segurança: Trivy, SBOM e referência da imagem](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/45024861048/artifacts/14755705756)
- [Entrega: eventos, alertas, dashboard, logs e estado](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/45024861048/artifacts/14755238265)

## Problemas encontrados e corrigidos

1. A [primeira execução](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/45024130673) bloqueou `zlib1g` por `CVE-2026-85091`, HIGH com correção disponível. A construção passou a atualizar os pacotes do sistema base. A política de segurança não foi desativada.
2. Na [execução seguinte](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/45024557385), o Docker rejeitou opções `tmpfs` interpretadas como elementos separados da lista YAML. O Compose passou a manter a especificação entre aspas. A execução aprovada confirmou o deploy real.

As falhas provocadas na demonstração são diferentes desses erros de implementação: a imagem defeituosa e a parada da API fazem parte do roteiro, e só passam quando a recuperação funciona.

## Limites

O teste confirma a entrega no laboratório. Não comprova desempenho sob carga, alta disponibilidade, backup/restauração nem migrações de banco. O alerta de erros 5xx está configurado, mas seu disparo não foi testado. Não há Alertmanager, notificações, autenticação/TLS na API nem aprovação humana para produção.
