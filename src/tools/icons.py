def ensure_icon(name, default_icon):
    """Ensure the first character of the name is a text-based icon."""
    # Check if the first character is already an icon
    first_char = name[0]
    if not _is_text_icon(first_char):
        name = f"{default_icon} {name}"
    return name


def _is_text_icon(char):
    """Check if a character is likely a text-based icon."""
    # Check common Unicode ranges for emoji symbols
    return (
        "\U0001F300" <= char <= "\U0001F9FF"  # Emoji range
        or "\U0001FA70" <= char <= "\U0001FAFF"  # Supplemental Symbols
        or "\u2600" <= char <= "\u26FF"  # Miscellaneous Symbols
    )
