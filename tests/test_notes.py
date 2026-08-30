from notes.store import Note, NoteStore

NOTES = [
    Note("N1", "Groceries", ("errand", "home")),
    Note("N2", "Fix sink", ("home", "repair")),
]


def test_find_by_tag_substring_match():
    store = NoteStore(list(NOTES))
    assert [n.note_id for n in store.find_by_tag("err")] == ["N1"]


def test_rename_tag_basic():
    store = NoteStore(list(NOTES))
    changed = store.rename_tag("home", "house")
    assert changed == 2
    by_id = {n.note_id: n for n in store.notes}
    assert by_id["N1"].tags == ("errand", "house")
    assert by_id["N2"].tags == ("house", "repair")
