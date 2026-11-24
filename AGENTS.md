# AGENTS.md — como agentes de IA trabalham neste repositório

Este arquivo é lido por assistentes de código (GitHub Copilot, Claude, Cursor…). Ele resume as regras que um
agente precisa respeitar para contribuir aqui. A fonte completa está em `specs/`.

## Leia antes de agir
1. `specs/constitution.md` — princípios inegociáveis (P1…P12) e baseline NFR.
2. `specs/SPEC-001-maestro-toolkit.md` — funcionalidades, regras RN-xx e critérios de aceite.
3. `specs/PLAN.md` — arquitetura, pastas, fluxo do agente de revisão, fases.
4. `specs/TASKS.md` — **fonte de verdade do progresso**. Pegue a próxima task `Aberto` cuja fase anterior esteja `Concluido`.

## Regras rígidas
- **Zero dado de empregador** (P1). Nomes de sistemas, pessoas, URLs e regras são sintéticos (`atlas-*`). Em dúvida, não escreva.
- **Sem segredo em código** — tokens só por variável de ambiente; `.env` nunca é versionado.
- **Clean Architecture** (P3): `presentation → application → domain`; `infrastructure → domain`. `domain` não importa I/O.
  `lint-imports` falha o build se você violar.
- **Saída de LLM é dado, não decisão** (P4): valide contra schema; publicar exige `--confirm`.
- **Append-only** no audit (P7): nunca abra `audit/*.jsonl` em modo de escrita que não seja `"a"`.
- **Uma task por vez**; ao concluir, preencha a coluna **Evidência** em `TASKS.md`.
- **Main sempre verde** (P11): `ruff check . && ruff format --check . && mypy && lint-imports && pytest` antes de commitar.

## Convenções
- Python 3.12+, `src/` layout, Typer/Rich na CLI, pydantic v2 para schemas, structlog para log JSON sem PII.
- Testes em `tests/{unit,property,architecture,security,e2e}`; nome `test_<comportamento>`; AAA.
- Commits: Conventional Commits (`feat(kb): …`, `test(review): …`, `docs(wiki): …`, `chore(tasks): checkpoint fase N`).
- Idioma: código/identificadores em inglês; docs e specs em PT-BR.

## O que um agente NÃO faz aqui
- Não cria integração com sistema de empregador, não copia código de repositório de trabalho.
- Não inventa valores institucionais (limites, custos, SLAs) — eles vivem em `maestro.toml` e são decisão do dono.
- Não publica parecer em PR real sem `--confirm` explícito do operador.
