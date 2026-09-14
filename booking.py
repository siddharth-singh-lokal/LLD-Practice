"""
Seat booking + lock — Strong Hire reference (60-90 min MC round).

DERIVE STRUCTURE (5-8 min):
  Seat, Venue, BookingService. user_id string. Two statuses: AVAILABLE, BOOKED.

LOCK (say out loud when you add it):
  "One lock per seat — A1 and A2 don't block each other.
   book_many locks seats in sorted order so two multi-book calls don't deadlock."

HIRE vs STRONG HIRE:
  Hire     = book / cancel / show + basic driver
  Strong   = edge driver + book_many + thread race demo
"""

from __future__ import annotations

import concurrent.futures
import threading
from enum import Enum


class SeatStatus(Enum):
    AVAILABLE = "available"
    BOOKED = "booked"


class Seat:
    def __init__(
        self,
        seat_id: str,
        status: SeatStatus = SeatStatus.AVAILABLE,
        booked_by: str | None = None,
    ):
        self.seat_id = seat_id
        self.status = status
        self.booked_by = booked_by


class Venue:
    def __init__(self):
        self._seats: dict[str, Seat] = {}

    def add_seat(self, seat_id: str) -> None:
        if seat_id not in self._seats:
            self._seats[seat_id] = Seat(seat_id)

    def get_seat(self, seat_id: str) -> Seat | None:
        if not seat_id:
            return None
        return self._seats.get(seat_id)

    def get_all_available_seats(self) -> list[str]:
        return [
            seat_id
            for seat_id, seat in self._seats.items()
            if seat.status == SeatStatus.AVAILABLE
        ]


class BookingService:
    def __init__(self, venue: Venue):
        self.venue = venue
        self._seat_locks: dict[str, threading.Lock] = {}

    def _seat_lock(self, seat_id: str) -> threading.Lock:
        if seat_id not in self._seat_locks:
            self._seat_locks[seat_id] = threading.Lock()
        return self._seat_locks[seat_id]

    def book(self, seat_id: str, user_id: str) -> bool:
        if not seat_id:
            return False

        seat = self.venue.get_seat(seat_id)
        if not seat:
            return False

        with self._seat_lock(seat_id):
            if seat.status == SeatStatus.BOOKED:
                return False
            seat.status = SeatStatus.BOOKED
            seat.booked_by = user_id
            return True

    def cancel(self, seat_id: str, user_id: str) -> bool:
        if not seat_id:
            return False

        seat = self.venue.get_seat(seat_id)
        if not seat:
            return False

        with self._seat_lock(seat_id):
            if seat.status == SeatStatus.AVAILABLE:
                return False
            if seat.booked_by != user_id:
                return False
            seat.status = SeatStatus.AVAILABLE
            seat.booked_by = None
            return True

    def show_available(self) -> list[str]:
        return self.venue.get_all_available_seats()

    def book_many(self, seat_ids: list[str], user_id: str) -> bool:
        """
        SH extension (~minute 50). Lock every seat in sorted order first
        so two threads booking overlapping sets don't deadlock.
        """
        ordered_ids = sorted(set(seat_ids))
        locks = [self._seat_lock(seat_id) for seat_id in ordered_ids]

        for lock in locks:
            lock.acquire()
        try:
            seats: list[Seat] = []
            for seat_id in ordered_ids:
                seat = self.venue.get_seat(seat_id)
                if not seat or seat.status == SeatStatus.BOOKED:
                    return False
                seats.append(seat)

            for seat in seats:
                seat.status = SeatStatus.BOOKED
                seat.booked_by = user_id
            return True
        finally:
            for lock in reversed(locks):
                lock.release()


def _run_concurrency_race_test() -> None:
    venue = Venue()
    venue.add_seat("R1")
    svc = BookingService(venue)

    successes = 0
    counter_lock = threading.Lock()

    def try_book(_: int) -> None:
        nonlocal successes
        if svc.book("R1", "u_race"):
            with counter_lock:
                successes += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(try_book, range(20)))

    assert successes == 1


if __name__ == "__main__":
    venue = Venue()
    for seat_id in ["A1", "A2", "A3"]:
        venue.add_seat(seat_id)

    svc = BookingService(venue)

    assert svc.book("A1", "u1") is True
    assert set(svc.show_available()) == {"A2", "A3"}

    assert svc.book("A1", "u2") is False

    assert svc.cancel("A1", "u2") is False
    assert svc.cancel("A1", "u1") is True
    assert svc.book("A1", "u2") is True

    assert svc.book("A9", "u1") is False
    assert svc.cancel("A9", "u1") is False
    assert svc.cancel("A2", "u1") is False

    assert svc.book_many(["A2", "A3"], "u3") is True
    assert svc.show_available() == []
    assert svc.book_many(["A1"], "u4") is False
    assert svc.cancel("A2", "u3") is True
    assert svc.book_many(["A2", "A3"], "u5") is False

    _run_concurrency_race_test()

    print("all checks passed")

"""
90-MIN REALISTIC PATH (one class, no subclass):
  0-8 min    Seat + Venue + book() single-threaded
  8-25 min   cancel(), show_available(), basic driver
  25-40 min  _seat_lock dict + wrap book/cancel — explain per-seat vs one big lock
  40-55 min  full driver (cancel, bad seat, rebook)
  55-70 min  book_many with sorted lock order if they ask
  70-90 min  thread race demo + walkthrough

OPENING:
  "In-memory seats. book, cancel, list available. Lock per seat so
   different seats don't block. book_many locks sorted seat ids to avoid deadlock."
"""
