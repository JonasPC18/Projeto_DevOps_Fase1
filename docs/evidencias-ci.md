# Evidências do CI

O workflow terminou com sucesso em **5 de novembro de 2026**. Esta evidência registra uma execução específica, que pode ser consultada mesmo quando novos commits forem enviados.

- Repositório: https://github.com/JonasPC18/Projeto_DevOps_Fase1
- Execução aprovada: https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions/runs/42007711406
- Commit testado: `814f79659ba64ea63232d8ab81808fa141dc9bbd`
- Job: **Testes e infraestrutura**
- Ambiente: runner `ubuntu-24.04`, Python 3.12 e Terraform 1.14.6.
- Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

| Verificação | Resultado observado |
| --- | --- |
| Sintaxe e testes da aplicação | 24 testes aprovados: 10 de regras e persistência, 14 pela interface HTTP. |
| Formatação e validação da IaC | `terraform fmt`, `init` e `validate` concluídos. |
| Testes de Terraform | 4 execuções aprovadas com provider simulado. |
| Provisionamento real | `apply` criou imagem, rede, volume e contêiner no Docker do runner. |
| API em funcionamento | Smoke test de saúde, criação, listagem, conclusão e exclusão aprovado. |
| Convergência | Um segundo `plan -detailed-exitcode` retornou 0, sem mudanças. |
| Limpeza | `destroy` removeu os 4 recursos temporários. |
| Evidências | Relatórios e `app.zip` enviados ao artifact `evidencias-814f79659ba64ea63232d8ab81808fa141dc9bbd`. |

## Trechos dos logs

Os horários abaixo estão em UTC. Os logs completos ficam na execução vinculada acima.

```text
2026-11-05T10:05:10Z Ran 24 tests in 0.230s
2026-11-05T10:05:17Z Success! 4 passed, 0 failed.
2026-11-05T10:05:28Z Apply complete! Resources: 4 added, 0 changed, 0 destroyed.
2026-11-05T10:05:28Z Smoke test aprovado: saúde, criação, listagem, conclusão e exclusão.
2026-11-05T10:05:30Z No changes. Your infrastructure matches the configuration.
2026-11-05T10:05:35Z Destroy complete! Resources: 4 destroyed.
```

O artifact tem retenção de sete dias. Este registro e os arquivos do projeto continuam disponíveis no repositório para consulta e reprodução dos testes.

## Ajuste identificado pelo pipeline

A primeira execução encontrou uma diferença em `memory_swap`: o Docker calculou 256 MB para o total de RAM e swap, enquanto o atributo não estava definido no Terraform. O arquivo `infra/main.tf` passou a declarar esse limite. A nova execução confirmou a ausência de mudanças após o `apply`, sem remover ou ignorar a verificação de convergência.

Referências para a configuração: [limites de recursos do Docker](https://docs.docker.com/engine/containers/resource_constraints/) e [recurso docker_container do provider 4.6.0](https://registry.terraform.io/providers/kreuzwerker/docker/4.6.0/docs/resources/container).

O provisionamento foi um teste temporário no runner. A aplicação não foi publicada em produção, e a proteção da branch `main` continua como melhoria planejada.
