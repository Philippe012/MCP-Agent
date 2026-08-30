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
        return [n for n in self.notes if any(query in t for t in n.tags)]

    def rename_tag(self, old: str, new: str) -> int:
        changed = 0
        updated = []
        for note in self.notes:
            if any(old in t for t in note.tags):
                new_tags = tuple(new if old in t else t for t in note.tags)
                updated.append(replace(note, tags=new_tags))
                changed += 1
            else:
                updated.append(note)
        self.notes = updated
        return changed
