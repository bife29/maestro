# Constitution — Maestro

**Versão:** 1.0 · 24/11/2026 · **Dono:** Michel Bueno Silva · **Executor:** Michel + squad agêntico (GitHub Copilot)
**Repositório:** `github.com/bife29/maestro` (pessoal, público, MIT)
**Natureza:** projeto de portfólio. **Nenhum dado, nome de sistema, credencial, URL interna ou regra de negócio de empregador atual ou anterior entra aqui.** Todo dado é sintético e gerado por script do próprio projeto.

## 1. Por que este projeto existe

Nos últimos dois anos construí, no dia a dia de coordenação de times de engenharia, um conjunto de práticas
que hoje chamo de **gestão de engenharia AI-native**: servidores MCP para consultar a esteira em linguagem
natural, base de conhecimento RAG que preserva decisões e incidentes, agentes que revisam PRs contra um padrão
arquitetural e um baseline de segurança, métricas DORA geradas automaticamente, e um fluxo SDD
(constitution → SPEC → PLAN → TASKS) que disciplina o trabalho dos agentes.

O **Maestro** reúne essas práticas em um toolkit **genérico, reproduzível e auditável**, para que um
recrutador, um tech lead ou um gestor consiga em 10 minutos: (a) entender a arquitetura, (b) rodar tudo
localmente sem credencial nenhuma, (c) ver gráficos e pareceres reais gerados sobre dados sintéticos, e
(d) ler o código e perceber o padrão de qualidade que eu exijo dos meus times.

## 2. Princípios inegociáveis

| # | Princípio | Consequência prática |
|---|---|---|
| P1 | **Zero dado de empregador** | Dados, nomes de repositórios, pessoas, sistemas e regras são sintéticos (`maestro seed`). Revisão de cada commit contra esta regra antes do push. Nome de empresa só aparece no currículo, nunca no repo. |
| P2 | **Roda sem credencial** | `pip install -e . && maestro demo` tem de funcionar offline: provider `local` para DevOps (dados sintéticos) e provider `dry` para LLM (determinístico). Integrações reais (GitHub, Azure DevOps, OpenAI-compatível, Bedrock) são **opcionais**, via variáveis de ambiente, nunca obrigatórias. |
| P3 | **Clean Architecture de verdade** | `domain` não importa nada de fora; `application` orquestra via portas; `infrastructure` implementa adaptadores; `presentation` (CLI e MCP) só traduz. Teste de arquitetura em CI (import-linter) garante a direção das dependências. |
| P4 | **Agente nunca decide sozinho** | Toda saída de LLM é validada contra schema (pydantic) antes de virar parecer. Publicar em PR exige `--confirm` explícito; o padrão é dry-run. Parecer publicado leva aviso de uso de IA no topo. |
| P5 | **Allow-list, não deny-list** | O servidor MCP expõe apenas tools declaradas em `tools.yaml`; cada tool declara se é read-only. O orquestrador de agentes só chama tools da lista do agente. |
| P6 | **Conteúdo de terceiro não entra no prompt de sistema** | Diff, descrição de PR e documentos da KB entram como *dado* delimitado no prompt de usuário, com instrução explícita de não-execução. Suíte mínima de prompt-injection roda em CI. |
| P7 | **Auditoria append-only** | Toda execução de agente e toda publicação geram linha em `audit/*.jsonl` (JSON por linha, sem PII, com `correlation_id`, modelo, custo estimado, verdicto, hash do input). Nenhum código do projeto reescreve ou apaga essas linhas. |
| P8 | **Gate de porte** | PR acima do limite (arquivos/linhas, configurável) recebe verdicto `REVISAO_MANUAL` sem tentar ler o diff inteiro — lição aprendida; o agente não trava e o tempo fica previsível. |
| P9 | **Qualidade visível** | ruff + mypy (strict no `domain`) + pytest ≥ 85 % de cobertura + CI verde em todo push. Badges no README refletem a verdade do `main`. |
| P10 | **Documentação é produto** | Wiki (MkDocs Material + GitHub Pages) com diagramas Mermaid, gráficos gerados pelo próprio código e ADRs. Se a documentação não explica, a feature não está pronta. |
| P11 | **Pausável e retomável** | Trabalho dividido em fases independentes com critério de "pronto" próprio; cada fase termina com push e CI verde. Parar no meio de uma fase nunca quebra o `main`. |
| P12 | **Fora dos relatórios de trabalho** | Este projeto não entra em registro de sessão, EOD, diário ou qualquer relatório profissional. Vive em `C:\Projetos\Michel\maestro`, fora do workspace de trabalho. |

## 3. Padrões técnicos

- **Python 3.12+**, `pyproject.toml` (hatchling), `src/maestro/` layout, CLI com **Typer**, saída com **Rich**.
- Camadas: `domain/` (entidades, value objects, portas) · `application/` (casos de uso) · `infrastructure/` (adaptadores: devops providers, llm providers, kb sqlite, audit, charts) · `presentation/` (`cli/`, `mcp/`).
- **MCP**: FastMCP (`mcp` SDK oficial), transporte stdio, manifesto `tools.yaml` com allow-list e flag `read_only`.
- **RAG**: SQLite FTS5 + BM25, chunking por heading de Markdown, metadados (`projeto`, `tema`, `fonte`); sem dependência de embedding por padrão (opcional: `sentence-transformers` em extra `[embeddings]`).
- **LLM providers**: porta `LLMProvider`; implementações `dry` (determinístico, para testes/demo), `openai_compatible` (qualquer endpoint OpenAI-like), `bedrock` (boto3, extra `[aws]`). Timeout explícito, retry com backoff e teto, custo estimado por chamada.
- **DevOps providers**: porta `DevOpsProvider`; implementações `local` (JSON sintético gerado por `maestro seed`), `github` (REST, token opcional), `azure_devops` (REST, PAT opcional).
- **Métricas**: DORA (lead time, deployment frequency, change failure rate, MTTR) + fluxo de PR (tempo até 1ª revisão, tamanho, taxa de retrabalho). Gráficos com matplotlib → PNG em `docs/assets/charts/` (gerados por `maestro charts`).
- **Testes**: pytest + hypothesis (propriedades do cálculo DORA) + testes de arquitetura (import-linter) + suíte de prompt-injection.
- **Qualidade**: ruff (lint+format), mypy, pre-commit, GitHub Actions (`ci.yml`: lint → type → test → cobertura; `docs.yml`: build e deploy MkDocs em Pages).
- **Licença** MIT. **Idioma**: código e identificadores em inglês; README e wiki em PT-BR com resumo em EN.

## 4. Aplicação do baseline NFR para plataformas com agentes de IA

Maestro é uma **ferramenta local de linha de comando / servidor MCP stdio**, sem endpoint HTTP, sem upload,
sem multiusuário. Aplica-se o pertinente; o restante é declarado não aplicável em vez de "deixado para depois".

| # | Item | Aqui |
|---|---|---|
| 1 | Autenticação e RBAC | ➖ sem usuários nem endpoint. Credenciais de integração são do operador, lidas de variável de ambiente; o agente usa identidade própria (`MAESTRO_BOT_TOKEN`) quando publica — nunca a credencial pessoal por padrão. |
| 2 | Criptografia e segredos | ✅ nenhum segredo em código, `.env.example` só com chaves vazias, `.gitignore` cobre `.env`, `audit/`, `data/local/`. Scanner de segredos (gitleaks) em CI. |
| 3 | Upload seguro | ➖ não se aplica. |
| 4 | Auditoria append-only | ✅ `audit/*.jsonl`, escrita exclusivamente em modo append pelo `AuditLogger`; teste garante ausência de qualquer caminho de escrita que não seja append. |
| 5 | Máquina de estados | ✅ pipeline de revisão com estados explícitos (`collected → gated → analyzed → validated → published/dry_run`); transição inválida levanta exceção. |
| 6 | Agente sem acesso irrestrito | ✅ allow-list em `tools.yaml` e por agente; limite de chamadas e de tokens por execução (`max_calls`, `max_tokens`) com teto padrão. |
| 7 | Prompt injection | ✅ P6 + schema pydantic na saída + suíte de ataques em `tests/security/test_prompt_injection.py`. |
| 8 | Human-in-the-loop | ✅ dry-run por padrão; publicação só com `--confirm`; verdictos `REPROVADO` e `REVISAO_MANUAL` nunca aplicam voto automático de aprovação. |
| 9 | Observabilidade | ✅ log JSON estruturado (structlog) sem PII, `correlation_id` gerado na borda (CLI/MCP) e propagado até provider; métricas de duração e custo por execução no audit. Export OTLP é **fora do MVP**. |
| 10 | Resiliência de integrações | ✅ timeout explícito, retry com backoff e teto em todo provider remoto; teste simulando indisponibilidade de cada provider. Idempotência de publicação por `(pr_id, hash do parecer)`. |
| 11 | Backup | ➖ não há dado de produção; KB e audit são regeneráveis a partir do repositório. |
| 12 | DevSecOps | ✅ ruff, mypy, pytest + cobertura, gitleaks, `pip-audit` em CI; falha barra o merge (branch protection em `main`). |
| 13 | Segregação de ambientes | ➖ ferramenta local; a separação é `provider=local` (sintético) × providers remotos (opt-in). |

**Fora do MVP (declarado, não planejado):** export OTLP para coletor real, multi-provider com fallback/routing, FinOps por agente, red teaming contínuo, dashboard web, GitHub App com webhooks.

**Valores que dependem de decisão do dono:** limites do gate de porte (padrão proposto: 50 arquivos / 3.000 linhas), teto de custo por execução (padrão proposto: US$ 0,50), cobertura mínima (85 %). Ficam em `maestro.toml` e podem mudar sem alterar código.
