# Documentação de planejamento

## 1. Descrição, objetivos e requisitos

O projeto é uma API para organizar tarefas. O usuário cadastra uma atividade, consulta o que precisa fazer, marca a conclusão e remove uma tarefa quando ela deixa de ser necessária. A aplicação usa Python e guarda os dados em SQLite.

A escolha de um sistema pequeno ajuda a concentrar o esforço no objetivo da fase: integrar mudanças com frequência, testar automaticamente e criar o ambiente de forma repetível. O código da aplicação e a infraestrutura ficam no mesmo repositório para facilitar a revisão.

O objetivo principal é deixar uma base de desenvolvimento que qualquer pessoa consiga executar seguindo o README. Para isso, cada mudança deve passar por testes, o ambiente deve ser descrito em código e os resultados das verificações precisam ficar disponíveis.

| Requisito | Critério de aceite |
| --- | --- |
| Cadastrar tarefa | `POST /tasks` retorna 201 e uma tarefa pendente com identificador. |
| Validar entrada | Títulos vazios, longos ou de outro tipo retornam 400. |
| Listar e consultar | A API retorna JSON com as tarefas gravadas. |
| Concluir e reabrir | `PATCH /tasks/{id}` aceita apenas `done` booleano. |
| Excluir | A API retorna 204 e a tarefa deixa de ser encontrada. |
| Persistir dados | Abrir novamente o banco mantém as tarefas. |
| Verificar saúde | `GET /health` confirma que a aplicação consegue consultar o banco. |
| Automatizar qualidade | O CI executa os testes e falha quando encontra erro. |
| Recriar ambiente | O Terraform descreve e gerencia imagem, rede, volume e contêiner. |

Nesta fase, o uso é local e educacional. Interface visual, autenticação, TLS, alta disponibilidade e deploy em produção ficam fora do escopo inicial. Essa limitação está refletida na porta publicada apenas no endereço local.

## 2. Plano de integração contínua

As mudanças começam em branches curtas, como `feat/nova-tarefa`. O responsável abre um pull request para `main`, explica a alteração e confere o resultado do CI. Mesmo em um trabalho individual, esse fluxo deixa a revisão e o histórico mais claros.

O workflow roda em todo push, em pull requests para `main` e por acionamento manual. Ele valida a sintaxe, executa 24 testes Python, confere o Terraform, roda os testes de IaC, cria um ambiente Docker temporário, testa a API em funcionamento e remove o ambiente. Os relatórios ficam em um artifact por sete dias.

Se qualquer teste falhar, a mudança precisa de correção antes de seguir. A regra planejada para a branch principal exige pull request e o check “Testes e infraestrutura”. Essa proteção ainda não foi configurada e depende dos recursos disponíveis no plano do GitHub. Um workflow vermelho, sem uma regra de proteção, não impede tecnicamente o merge.

O workflow valida a base para uma futura entrega contínua. Não há deploy em produção nesta fase. Em uma evolução, a implantação pode usar aprovação do ambiente, uma imagem imutável e uma estratégia de rollback testada.

## 3. Infraestrutura necessária

O ambiente de desenvolvimento precisa de Python 3.12, Git, Docker Engine ou Docker Desktop e Terraform 1.14.6. Como referência inicial para o laboratório, consideramos um host com 2 CPUs, 2 GB de RAM e 2 GB livres. Esse dimensionamento é uma estimativa, não um resultado de teste de carga.

O Terraform usa o provider `kreuzwerker/docker` 4.6.0 e cria uma imagem a partir do Dockerfile, uma rede bridge, um volume para SQLite e um contêiner da aplicação. Ele atua sobre um Docker já instalado. Não provisiona uma máquina virtual nem recursos em AWS.

O contêiner usa 0,5 CPU e 128 MB de memória como limites. A API escuta na porta 8000 e o Docker publica essa porta somente em `127.0.0.1`. O processo usa um usuário sem privilégios, raiz somente leitura, `/tmp` temporário e volume gravável em `/data`. O healthcheck consulta a aplicação a cada dez segundos. Os logs têm rotação de dois arquivos de 5 MB.

O volume mantém os dados quando o contêiner reinicia ou é substituído. O comando `terraform destroy`, porém, também remove o volume. Como se trata de um laboratório, a limpeza é explícita e os dados devem ser copiados antes caso precisem ser preservados.

Os arquivos de estado e variáveis locais ficam fora do Git. O arquivo `.terraform.lock.hcl` acompanha o código para registrar a seleção e os checksums do provider. Se o projeto passar a ter vários responsáveis aplicando a infraestrutura, será necessário planejar um backend remoto com controle de acesso e bloqueio de estado.

## 4. Organização e etapas

| Etapa | Entrega |
| --- | --- |
| Planejamento | Escopo, requisitos e decisões de infraestrutura documentados. |
| Aplicação | API, persistência e tratamento dos erros previstos. |
| Qualidade | Testes unitários, HTTP e smoke test. |
| Automação | Workflow do GitHub Actions e arquivos Terraform. |
| Conferência | Execução do CI, revisão das evidências e atualização da apresentação. |

Uma alteração no código da API ou no Dockerfile altera o hash usado pelo recurso de imagem. Isso permite que o próximo `apply` construa novamente a imagem. Depois da aplicação, um segundo `plan` deve indicar ausência de mudanças, desde que nenhum arquivo ou recurso tenha sido alterado.

## 5. Repositório e evidências

Conta escolhida: **JonasPC18**.

Repositório: **https://github.com/JonasPC18/Projeto_DevOps_Fase1**.

O repositório é público e contém `.github/workflows/ci.yml`, a pasta `infra/`, a aplicação e os testes. A aba [Actions](https://github.com/JonasPC18/Projeto_DevOps_Fase1/actions) permite acompanhar as verificações automáticas.

Os resultados da preparação local estão em `docs/evidencias-locais.txt`. A evidência remota deve registrar o commit testado, o link da execução e os resultados das etapas. O provisionamento temporário acontece no runner do GitHub e é removido ao final do workflow.

## 6. Relação com as aulas

A Aula 1 orienta a colaboração e a responsabilidade compartilhada. A Aula 2 fornece a base da integração contínua e do uso do GitHub Actions. A Aula 3 conecta essa base à entrega contínua e às estratégias de recuperação. No PDF enviado, a Aula 4 trata de Docker e contêineres, o que apoia o empacotamento da aplicação. A documentação oficial do Terraform complementa a implementação de infraestrutura como código exigida no enunciado.
