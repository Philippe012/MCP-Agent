from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Note:
    note_id: str
    title: str
    tags: tuple[str, ...]


class NoteStore:
    def __init__(self, notes: list[Note]) -> None:
        self.notes = notes

    def find_by_tag(self, query: str) -> list[Note]:
        """Substring search across tags - intentionally fuzzy, the same
        way searching by title text would be."""
        return [n for n in self.notes if any(query in t for t in n.tags)]

    def rename_tag(self, old: str, new: str) -> int:
        """Rename every occurrence of the exact tag `old` to `new`.
        Unlike find_by_tag, this matches by exact tag value - a tag that
        merely contains `old` as a substring (e.g. "workshop" containing
        "work") must not be touched. Returns how many notes were changed.
        """
        changed = 0
        updated = []
        for note in self.notes:
            if old in note.tags:
                new_tags = tuple(new if t == old else t for t in note.tags)
                updated.append(replace(note, tags=new_tags))
                changed += 1
            else:
                updated.append(note)
        self.notes = updated
        return changed
