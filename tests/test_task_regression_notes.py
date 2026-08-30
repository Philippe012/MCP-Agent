from notes.store import Note, NoteStore


def test_rename_does_not_touch_a_tag_that_only_contains_the_word():
    store = NoteStore([Note("N1", "A", ("work",)), Note("N2", "B", ("workshop",))])
    changed = store.rename_tag("work", "job")
    assert changed == 1
    by_id = {n.note_id: n for n in store.notes}
    assert by_id["N1"].tags == ("job",)
    assert by_id["N2"].tags == ("workshop",)
