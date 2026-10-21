import re


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def validate_identifier(value: str, label: str) -> str:
    if not _IDENTIFIER.fullmatch(value) or value in {".", ".."}:
        raise ValueError(
            f"invalid {label}: {value!r}; use 1-64 letters, digits, dots, underscores, or hyphens"
        )
    return value
