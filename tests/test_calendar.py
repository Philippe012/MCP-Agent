import pytest

from scheduler.calendar import Calendar


def test_non_overlapping_bookings_are_both_accepted():
    cal = Calendar()
    cal.book("R1", 540, 600)  
    cal.book("R1", 660, 720)  
    assert len(cal.bookings) == 2


def test_genuinely_overlapping_booking_is_rejected():
    cal = Calendar()
    cal.book("R1", 540, 600) 
    with pytest.raises(ValueError):
        cal.book("R1", 570, 630)


def test_different_rooms_never_conflict():
    cal = Calendar()
    cal.book("R1", 540, 600)
    cal.book("R2", 540, 600)
    assert len(cal.bookings) == 2


def test_start_must_be_before_end():
    cal = Calendar()
    with pytest.raises(ValueError):
        cal.book("R1", 600, 600)
