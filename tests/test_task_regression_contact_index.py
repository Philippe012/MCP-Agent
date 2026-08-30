from contact_index.directory import Directory, Contact


def test_contact_matching_multiple_fields_is_returned_once():
    contact = Contact("C1", "Dana Reyes", ("family", "primary", "red"), "555-0101")
    directory = Directory([contact])

    results = directory.find("re")

    assert [c.contact_id for c in results] == ["C1"]
