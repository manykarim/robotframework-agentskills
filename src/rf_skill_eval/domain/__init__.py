"""Pure domain layer — no I/O, no subprocess, no filesystem access.

Modules here define value objects, entities and aggregates that describe
the evaluation domain. Downstream layers (`application`, `infrastructure`)
depend on these types; the domain layer depends on nothing internal.
"""
