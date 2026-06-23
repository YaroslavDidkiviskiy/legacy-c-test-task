"""
test_scenarios.py — acceptance tests S1–S15 + edge cases.

Each test gets a fresh in-memory SQLite DB seeded from the canonical
schema.sqlite.sql + seed.sqlite.sql files.
"""

import sqlite3
import sys
import os
import pytest

# ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db import (
    db_open, db_close,
    REG_OK, REG_FAIL,
    RG_DONE, RG_NOTENR, RG_GRADED, RG_HOLD,
    RG_DROPCLOSE, RG_ADDCLOSE, RG_ALRENR, RG_NOPRE, RG_MAXCRD, RG_WAITED,
)
from proc import do_drop, do_add, do_swap

# ── locate SQL files relative to this test file ────────────────────────────
_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)
SCHEMA_PATH = os.path.join(_ROOT, "data", "schema.sqlite.sql")
SEED_PATH   = os.path.join(_ROOT, "data", "seed.sqlite.sql")


def _load_sql(path: str) -> str:
    with open(path) as f:
        return f.read()


@pytest.fixture
def conn():
    """
    Fresh in-memory SQLite with schema+seed applied.
    Transaction is begun; individual tests commit / rollback via the proc.
    """
    c = sqlite3.connect(":memory:", isolation_level=None)
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(_load_sql(SCHEMA_PATH))
    c.executescript(_load_sql(SEED_PATH))
    c.execute("BEGIN")
    yield c
    try:
        c.execute("ROLLBACK")
    except Exception:
        pass
    c.close()


# ─────────────────────────── DROP scenarios ──────────────────────────────────

def test_S1_drop_done(conn):
    """S1: Alice drops CS101-01 2024 S → Done."""
    assert do_drop(conn, 1001, "CS101-01", 2024, "S") == RG_DONE


def test_S2_drop_only_course_sets_inactive(conn):
    """S2: Bob drops his only course → Done + enrolled='N'."""
    rc = do_drop(conn, 1002, "CS101-02", 2024, "S")
    assert rc == RG_DONE
    row = conn.execute("SELECT enrolled FROM stu_rec WHERE id=1002").fetchone()
    assert row[0] == "N"


def test_S3_drop_hold(conn):
    """S3: Carol has active hold → RG_HOLD."""
    assert do_drop(conn, 1003, "CS101-01", 2024, "S") == RG_HOLD


def test_S4_drop_graded(conn):
    """S4: Dave has grade='A ' → RG_GRADED."""
    assert do_drop(conn, 1004, "CS101-01", 2024, "S") == RG_GRADED


def test_S5_drop_closed_term(conn):
    """S5: Drop window closed for Fall 2023 → RG_DROPCLOSE."""
    assert do_drop(conn, 1001, "HX999-01", 2023, "F") == RG_DROPCLOSE


def test_S6_drop_not_enrolled(conn):
    """S6: Gina not enrolled in CS101-02 → RG_NOTENR."""
    assert do_drop(conn, 1007, "CS101-02", 2024, "S") == RG_NOTENR


# ─────────────────────────── ADD scenarios ───────────────────────────────────

def test_S7_add_done(conn):
    """S7: Gina adds CS101-02 (room available) → Done."""
    assert do_add(conn, 1007, "CS101-02", 2024, "S") == RG_DONE


def test_S8_add_no_prereq_cs201(conn):
    """S8: Gina tries CS201 without passing CS101 → RG_NOPRE."""
    assert do_add(conn, 1007, "CS201-01", 2024, "S") == RG_NOPRE


def test_S9_add_no_prereq_phil300(conn):
    """S9: Gina tries PHIL300 without passing MA200 → RG_NOPRE."""
    assert do_add(conn, 1007, "PHIL300-1", 2024, "S") == RG_NOPRE


def test_S10_add_full_waitlist(conn):
    """S10: Hank adds PHIL300-1 (full, cap=1) → RG_WAITED."""
    assert do_add(conn, 1008, "PHIL300-1", 2024, "S") == RG_WAITED


def test_S11_add_already_enrolled(conn):
    """S11: Alice tries MA200-01 again → RG_ALRENR."""
    assert do_add(conn, 1001, "MA200-01", 2024, "S") == RG_ALRENR


def test_S12_add_closed_term(conn):
    """S12: Gina tries HX999-01 in closed Fall 2023 → RG_ADDCLOSE."""
    assert do_add(conn, 1007, "HX999-01", 2023, "F") == RG_ADDCLOSE


def test_S13_add_full_waitlist_cs101(conn):
    """S13: Gina adds CS101-01 (full, cap=2) → RG_WAITED."""
    assert do_add(conn, 1007, "CS101-01", 2024, "S") == RG_WAITED


# ─────────────────────────── SWAP scenarios ──────────────────────────────────

def test_S14_swap_done(conn):
    """S14 (A): Alice swaps CS101-01 → CS201-01 → Done."""
    assert do_swap(conn, 1001, "CS101-01", "CS201-01", 2024, "S") == RG_DONE


def test_S15_swap_atomic_rollback(conn):
    """
    S15 (A+): Alice tries to swap MA200-01 → CS999-01 (nonexistent section).
    add fails → entire swap rolls back → MA200-01 still enrolled.
    """
    rc = do_swap(conn, 1001, "MA200-01", "CS999-01", 2024, "S")
    assert rc == RG_NOTENR
    # MA200-01 must still be present (rollback happened)
    row = conn.execute(
        "SELECT 1 FROM cw_rec WHERE id=1001 AND sec='MA200-01' AND yr=2024 AND sess='S'"
    ).fetchone()
    assert row is not None, "MA200-01 should still exist after failed swap"


# ─────────────────────────── extra edge cases ────────────────────────────────

def test_drop_withdrawn_grade_allowed(conn):
    """Dave has grade='W ' on MA200-01 — should be droppable."""
    assert do_drop(conn, 1004, "MA200-01", 2024, "S") == RG_DONE


def test_drop_promotes_waitlist(conn):
    """
    Alice drops CS101-01 (full, cap=2, taken=2, waitlist: Erin pos1, Frank pos2).
    Erin should be promoted from waitlist to cw_rec.
    """
    rc = do_drop(conn, 1001, "CS101-01", 2024, "S")
    assert rc == RG_DONE
    # Erin (1005) promoted
    row = conn.execute(
        "SELECT 1 FROM cw_rec WHERE id=1005 AND sec='CS101-01' AND yr=2024 AND sess='S'"
    ).fetchone()
    assert row is not None, "Erin should have been promoted from waitlist"
    # seats_taken stays at 2 (dec then inc cancel out)
    row = conn.execute(
        "SELECT seats_taken FROM sec_rec WHERE sec_no='CS101-01' AND yr=2024 AND sess='S'"
    ).fetchone()
    assert row[0] == 2


def test_add_credit_limit(conn):
    """
    Hank has 3+3+4=10 credits. max=18. Adding PHIL300 (3cr) → 13 ≤ 18 → ok.
    But if we artificially lower max to 12 to force RG_MAXCRD.
    """
    conn.execute(
        "UPDATE acad_cal_rec SET max_credits=12 WHERE yr=2024 AND sess='S'"
    )
    # Hank (10 cr) + PHIL300 (3 cr) = 13 > 12 → RG_MAXCRD
    assert do_add(conn, 1008, "PHIL300-1", 2024, "S") == RG_MAXCRD


def test_inactive_hold_ignored(conn):
    """Alice has an INACTIVE hold — must not block drop."""
    # Verify the inactive hold exists
    row = conn.execute(
        "SELECT active FROM reg_hold_rec WHERE id=1001"
    ).fetchone()
    assert row[0] == "N"
    # Drop should succeed
    assert do_drop(conn, 1001, "CS101-01", 2024, "S") == RG_DONE


def test_add_nonexistent_section(conn):
    """Adding to a section that doesn't exist → RG_NOTENR."""
    assert do_add(conn, 1007, "FAKE-99", 2024, "S") == RG_NOTENR


def test_drop_log_written(conn):
    """After a successful drop, drop_log_rec must have a row."""
    do_drop(conn, 1001, "CS101-01", 2024, "S")
    row = conn.execute(
        "SELECT 1 FROM drop_log_rec WHERE id=1001 AND sec='CS101-01'"
    ).fetchone()
    assert row is not None


def test_waitlist_position_increments(conn):
    """Adding two students to a full section gives positions 3 and 4."""
    # CS101-01 waitlist already has pos 1 (Erin) and 2 (Frank)
    # Gina → position 3
    rc1 = do_add(conn, 1007, "CS101-01", 2024, "S")
    assert rc1 == RG_WAITED
    row1 = conn.execute(
        "SELECT position FROM rgwait_rec WHERE id=1007 AND sec='CS101-01'"
    ).fetchone()
    assert row1[0] == 3

    # Dave (1004) → position 4 (he's not enrolled in CS101-01 current term w/ active grade,
    # but he IS enrolled — the enrolled row is grade='A ', so add would hit ALRENR)
    # Use a different student without conflict: student 1002 (Bob) — not in CS101-01
    rc2 = do_add(conn, 1002, "CS101-01", 2024, "S")
    assert rc2 == RG_WAITED
    row2 = conn.execute(
        "SELECT position FROM rgwait_rec WHERE id=1002 AND sec='CS101-01'"
    ).fetchone()
    assert row2[0] == 4
