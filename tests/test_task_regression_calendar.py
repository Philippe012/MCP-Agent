from scheduler.calendar import Calendar


def test_back_to_back_bookings_are_both_accepted():
    cal = Calendar()
    cal.book("R1", 540, 600)
    cal.book("R1", 600, 660)
    assert len(cal.bookings) == 2
