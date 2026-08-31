from dataclasses import dataclass


@dataclass(frozen=True)
class Booking:
    room: str
    start: int  
    end: int


class Calendar:
    def __init__(self, bookings: list[Booking] | None = None) -> None:
        self.bookings: list[Booking] = list(bookings or [])

    def _overlaps(self, room: str, start: int, end: int) -> bool:
        for b in self.bookings:
            if b.room != room:
                continue
            if start < b.end and b.start < end:
                return True
        return False

    def book(self, room: str, start: int, end: int) -> Booking:
        if start >= end:
            raise ValueError("start must be before end")
        if self._overlaps(room, start, end):
            raise ValueError(f"{room} is already booked in that window")
        booking = Booking(room, start, end)
        self.bookings.append(booking)
        return booking
