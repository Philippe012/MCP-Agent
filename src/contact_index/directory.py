from dataclasses import dataclass


@dataclass(frozen=True)
class Contact:
    contact_id: str
    full_name: str
    labels: tuple[str, ...]
    phone: str


class Directory:
    def __init__(self, contacts: list[Contact]) -> None:
        self.contacts = contacts

    def find(self, query: str) -> list[Contact]:
        query = query.strip().lower()

        if not query:
            return list(self.contacts)

        results: list[Contact] = []

        for contact in self.contacts:
            matched = query in contact.full_name.lower()

            if not matched:
                matched = any(
                    query in label.lower()
                    for label in contact.labels
                )

            if matched:
                results.append(contact)

        return results
