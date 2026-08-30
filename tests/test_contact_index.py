from contact_index.directory import Directory, Contact


CONTACTS = [
    Contact("C1", "Philippe Mugisha", ("family", "primary"), "555-0101"),
    Contact("C2", "Philippe Engineer", ("work", "manager"), "555-0202"),
]


def test_find_by_name():
    directory = Directory(CONTACTS)
    assert [c.contact_id for c in directory.find("shah")] == ["C2"]


def test_empty_query_returns_all():
    directory = Directory(CONTACTS)
    assert [c.contact_id for c in directory.find("")] == ["C1", "C2"]
