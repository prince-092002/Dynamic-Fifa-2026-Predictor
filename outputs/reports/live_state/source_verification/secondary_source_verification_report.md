# Secondary Source Verification Report

Secondary sources are sanity checks only. This project does not bypass blocks and does not replace API-Football data with scraped secondary data by default.

| Source | Reachable | Parseable | Detected | Recommendation |
|---|---|---|---|---|
| FIFA official | True | True | basic page text parseable | Use only as a sanity-check report; do not overwrite API-Football state by default. |
| ESPN soccer | True | True | basic page text parseable | Use only as a sanity-check report; do not overwrite API-Football state by default. |
| FOX Sports soccer | True | True | basic page text parseable | Use only as a sanity-check report; do not overwrite API-Football state by default. |
| Reuters sports | False | False | HTTP 401 | Unavailable for automated verification; keep API/local state unchanged. |