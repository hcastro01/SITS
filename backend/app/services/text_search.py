"""Normalización SQL compartida para búsquedas de texto en SQLite."""

import unicodedata

from sqlalchemy import func, or_

_ACCENT_REPLACEMENTS = (
    ("Á", "A"), ("À", "A"), ("Ä", "A"), ("Â", "A"), ("á", "a"), ("à", "a"), ("ä", "a"), ("â", "a"),
    ("É", "E"), ("È", "E"), ("Ë", "E"), ("Ê", "E"), ("é", "e"), ("è", "e"), ("ë", "e"), ("ê", "e"),
    ("Í", "I"), ("Ì", "I"), ("Ï", "I"), ("Î", "I"), ("í", "i"), ("ì", "i"), ("ï", "i"), ("î", "i"),
    ("Ó", "O"), ("Ò", "O"), ("Ö", "O"), ("Ô", "O"), ("ó", "o"), ("ò", "o"), ("ö", "o"), ("ô", "o"),
    ("Ú", "U"), ("Ù", "U"), ("Ü", "U"), ("Û", "U"), ("ú", "u"), ("ù", "u"), ("ü", "u"), ("û", "u"),
    ("Ñ", "N"), ("ñ", "n"),
)


def normalize_term(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFKD", value.strip().casefold())
        if not unicodedata.combining(character)
    )


def normalized_column(column):
    expression = func.coalesce(column, "")
    for source, replacement in _ACCENT_REPLACEMENTS:
        expression = func.replace(expression, source, replacement)
    return func.lower(expression)


def matches(term: str, *columns):
    normalized = normalize_term(term).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{normalized}%"
    return or_(*(normalized_column(column).like(pattern, escape="\\") for column in columns))
