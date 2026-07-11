"""Phase 5H-A — Zafronix World Cup, squad & historical intelligence enrichment.

Enrichment-only. football-data.org remains the primary live-tournament-truth provider;
nothing in this package overwrites live tournament state. Modules here fetch, normalize,
resolve entities, and build leakage-safe World Cup history / squad features that are
evaluated as challengers against the frozen production XGBoost baseline.
"""
