"""Controlled team identity mapping: slugs, ISO codes, and flag emoji.

Only teams in this validated map receive a flag; anything unmapped renders as
plain text rather than guessing. England and Scotland use Unicode tag-sequence
flags because they are not ISO 3166-1 countries.
"""

from __future__ import annotations

import re
import unicodedata

# provider team name -> (ISO-like code, flag emoji)
_FLAG_ENGLAND = "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"
_FLAG_SCOTLAND = "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F"

TEAM_CODES: dict[str, str] = {
    "Algeria": "DZ", "Argentina": "AR", "Australia": "AU", "Austria": "AT", "Belgium": "BE",
    "Bosnia-Herzegovina": "BA", "Brazil": "BR", "Canada": "CA", "Cape Verde Islands": "CV",
    "Colombia": "CO", "Congo DR": "CD", "Croatia": "HR", "Curacao": "CW", "Czechia": "CZ",
    "Ecuador": "EC", "Egypt": "EG", "England": "GB-ENG", "France": "FR", "Germany": "DE",
    "Ghana": "GH", "Haiti": "HT", "Iran": "IR", "Iraq": "IQ", "Ivory Coast": "CI",
    "Japan": "JP", "Jordan": "JO", "Mexico": "MX", "Morocco": "MA", "Netherlands": "NL",
    "New Zealand": "NZ", "Norway": "NO", "Panama": "PA", "Paraguay": "PY", "Portugal": "PT",
    "Qatar": "QA", "Saudi Arabia": "SA", "Scotland": "GB-SCT", "Senegal": "SN",
    "South Africa": "ZA", "South Korea": "KR", "Spain": "ES", "Sweden": "SE",
    "Switzerland": "CH", "Tunisia": "TN", "Turkey": "TR", "United States": "US",
    "Uruguay": "UY", "Uzbekistan": "UZ",
}


def _ascii_fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def team_slug(name: str) -> str:
    folded = _ascii_fold(str(name)).lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


def team_code(name: str) -> str | None:
    return TEAM_CODES.get(_ascii_fold(str(name)))


def team_flag(name: str) -> str | None:
    code = team_code(name)
    if code is None:
        return None
    if code == "GB-ENG":
        return _FLAG_ENGLAND
    if code == "GB-SCT":
        return _FLAG_SCOTLAND
    if len(code) == 2 and code.isalpha():
        return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())
    return None
