# TASKS — Maestro

**Base:** PLAN v1.0 · **Executor:** Michel Bueno Silva + squad agêntico · **Fonte de verdade do progresso** (P11)
**Status permitidos:** `Aberto` · `Em Andamento` · `Concluido` · `Bloqueado`
**Regra:** uma task por vez; `Concluido` exige **Evidência** (commit/arquivo/saída). Ao pausar, atualizar este arquivo e commitar.

> Colunas: **ID** (estável — nunca renumerar) · **Fase** · **Tipo** · **Est.** = horas · **Status** · **Evidência**

| ID | Fase | Tarefa | Itens | Tipo | Est. | Status | Evidência |
|---|---|---|---|---|---|---|---|
| T01 | 0 | Aprovar D-01…D-05 (nome, idioma, wiki, stack do demo, integração) e fixar no `constitution.md`/SPEC | SPEC §6 | Decisão | 0.5 | Concluido | Aprovado pelo dono em 24/11/2026: `maestro` · README PT-BR+EN · MkDocs Material · demo Python · GitHub primeiro |
| T02 | 0 | Criar repo público `bife29/maestro` (MIT), branch protection em `main` (CI obrigatório), descrição + topics (`mcp`, `rag`, `ai-agents`, `dora-metrics`, `clean-architecture`, `python`) | CA-00 | Infra | 0.5 | Concluido | https://github.com/bife29/maestro criado via API em 24/11 (público, MIT); 10 topics; branch protection em `main` com 3 checks obrigatórios + force-push bloqueado |
| T03 | 0 | Esqueleto: `pyproject.toml` (hatchling, extras `dev`/`aws`/`embeddings`), `src/maestro/{domain,application,infrastructure,presentation}`, `maestro.toml`, `.env.example`, `.gitignore` (`.env`, `audit/`, `data/local/`, `out/`), `LICENSE`, `AGENTS.md` | P3, P2 | Codificação | 1 | Concluido | commit 3cff547 — `pyproject.toml`, `src/maestro/*`, `maestro.toml`, `.env.example`, `.gitignore`, `LICENSE`, `AGENTS.md` |
| T04 | 0 | Qualidade: ruff + mypy (strict em `domain`), pytest + cobertura, import-linter (contratos de camada), pre-commit, gitleaks, pip-audit; `ci.yml` rodando tudo em push/PR | P9, CA-07 | Infra | 1 | Concluido | commit 3cff547 — ruff/mypy/import-linter (3 contratos KEPT)/pytest 86%/pre-commit/gitleaks/pip-audit; `.github/workflows/ci.yml` |
| T05 | 0 | README v0 ("em construção", badges reais, propósito, roadmap por fases), `specs/` publicadas, 1º push, CI verde | CA-00 | Documentação | 0.5 | Concluido | push `1410478`, CI verde (quality 3.12/3.13 + security) — https://github.com/bife29/maestro/actions |
| T06 | 1 | `domain`: entidades `Repository`, `PullRequest`, `Commit`, `Build`, `Deployment`, `Incident`, value objects de período; portas `DevOpsProvider`, `Clock`, `ChartRenderer` | PLAN §1 | Codificação | 1 | Aberto | — |
| T07 | 1 | `GenerateSeed` + provider `local_json`: 6 repos `atlas-*`, 12 meses, perfis DORA distintos, `PR-07` (pequena, 2 achados plantados) e `PR-13` (80 arquivos); determinístico por `--seed`; comando `maestro seed` | F-01, RN-07 | Codificação | 1.5 | Aberto | — |
| T08 | 1 | `ComputeDora`: lead time, deployment frequency, CFR, MTTR por repo/período + classificação Elite/High/Medium/Low; `ComputePrFlow`; comando `maestro metrics dora|pr-flow` (Rich + `--json`) | F-02, F-03 | Codificação | 1.5 | Aberto | — |
| T09 | 1 | Testes: unitários das métricas com casos de borda (zero deploys, incidente sem fim), **hypothesis** (monotonicidade, invariantes), teste de determinismo do seed | CA-01 | Teste | 1 | Aberto | — |
| T10 | 1 | `RenderCharts` (matplotlib): 4 painéis DORA mensal, distribuição de tamanho de PR, heatmap deploys × dia da semana, funil de revisão; `maestro charts` → `docs/assets/charts/*.png`; push dos PNGs | F-04 | Codificação | 1 | Aberto | — |
| T11 | 2 | `domain`: `Document`, `Chunk`, porta `KnowledgeStore`; `infrastructure/kb/sqlite_fts5`: chunking por heading, front-matter `project`/`topic`, BM25, filtros | F-05 | Codificação | 1.5 | Aberto | — |
| T12 | 2 | 40 docs sintéticos gerados pelo seed (ADRs, runbooks, post-mortems, padrão arquitetural Python, baseline de segurança multi-stack) em `data/sample/docs/`; comandos `kb index|ask|status|note` | F-05, RN-08 | Codificação | 1 | Aberto | — |
| T13 | 2 | Testes da KB: indexação idempotente, ranking (doc relevante em top-3), filtro por projeto/tema, `note` reindexa | CA-02 | Teste | 0.5 | Aberto | — |
| T14 | 3 | `infrastructure/audit/jsonl_append_only` + porta `AuditSink`; `correlation_id` na borda; teste de append-only (nenhum `open(..., "w")` no módulo) | F-09, P7 | Codificação | 1 | Aberto | — |
| T15 | 3 | `presentation/mcp/server.py` (FastMCP stdio) + `tools.yaml` (allow-list, `read_only`): `list_repositories`, `get_pull_request`, `dora_metrics`, `kb_search`, `kb_status`, `audit_tail`; cada chamada audita; `maestro mcp serve`; exemplos `.vscode/mcp.json` e Claude Desktop em `docs/mcp.md` | F-06, P5 | Codificação | 1.5 | Aberto | — |
| T16 | 3 | Teste do servidor MCP com cliente em processo: lista exatamente as tools do YAML; tool não listada é recusada; audit recebe 1 linha por chamada | CA-03 | Teste | 0.5 | Aberto | — |
| T17 | 4 | `domain/review.py`: `ReviewVerdict` (enum 4 verdictos), `Finding` (severidade, arquivo, linha, justificativa, fonte KB), estados do pipeline e transições válidas; porta `LLMProvider` (timeout, retries, max_tokens, custo) | F-07, NFR 5 | Codificação | 1 | Aberto | — |
| T18 | 4 | `ReviewPullRequest` (state machine collect→gate→ground→analyze→validate→render→publish/dry_run); gate de porte (RN-02); RN-01, RN-03; render Markdown com aviso de IA e rodapé de custo | F-07, P4, P8 | Codificação | 1.5 | Aberto | — |
| T19 | 4 | Provider LLM `dry`: heurísticas reais (segredo hardcoded, SQL concatenado, `except: pass`, ausência de teste para arquivo novo) que produzem achados determinísticos; prompts versionados em `src/maestro/prompts/` com blocos delimitados (RN-05) | P2, P6 | Codificação | 1 | Aberto | — |
| T20 | 4 | Publicação: `DevOpsProvider.publish_review` idempotente (RN-04), `--confirm` obrigatório, voto só quando permitido; `local` grava em `out/`; mensagem clara sem token | RN-04, NFR 8 | Codificação | 0.5 | Aberto | — |
| T21 | 4 | Testes: `PR-07` → parecer válido; `PR-13` → `REVISAO_MANUAL` sem chamar LLM (spy); schema inválido → RN-01; **suíte de prompt-injection** (`tests/security/`: instruções embutidas no diff/descrição não alteram verdicto nem vazam prompt de sistema); indisponibilidade do provider → erro controlado | CA-04, NFR 7, NFR 10 | Teste | 1.5 | Aberto | — |
| T22 | 4 | Artefatos do squad: `.github/agents/code-reviewer.agent.md` (gatilhos, fontes, verdictos, regra de porte, aviso de IA), `.github/instructions/security-baseline.instructions.md` e `python-architecture.instructions.md` (genéricos), `PULL_REQUEST_TEMPLATE.md` com manifesto obrigatório | F-08 | Documentação | 0.5 | Aberto | — |
| T23 | 5 | MkDocs Material: `mkdocs.yml` (tema, Mermaid, busca, PT-BR), `docs.yml` deploy em Pages, páginas `index`, `architecture` (C4 L1–L2 Mermaid), `review-flow` (sequence), `rag` (flow) | F-10 | Documentação | 1.5 | Aberto | — |
| T24 | 5 | Páginas `mcp` (como plugar), `metrics` (PNGs + leitura), `governance` (tabela NFR aplicada), `roadmap`, `adr/` (ADR-001 Clean Arch, ADR-002 FTS5 sem embeddings, ADR-003 dry provider, ADR-004 gate de porte) | F-10 | Documentação | 1 | Aberto | — |
| T25 | 5 | README final: badges, GIF do terminal (`maestro demo`), mapa competências ↔ módulos, quick start, seção EN; comando `maestro demo` que encadeia seed → metrics → charts → kb → review | F-11 | Documentação | 1 | Aberto | — |
| T26 | 5 | Revisão P1 (zero dado de empregador) em todo o repo: grep por termos sensíveis, nomes, URLs; gitleaks; ajuste do que aparecer | P1 | Revisão | 0.5 | Aberto | — |
| T27 | 5 | Publicar Pages, conferir links/badges, release `v0.1.0` com notas | CA-05 | Infra | 0.5 | Aberto | — |
| T28 | 6 | Provider `github_rest` (PR, arquivos, diff, comentários; publish idempotente); teste com respostas gravadas | F-12 | Integração | 2 | Aberto | — |
| T29 | 6 | Provider LLM `openai_compatible` (timeout/retry/custo); `bedrock` atrás de extra `[aws]` | F-12 | Integração | 1.5 | Aberto | — |
| T30 | 6 | Demo real: `maestro review <PR de repo meu> --provider github` em dry-run; print na wiki; release `v0.2.0` | CA-06 | Integração | 0.5 | Aberto | — |

**Total estimado:** 28 h (3 h concluídas — Fase 0 concluída em 24/11/2026).

## Pré-condições (fora do squad)

| # | Item | Dono | Status |
|---|---|---|---|
| P-01 | Decisões D-01…D-05 da SPEC §6 | Michel | Concluido |
| P-02 | Credencial GitHub para push (já existe `git:https://github.com` no Credential Manager; sem `gh` CLI) e para criar o repo (via web ou token com escopo `repo`) | Michel | Concluido (credencial do Credential Manager via `git credential fill`, usada em memória) |
| P-03 | Python 3.12+ instalado fora do venv do trabalho (hoje `python` global não está no PATH) | Michel | Concluido (py 3.14 via `py` launcher; venv próprio em `maestro\.venv`) |
| P-04 | Confirmar que o projeto fica em `C:\Projetos\Michel\maestro` e fora de qualquer relatório (P12) | Michel | Concluido (aprovado 24/11) |
