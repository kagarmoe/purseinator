from __future__ import annotations


def group_photos(
    filenames: list[str],
    is_card: list[bool],
) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    for filename, card in zip(filenames, is_card):
        if card:
            if current:
                groups.append(current)
                current = []
        else:
            current.append(filename)
    if current:
        groups.append(current)
    return groups
