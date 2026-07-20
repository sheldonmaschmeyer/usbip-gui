"""Shared heuristics for USB string descriptors."""


def is_generic_manufacturer(manufacturer: str) -> bool:
    """Return True if the manufacturer string is a generic Windows fallback."""
    if not manufacturer:
        return False

    mfg_lower = manufacturer.lower()
    return (
        mfg_lower
        in (
            "microsoft",
            "generic",
            "standard",
            "compatible",
            "unknown",
        )
        or mfg_lower.startswith("(standard")
        or mfg_lower.startswith("(generic")
    )
