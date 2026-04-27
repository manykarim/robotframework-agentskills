# ADR-002: DDD Bounded-Context Layout for the Eval Subsystem

**Status:** Accepted
**Date:** 2026-04-14
**Deciders:** System Architecture
**Related:** ADR-003, ADR-004, ADR-006

---

## Context

The eval harness spans multiple concerns: planning, invocation, telemetry parsing,
statistical scoring, persistence, reporting, and CI glue. A naive "one big module" layout
(as in many research scripts) would quickly tangle these — e.g., metric code reading
environment variables, CLI flags bleeding into statistics, or storage schemas driving
domain types.

The implementation plan (`rf-agentskills-eval-implementation-plan.md`) sketches a layered
layout (`telemetry/`, `runner/`, `tasks/`, `analysis/`, `report/`). This is a reasonable
start but is organized by **technical function**, not by **domain boundary**. Without
explicit bounded contexts we get:

- Coupling drift: a "metric" that quietly depends on the Jinja template's column order.
- Schema leakage: the Claude Code session JSONL format (owned upstream by Anthropic)
  bleeding into reporting code, making an Anthropic schema bump ripple across the codebase.
- Core-domain dilution: the **statistical scoring** code (the actual reason this project
  exists) buried in an `analysis/` grab bag alongside CSV formatters.

Principles to apply:

1. **Core domain first.** Scoring & Verdict is the core — everything else is support.
2. **Isolate upstream schemas** behind an anti-corruption layer.
3. **Pure domain, imperative shell.** Domain logic is I/O-free; infrastructure adapts.
4. **Events over queries** where practical — contexts publish, others subscribe.

---

## Decision

**Adopt an explicit DDD bounded-context layout with six contexts** and a strict
layering: `domain/` (pure) → `application/` (use cases) → `infrastructure/` (I/O).

### The six bounded contexts

| # | Context | Classification | Primary responsibility |
|---|---------|----------------|------------------------|
| 1 | Evaluation Orchestration | Supporting | Plan + sequence `RunBatch` over cells |
| 2 | Skill Invocation | Supporting | Execute one Claude Code session per cell |
| 3 | Dataset / Fixtures | Supporting | Version tasks + SUT fixtures |
| 4 | Telemetry & Metrics | **Core** | Parse JSONL → metrics dataframe |
| 5 | Scoring & Verdict | **Core** | Compare arms; render shipping verdict |
| 6 | Result Persistence & Reporting | Supporting | Durable artifacts + scorecards |
| 7 | CI Integration | Generic | GH Actions adapter |

Telemetry and Scoring are both marked **core** because the harness's value comes from
(a) extracting statistically meaningful signal from stochastic sessions, and (b) turning
that signal into a defensible ship/hold decision. Neither is "just plumbing."

### Layering rules

```
infrastructure  ──depends on──▶  application  ──depends on──▶  domain
                                                                  ▲
                                               (domain depends on nothing project-internal)
```

- `domain/` imports only stdlib + pydantic + polars/numpy (value types). No filesystem,
  no subprocess, no env vars, no SQLAlchemy, no Jinja.
- `application/` orchestrates use cases. Depends on `domain/` and on `domain/persistence/`
  *protocols* (not implementations).
- `infrastructure/` provides concrete adapters. Implements the persistence protocols;
  owns subprocess calls, HTTP, Jinja, SQLite.

### Communication patterns

- **Within a context:** direct method calls on aggregates.
- **Across contexts:** domain events published via an in-process event bus. Downstream
  contexts subscribe. No context reads another's aggregate state directly.
- **Across processes (CI vs local):** artifacts on disk (run directories, Parquet, SQLite).
  The event bus is in-process only; persistence is the durable boundary.

### Anti-corruption layer (ACL)

- The Claude Code session JSONL schema is **owned upstream by Anthropic**. Telemetry's
  `schema.py` defines internal types (`ToolCall`, `ThinkingBlock`, …) that are **not**
  thin wrappers over the raw dicts — they are a stable internal vocabulary. A schema
  change upstream is contained to one file: the parser.
- The `claude` CLI is wrapped by `infrastructure/runner/claude_cli.py`; the rest of the
  domain never sees CLI flags.

---

## Consequences

### Positive

- **Core domain is legible.** `domain/scoring/` contains ~400–600 lines of pure statistics;
  reviewers can read it end-to-end without chasing adapters.
- **Upstream changes are contained.** When Anthropic ships a new JSONL field (they do
  regularly), only `telemetry/schema.py` and the relevant metric functions change.
- **Testability.** Domain is trivially unit-testable without fixtures, subprocess, or
  filesystem. Integration tests exercise `infrastructure/`.
- **Future-proofing.** If we later want to grade OpenAI Codex sessions or Cursor sessions,
  Skill Invocation and Telemetry get new adapters/parsers without touching Scoring.
- **Clear ownership.** Each context's module is the single place to look for its concern;
  PRs don't sprawl across the tree.

### Negative

- **More files for a given change.** A new metric touches: `domain/telemetry/metrics/*.py`
  (implementation), `domain/telemetry/metrics/catalog.py` (registration), and often
  `domain/scoring/gate.py` (if primary). Mitigated by: the registry pattern makes each
  touch small and mechanical.
- **Upfront design cost.** Engineers unfamiliar with DDD may find the layout heavier than
  "just put it in `analysis.py`." Mitigated by: the `ddd-design.md` document names every
  aggregate/entity/VO; newcomers have a map.
- **Risk of anemic-domain anti-pattern.** Value objects and aggregates can degenerate into
  dataclasses if behavior is all pushed into `application/`. Mitigated by: invariants are
  enforced inside aggregates (e.g., `RunBatch` refuses to add cells after `start()`;
  `Scorecard.render_verdict()` is a method, not a free function).

### Neutral

- Slight indirection cost (~one extra level of imports) — invisible at runtime.

---

## Alternatives Considered

### Flat layering (the implementation plan's initial sketch)
`telemetry/ runner/ tasks/ analysis/ report/` — one directory per technical function.

- **Pros:** Familiar to Python developers; easy to start.
- **Cons:** Mixes core and supporting concerns; no ACL — Anthropic schema leaks downstream;
  statistical scoring code tends to sprawl across `analysis/` and `report/`.
- **Why rejected:** Encodes concerns by function, not by domain. Exactly the tangling this
  ADR exists to prevent.

### Hexagonal / ports-and-adapters (no explicit bounded contexts)
A single domain core with pluggable adapters.

- **Pros:** Clean domain/infrastructure split; familiar to architects.
- **Cons:** Treats the whole domain as one blob. A 6-month-older version of this project
  would have a 3000-line "domain" module. Doesn't scale the way bounded contexts do.
- **Why rejected:** Hexagonal is a **complementary** pattern — we use it **within**
  contexts (the `domain → application → infrastructure` layering). Bounded contexts
  carve the problem space; hexagonal organizes each carve.

### Microservices / separate Python packages
Publish `eval-telemetry`, `eval-scoring`, etc. as independent PyPI packages.

- **Pros:** Maximum isolation; other projects could adopt individual components.
- **Cons:** Massive overhead for a one-team project. Cross-package development friction.
- **Why rejected:** Premature decomposition. Revisit if we ever need to publish the
  telemetry library separately (the parent doc hints at a `cc-telemetry` library worth
  spinning out later).

### Onion architecture (rings of concentric dependency)
Domain entities at the center, use cases around, gateways outside, UI outermost.

- **Pros:** Clear dependency direction.
- **Cons:** Over-prescriptive for this size; onion dogma often produces deeper trees than
  useful.
- **Why rejected:** The simpler three-layer `domain/application/infrastructure/` with
  bounded contexts achieves the same goals with less ceremony.

---

## Implementation Notes

- Each bounded context has its own subdirectory under `domain/` with:
  `aggregates.py`, `events.py`, and optionally `invariants.py`.
- The event bus is a simple in-process `blinker`-like dispatcher or a plain dict of
  subscribers. No Kafka, no Redis. If the harness ever needs distributed coordination it
  will be via on-disk artifacts, not an in-process bus.
- `domain/persistence/repositories.py` defines `Protocol` classes; concrete impls live in
  `infrastructure/persistence/`.
- Application-layer command handlers (`application/plan_batch.py`, etc.) are the only
  place that wires events from one context to another.

---

## References

- Evans, *Domain-Driven Design* (2003) — bounded contexts, context map.
- Vernon, *Implementing DDD* (2013) — pragmatic context patterns.
- `docs/ci/rf-agentskills-eval-implementation-plan.md` — original flat layout.
- `docs/skill-architecture-review.md` — precedent for "single source of truth +
  derived channels" in this repo.
