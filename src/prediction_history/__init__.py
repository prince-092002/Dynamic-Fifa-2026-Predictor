"""Prediction History — an automatic, immutable audit trail of live forecasts.

Each meaningful production refresh archives the published forecast (tournament-level
odds + the then-upcoming matchday predictions) as a small JSON snapshot under
``data/prediction_history/``. Snapshots are never mutated; actual match results are
joined against the immutable committed ``knockout_bracket.json`` at render time to derive
correct/incorrect outcomes. This package only *consumes and preserves* existing forecast
outputs — it does not change how any prediction is produced.
"""
