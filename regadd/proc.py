"""
proc.py — business-logic layer (port of proc.ec).

do_drop / do_add / do_swap.
Check order is critical and mirrors the original C exactly.
No SQL here — all data access goes through db.py.

Structure:
  _do_drop_no_commit / _do_add_no_commit — the actual business logic,
      called with rules in the EXACT original order. They never touch
      the transaction boundary themselves.
  do_drop / do_add   — thin public wrappers: run the no-commit version,
      then commit/begin-anew on a terminal outcome (mirrors the two
      early-commit points in the original $COMMIT WORK calls).
  do_swap            — wraps both no-commit phases in one SAVEPOINT for
      true atomicity (A+), committing only once, at the very end.

This way the rule order lives in exactly one place per operation.
"""

import sqlite3
from db import (
    REG_OK, REG_FAIL, TRUE, FALSE,
    RG_DONE, RG_NOTENR, RG_GRADED, RG_HOLD,
    RG_DROPCLOSE, RG_ADDCLOSE, RG_ALRENR, RG_NOPRE, RG_MAXCRD, RG_WAITED,
    CW_INPROG, CW_WDRAW,
    has_hold, drop_open, add_open,
    find_enr, count_enr, get_seats,
    del_enr, del_wait, dec_taken, promote_wait,
    set_inactive, set_active, log_drop,
    sect_crs, prereq_met,
    term_credits, sect_credits, max_credits,
    ins_enr, inc_taken, next_wait_pos, ins_wait,
)


def _commit_and_reopen(conn: sqlite3.Connection) -> None:
    """Flush the current transaction and immediately start a new one,
    so the connection stays usable for whatever the caller does next."""
    conn.execute("COMMIT")
    conn.execute("BEGIN")


# ── no-commit core logic (single source of truth for rule order) ───────────

def _do_drop_no_commit(conn: sqlite3.Connection,
                        id: int, sec: str, yr: int, sess: str) -> int:
    """
    Drop a student from a section — business rules only, no transaction
    control. Check order (mirrors proc.ec exactly):
      1. hold
      2. drop window open
      3. enrolled? (find_enr)
      4. grade droppable? (in-progress or withdrawn)
      5. count active enrollments BEFORE delete
      6. delete enrollment
      7. delete waitlist row (no-op if not on waitlist)
      8. decrement seats_taken
      9. re-read seats; if room → promote_wait
     10. if this was the last active enrollment → set_inactive
     11. log_drop
    """
    rc = has_hold(conn, id)
    if rc == TRUE:
        return RG_HOLD
    if rc == REG_FAIL:
        return REG_FAIL

    rc = drop_open(conn, yr, sess)
    if rc == FALSE:
        return RG_DROPCLOSE
    if rc == REG_FAIL:
        return REG_FAIL

    rc, grade = find_enr(conn, id, sec, yr, sess)
    if rc != REG_OK:
        return rc  # RG_NOTENR or REG_FAIL

    if grade != CW_INPROG and grade != CW_WDRAW:
        return RG_GRADED

    active = count_enr(conn, id, yr, sess)
    if active == REG_FAIL:
        return REG_FAIL

    if del_enr(conn, id, sec, yr, sess) != REG_OK:
        return REG_FAIL
    if del_wait(conn, id, sec, yr, sess) != REG_OK:
        return REG_FAIL
    if dec_taken(conn, sec, yr, sess) != REG_OK:
        return REG_FAIL

    rc_seats, taken, cap = get_seats(conn, sec, yr, sess)
    if rc_seats != REG_OK:
        return REG_FAIL

    if taken < cap:
        promoted = promote_wait(conn, sec, yr, sess)
        if promoted == REG_FAIL:
            return REG_FAIL

    if active == 1:
        if set_inactive(conn, id) != REG_OK:
            return REG_FAIL

    if log_drop(conn, id, sec, yr, sess) != REG_OK:
        return REG_FAIL

    return RG_DONE


def _do_add_no_commit(conn: sqlite3.Connection,
                       id: int, sec: str, yr: int, sess: str) -> int:
    """
    Add a student to a section — business rules only, no transaction
    control. Check order (mirrors proc.ec exactly):
      1. hold
      2. add window open
      3. section exists? (sect_crs)
      4. already enrolled? (find_enr)
      5. prerequisites met?
      6. credit limit?
      7. seats: if full → waitlist, return RG_WAITED (caller commits)
      8. otherwise enroll: insert, inc_taken, set_active, return RG_DONE
    """
    rc = has_hold(conn, id)
    if rc == TRUE:
        return RG_HOLD
    if rc == REG_FAIL:
        return REG_FAIL

    rc = add_open(conn, yr, sess)
    if rc == FALSE:
        return RG_ADDCLOSE
    if rc == REG_FAIL:
        return REG_FAIL

    rc, crs = sect_crs(conn, sec, yr, sess)
    if rc != REG_OK:
        return rc  # RG_NOTENR or REG_FAIL

    rc_enr, _ = find_enr(conn, id, sec, yr, sess)
    if rc_enr == REG_OK:
        return RG_ALRENR

    rc = prereq_met(conn, id, crs)
    if rc == REG_FAIL:
        return REG_FAIL
    if rc != TRUE:
        return RG_NOPRE

    cur_cr = term_credits(conn, id, yr, sess)
    sec_cr = sect_credits(conn, sec, yr, sess)
    max_cr = max_credits(conn, yr, sess)
    if cur_cr == REG_FAIL or sec_cr == REG_FAIL or max_cr == REG_FAIL:
        return REG_FAIL
    if cur_cr + sec_cr > max_cr:
        return RG_MAXCRD

    rc_seats, taken, cap = get_seats(conn, sec, yr, sess)
    if rc_seats != REG_OK:
        return REG_FAIL

    if taken >= cap:
        pos = next_wait_pos(conn, sec, yr, sess)
        if pos == REG_FAIL:
            return REG_FAIL
        if ins_wait(conn, id, sec, yr, sess, pos) != REG_OK:
            return REG_FAIL
        return RG_WAITED

    if ins_enr(conn, id, sec, yr, sess) != REG_OK:
        return REG_FAIL
    if inc_taken(conn, sec, yr, sess) != REG_OK:
        return REG_FAIL
    set_active(conn, id)  # errors ignored in original (no check on return)

    return RG_DONE


# ── public, commit-owning wrappers ──────────────────────────────────────────

def do_drop(conn: sqlite3.Connection,
            id: int, sec: str, yr: int, sess: str) -> int:
    """Public drop entrypoint: run the rules, commit on any terminal
    outcome (mirrors the original $COMMIT WORK at the end of do_drop)."""
    rc = _do_drop_no_commit(conn, id, sec, yr, sess)
    if rc == RG_DONE:
        _commit_and_reopen(conn)
    return rc


def do_add(conn: sqlite3.Connection,
           id: int, sec: str, yr: int, sess: str) -> int:
    """Public add entrypoint: run the rules, commit on either terminal
    success outcome — RG_DONE or RG_WAITED — mirroring the two original
    $COMMIT WORK call sites (waitlist branch and normal-enroll branch)."""
    rc = _do_add_no_commit(conn, id, sec, yr, sess)
    if rc in (RG_DONE, RG_WAITED):
        _commit_and_reopen(conn)
    return rc


def do_swap(conn: sqlite3.Connection,
            id: int, dropsec: str, addsec: str, yr: int, sess: str) -> int:
    """
    Atomic swap (A+): drop + add as a single unit.
    Reuses the same no-commit core as do_drop/do_add, but wraps both
    phases in a SAVEPOINT so neither phase's success is visible until
    the whole swap succeeds. On any failure in either phase, the
    savepoint is rolled back and nothing from the swap persists.
    """
    conn.execute("SAVEPOINT swap_point")

    rc = _do_drop_no_commit(conn, id, dropsec, yr, sess)
    if rc != RG_DONE:
        conn.execute("ROLLBACK TO swap_point")
        conn.execute("RELEASE swap_point")
        return rc

    rc = _do_add_no_commit(conn, id, addsec, yr, sess)
    if rc not in (RG_DONE, RG_WAITED):
        conn.execute("ROLLBACK TO swap_point")
        conn.execute("RELEASE swap_point")
        return rc

    # Both phases succeeded — release the savepoint and commit the outer txn.
    conn.execute("RELEASE swap_point")
    _commit_and_reopen(conn)
    return rc