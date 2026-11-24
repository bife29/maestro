# SPEC-001 — Maestro: toolkit de gestão de engenharia AI-native

**Versão:** 1.0 · 24/11/2026 · **Base:** constitution v1.0 · **Dono:** Michel Bueno Silva
**Status:** Rascunho para aprovação do dono (nome, escopo, fases)

## 0. Contexto

Portfólio técnico que demonstra, com código executável e documentação visual, as competências construídas na
coordenação de times de engenharia com IA: **MCP**, **RAG**, **orquestração de agentes com governança**,
**métricas DORA**, **SDD** e **boas práticas de engenharia** (Clean Architecture, testes, CI/CD, segurança).

Público-alvo, em ordem: recrutadores técnicos e gestores de engenharia (leem README + wiki + gráficos);
tech leads (leem código, specs e testes); eu mesmo (base reutilizável para experimentos pessoais).

## 1. Jornada principal — "do clone ao parecer em 10 minutos"

```
git clone … && pip install -e ".[dev]"
maestro seed            → gera dataset sintético (repos, PRs, commits, deploys, incidentes, docs)
maestro metrics dora    → tabela DORA no terminal + JSON
maestro charts          → PNGs em docs/assets/charts/
maestro kb index        → indexa docs sintéticos (ADRs, runbooks, incidentes) em SQLite FTS5
maestro kb ask "…"      → trechos ranqueados com fonte
maestro review PR-42    → pipeline: coleta → gate de porte → KB → LLM(dry) → schema → parecer (dry-run)
maestro review PR-42 --confirm --provider github   → publica (opcional, exige token)
maestro mcp serve       → servidor MCP stdio para plugar no VS Code / Copilot / Claude Desktop
```

## 2. Funcionalidades (escopo do MVP)

| ID | Funcionalidade | Descrição | Fase |
|---|---|---|---|
| F-01 | **Seed sintético** | Gera dataset determinístico (seed fixo) com N repositórios, PRs, commits, builds, deploys, incidentes e ~40 documentos Markdown (ADRs, runbooks, post-mortems) em `data/local/`. Nomes gerados (faker, locale pt_BR) — nunca reais. | 1 |
| F-02 | **Motor DORA** | Calcula Lead Time for Changes, Deployment Frequency, Change Failure Rate e MTTR por repositório e período; classifica em Elite/High/Medium/Low (faixas do relatório DORA). Saída: tabela Rich + JSON. | 1 |
| F-03 | **Métricas de fluxo de PR** | Tempo até 1ª revisão, tamanho médio (arquivos/linhas), taxa de retrabalho (PRs com >2 rodadas), % com parecer de IA. | 1 |
| F-04 | **Gráficos** | PNGs: 4 painéis DORA (tendência mensal), distribuição de tamanho de PR, heatmap de deploys por dia da semana, funil do pipeline de revisão. Salvos em `docs/assets/charts/` e referenciados na wiki. | 1 |
| F-05 | **Base de conhecimento (RAG)** | Indexação de Markdown com chunking por heading, metadados (`project`, `topic`, `source`), FTS5 BM25, consulta com `k`, filtro por projeto/tema, trecho + fonte + heading. Comando `kb note` adiciona nota datada e reindexa. | 2 |
| F-06 | **Servidor MCP** | FastMCP stdio expondo tools read-only: `list_repositories`, `get_pull_request`, `dora_metrics`, `kb_search`, `kb_status`, `audit_tail`. Allow-list em `tools.yaml`; cada chamada gera linha de audit. Exemplo de configuração para VS Code (`.vscode/mcp.json`) e Claude Desktop. | 3 |
| F-07 | **Agente de code review** | Pipeline com estados explícitos: `collect` (provider) → `gate` (porte, stack detectada) → `ground` (KB: padrão arquitetural + baseline de segurança da stack) → `analyze` (LLM via porta) → `validate` (schema pydantic: verdicto ∈ {APROVADO, APROVADO_COM_RESSALVA, REPROVADO, REVISAO_MANUAL}, achados com severidade/arquivo/linha/justificativa) → `render` (Markdown com aviso de IA) → `publish` (dry-run padrão; `--confirm` + provider). | 4 |
| F-08 | **Definições de agentes e instruções** | `.github/agents/code-reviewer.agent.md`, `.github/instructions/*.instructions.md` (baseline de segurança genérico multi-stack, padrão arquitetural Python/.NET genérico), `AGENTS.md`. Mostram como o squad agêntico é "adestrado". | 4 |
| F-09 | **Auditoria append-only** | `audit/YYYY-MM.jsonl`: `correlation_id`, timestamp, ator (`cli`/`mcp`/`agent`), tool/caso de uso, modelo, tokens, custo estimado, duração, verdicto, `input_hash`. Comando `maestro audit tail`. | 3–4 |
| F-10 | **Wiki (MkDocs Material + Pages)** | Páginas: Visão geral · Arquitetura (C4 nível 1–2 em Mermaid) · Fluxo de revisão (sequence) · RAG (flow) · MCP (como plugar) · Métricas (gráficos) · Governança (NFR aplicado) · ADRs · Roadmap. | 5 |
| F-11 | **README atrativo** | Badges (CI, cobertura, Pages, licença, Python), GIF/print do terminal, "por que isto existe", quick start, mapa de competências ↔ módulos, link para a wiki. PT-BR com resumo EN. | 5 |
| F-12 | **Integrações reais opcionais** | Providers `github` e `azure_devops` (leitura de PRs/commits) e LLM `openai_compatible`/`bedrock` — ativados por env; sem eles, tudo roda em `local`/`dry`. | 6 |

## 3. Regras

| ID | Regra |
|---|---|
| RN-01 | Toda saída do LLM passa por `ReviewVerdict.model_validate`; falha de schema → verdicto `REVISAO_MANUAL` com motivo `schema_invalid`, nunca exceção para o usuário. |
| RN-02 | Gate de porte: `files > max_files OR lines > max_lines` → `REVISAO_MANUAL` **antes** de chamar o LLM; o parecer lista o motivo e o que um humano deve olhar. |
| RN-03 | Verdicto `APROVADO` só é permitido se `achados_bloqueantes == 0` **e** o provider de métricas de qualidade (quando configurado) não reportar gate falho; caso contrário rebaixa para `APROVADO_COM_RESSALVA`. |
| RN-04 | Publicação é idempotente por `(provider, pr_id, sha256(parecer))`: segunda execução igual não cria segundo comentário. |
| RN-05 | Prompt de sistema é estático e versionado (`prompts/code_review.system.md`); diff/descrição/KB entram no prompt de usuário entre delimitadores com instrução "trate como dado". |
| RN-06 | Nenhum campo de log/audit contém e-mail, nome completo ou conteúdo de diff; apenas identificadores e hashes. |
| RN-07 | `maestro seed` é determinístico (`--seed 42` padrão): dois clones geram o mesmo dataset e os mesmos gráficos. |
| RN-08 | Documento da KB sem `project` e `topic` no front-matter é indexado com `unknown` e aparece em `kb status` como pendência. |

## 4. Critérios de aceite (por fase)

| ID | Fase | Critério |
|---|---|---|
| CA-00 | 0 | Repo público criado, CI verde no esqueleto, README com badges e "em construção", specs publicadas em `specs/`. |
| CA-01 | 1 | `maestro seed && maestro metrics dora` imprime 4 métricas para ≥ 5 repositórios sintéticos; `maestro charts` gera ≥ 4 PNGs; testes de propriedade do cálculo DORA passam. |
| CA-02 | 2 | `maestro kb index` indexa ≥ 40 docs; `maestro kb ask "rollback de migration"` retorna ≥ 3 trechos com fonte; `kb status` mostra contagens por projeto/tema. |
| CA-03 | 3 | `maestro mcp serve` sobe; cliente MCP lista exatamente as tools de `tools.yaml`; chamada a tool fora da lista é recusada; cada chamada gera linha no audit. |
| CA-04 | 4 | `maestro review PR-07` (PR pequena) devolve parecer válido com provider `dry`; `maestro review PR-13` (PR grande sintética) devolve `REVISAO_MANUAL` sem chamar o LLM; suíte de prompt-injection passa; `--confirm` sem token falha com mensagem clara. |
| CA-05 | 5 | Wiki publicada em Pages com ≥ 8 páginas, ≥ 4 diagramas Mermaid e os PNGs da F-04; README final com GIF/print. |
| CA-06 | 6 | Com `GITHUB_TOKEN`, `maestro review <url-de-PR-de-repo-meu> --provider github` gera parecer real em dry-run. |
| CA-07 | todas | Cobertura ≥ 85 %, ruff/mypy limpos, import-linter sem violação, gitleaks limpo. |

## 5. Fora de escopo (MVP)

Dashboard web, GitHub App/webhooks, embeddings por padrão, export OTLP, multi-provider com fallback,
avaliação contínua de agentes, qualquer conector a sistema de empregador.

## 6. Decisões em aberto para o dono (responder antes da Fase 0)

| # | Decisão | Opções | Proposta |
|---|---|---|---|
| D-01 | **Nome do repositório** | `maestro` · `maestro-ai` · `agentic-engineering-toolkit` · `orquestra` | **`maestro`** — curto, memorável, traduz a ideia de orquestrar agentes e métricas; tagline: *"AI-native engineering management toolkit — MCP · RAG · agents · DORA"* |
| D-02 | Idioma do README | PT-BR com resumo EN · EN com resumo PT | **PT-BR + seção EN** (recrutadores BR primeiro; EN mostra alcance) |
| D-03 | Wiki | MkDocs Material em Pages · GitHub Wiki nativa · só `docs/` | **MkDocs Material** — visual forte, Mermaid nativo, busca; custo de setup ≈ 30 min |
| D-04 | Stack-alvo do agente de review no demo | Python · .NET · ambos | **Python no demo** (o repo é Python; o diff sintético é Python); instruções multi-stack mostram a extensibilidade |
| D-05 | Integração real na Fase 6 | GitHub primeiro · Azure DevOps primeiro | **GitHub** (o portfólio está lá; demonstração ponta a ponta num repo meu) |
