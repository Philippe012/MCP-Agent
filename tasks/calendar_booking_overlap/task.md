# Task: back-to-back room bookings are wrongly rejected

You're working in a small room-booking library. A user reports that
booking a room from 10:00-11:00 fails with "already booked" when there's
an existing booking from 9:00-10:00 for the same room - even though those
two bookings don't actually overlap, they just meet at 10:00.

## Requirements

1. Two bookings for the same room that only touch at a boundary (one ends
   exactly when the other starts) must both be allowed.
2. Bookings that genuinely overlap (share any interior minute) must still
   be rejected, exactly as before.
3. Bookings for different rooms must never conflict with each other,
   regardless of time.
4. A booking where `start >= end` must still raise `ValueError`.
5. Add a regression test proving that two back-to-back bookings (one
   ending exactly when the other starts) are both accepted.
6. Do not change the public `Booking` API.

## Constraints

- Use only the repository and the tools exposed through MCP.
- Run the full test suite before declaring success.
