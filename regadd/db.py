"""
db.py — DAO layer (port of db.ec).

One SQL query per function, zero business logic.
Return conventions mirror the original C:
  REG_OK   (0)  — success
  REG_FAIL (-1) — DB error
  RG_NOTENR(-1) — row not found (find_enr / sect_crs)
  TRUE (1) / FALSE (0) — boolean queries (has_hold, drop_open, add_open,
                          passed_crs, prereq_met)
  integer  — count / value queries (count_enr, get_seats, term_credits, …)
"""

import sqlite3

# ── internal constants (mirror dec.h) ──────────────────────────────────────
REG_OK   =  0
REG_FAIL = -1
REG_WARN =  1

TRUE  = 1
FALSE = 0

# ── operation-outcome codes (mirror dec.h) ──────────────────────────────────
RG_DONE      =  0
RG_NOTENR    = -1
RG_GRADED    = -2
RG_HOLD      = -3
RG_DROPCLOSE = -4
RG_ADDCLOSE  = -5
RG_ALRENR    = -6
RG_NOPRE     = -7
RG_MAXCRD    = -8
RG_WAITED    =  2

CW_INPROG = "  "
CW_WDRAW  = "W "


# ── connection management ────────────────────────────────────────────────────

def db_open(path: str) -> tuple[sqlite3.Connection | None, int]:
    """
    Open the SQLite database and begin a transaction (mirrors $BEGIN WORK).
    Returns (conn, REG_OK) on success, (None, REG_FAIL) on error.
    isolation_level=None → autocommit off; we manage transactions manually.
    """
    try:
        conn = sqlite3.connect(path, isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN")
        return conn, REG_OK
    except sqlite3.Error:
        return None, REG_FAIL


def db_close(conn: sqlite3.Connection, commit: bool) -> None:
    """
    Commit or rollback and close (mirrors db_close() with trial_run flag).
    """
    try:
        if commit:
            conn.execute("COMMIT")
        else:
            conn.execute("ROLLBACK")
    except sqlite3.Error:
        pass
    finally:
        conn.close()


# ── DAO functions ─────────────────────────────────────────────────────────────

def find_enr(conn: sqlite3.Connection,
             id: int, sec: str, yr: int, sess: str) -> tuple[int, str]:
    """
    SELECT grade FROM cw_rec WHERE id=? AND sec=? AND yr=? AND sess=?
    Returns (REG_OK, grade) | (RG_NOTENR, '') | (REG_FAIL, '')
    """
    try:
        row = conn.execute(
            "SELECT grade FROM cw_rec "
            "WHERE id=? AND sec=? AND yr=? AND sess=?",
            (id, sec, yr, sess)
        ).fetchone()
        if row is None:
            return RG_NOTENR, ""
        return REG_OK, row[0]
    except sqlite3.Error:
        return REG_FAIL, ""


def count_enr(conn: sqlite3.Connection,
              id: int, yr: int, sess: str) -> int:
    """
    SELECT count(*) FROM cw_rec WHERE id=? AND yr=? AND sess=?
    Returns count (>=0) or REG_FAIL.
    """
    try:
        row = conn.execute(
            "SELECT count(*) FROM cw_rec WHERE id=? AND yr=? AND sess=?",
            (id, yr, sess)
        ).fetchone()
        return row[0]
    except sqlite3.Error:
        return REG_FAIL


def get_seats(conn: sqlite3.Connection,
              sec: str, yr: int, sess: str) -> tuple[int, int, int]:
    """
    SELECT seats_taken, seats_cap FROM sec_rec WHERE sec_no=? AND yr=? AND sess=?
    Returns (REG_OK, taken, cap) | (REG_FAIL, 0, 0)
    """
    try:
        row = conn.execute(
            "SELECT seats_taken, seats_cap FROM sec_rec "
            "WHERE sec_no=? AND yr=? AND sess=?",
            (sec, yr, sess)
        ).fetchone()
        if row is None:
            return REG_FAIL, 0, 0
        return REG_OK, row[0], row[1]
    except sqlite3.Error:
        return REG_FAIL, 0, 0


def has_hold(conn: sqlite3.Connection, id: int) -> int:
    """
    SELECT count(*) FROM reg_hold_rec WHERE id=? AND active='Y'
    Returns TRUE/FALSE or REG_FAIL.
    """
    try:
        row = conn.execute(
            "SELECT count(*) FROM reg_hold_rec WHERE id=? AND active='Y'",
            (id,)
        ).fetchone()
        return TRUE if row[0] > 0 else FALSE
    except sqlite3.Error:
        return REG_FAIL


def drop_open(conn: sqlite3.Connection, yr: int, sess: str) -> int:
    """
    SELECT drop_open FROM acad_cal_rec WHERE yr=? AND sess=?
    Returns TRUE/FALSE (SQLNOTFOUND → FALSE).
    """
    try:
        row = conn.execute(
            "SELECT drop_open FROM acad_cal_rec WHERE yr=? AND sess=?",
            (yr, sess)
        ).fetchone()
        if row is None:
            return FALSE
        return TRUE if row[0] == "Y" else FALSE
    except sqlite3.Error:
        return REG_FAIL


def add_open(conn: sqlite3.Connection, yr: int, sess: str) -> int:
    """
    SELECT add_open FROM acad_cal_rec WHERE yr=? AND sess=?
    Returns TRUE/FALSE (SQLNOTFOUND → FALSE).
    """
    try:
        row = conn.execute(
            "SELECT add_open FROM acad_cal_rec WHERE yr=? AND sess=?",
            (yr, sess)
        ).fetchone()
        if row is None:
            return FALSE
        return TRUE if row[0] == "Y" else FALSE
    except sqlite3.Error:
        return REG_FAIL


def del_enr(conn: sqlite3.Connection,
            id: int, sec: str, yr: int, sess: str) -> int:
    """
    DELETE FROM cw_rec WHERE id=? AND sec=? AND yr=? AND sess=?
    Returns REG_OK | REG_FAIL.
    """
    try:
        conn.execute(
            "DELETE FROM cw_rec WHERE id=? AND sec=? AND yr=? AND sess=?",
            (id, sec, yr, sess)
        )
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL


def del_wait(conn: sqlite3.Connection,
             id: int, sec: str, yr: int, sess: str) -> int:
    """
    DELETE FROM rgwait_rec WHERE id=? AND sec=? AND yr=? AND sess=?
    Returns REG_OK | REG_FAIL.
    """
    try:
        conn.execute(
            "DELETE FROM rgwait_rec WHERE id=? AND sec=? AND yr=? AND sess=?",
            (id, sec, yr, sess)
        )
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL


def dec_taken(conn: sqlite3.Connection,
              sec: str, yr: int, sess: str) -> int:
    """
    UPDATE sec_rec SET seats_taken = seats_taken - 1 WHERE sec_no=? …
    Returns REG_OK | REG_FAIL.
    """
    try:
        conn.execute(
            "UPDATE sec_rec SET seats_taken = seats_taken - 1 "
            "WHERE sec_no=? AND yr=? AND sess=?",
            (sec, yr, sess)
        )
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL


def promote_wait(conn: sqlite3.Connection,
                 sec: str, yr: int, sess: str) -> int:
    """
    Fetches the first waitlisted student (ORDER BY position), removes them
    from rgwait_rec, inserts into cw_rec, increments seats_taken.
    Returns promoted student id (>0), 0 if waitlist empty, REG_FAIL on error.
    """
    try:
        row = conn.execute(
            "SELECT id, position FROM rgwait_rec "
            "WHERE sec=? AND yr=? AND sess=? ORDER BY position LIMIT 1",
            (sec, yr, sess)
        ).fetchone()
        if row is None:
            return 0

        promoted_id = row[0]

        conn.execute(
            "DELETE FROM rgwait_rec WHERE id=? AND sec=? AND yr=? AND sess=?",
            (promoted_id, sec, yr, sess)
        )
        conn.execute(
            "INSERT INTO cw_rec (id, sec, yr, sess, grade) VALUES (?,?,?,?,?)",
            (promoted_id, sec, yr, sess, CW_INPROG)
        )
        conn.execute(
            "UPDATE sec_rec SET seats_taken = seats_taken + 1 "
            "WHERE sec_no=? AND yr=? AND sess=?",
            (sec, yr, sess)
        )
        return promoted_id
    except sqlite3.Error:
        return REG_FAIL


def set_inactive(conn: sqlite3.Connection, id: int) -> int:
    """UPDATE stu_rec SET enrolled='N' WHERE id=?"""
    try:
        conn.execute("UPDATE stu_rec SET enrolled='N' WHERE id=?", (id,))
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL


def set_active(conn: sqlite3.Connection, id: int) -> int:
    """UPDATE stu_rec SET enrolled='Y' WHERE id=?"""
    try:
        conn.execute("UPDATE stu_rec SET enrolled='Y' WHERE id=?", (id,))
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL


def log_drop(conn: sqlite3.Connection,
             id: int, sec: str, yr: int, sess: str) -> int:
    """INSERT INTO drop_log_rec (id, sec, yr, sess) VALUES (?,?,?,?)"""
    try:
        conn.execute(
            "INSERT INTO drop_log_rec (id, sec, yr, sess) VALUES (?,?,?,?)",
            (id, sec, yr, sess)
        )
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL


def sect_crs(conn: sqlite3.Connection,
             sec: str, yr: int, sess: str) -> tuple[int, str]:
    """
    SELECT crs_no FROM sec_rec WHERE sec_no=? AND yr=? AND sess=?
    Returns (REG_OK, crs_no) | (RG_NOTENR, '') | (REG_FAIL, '')
    Note: original returns RG_NOTENR on SQLNOTFOUND — section doesn't exist.
    """
    try:
        row = conn.execute(
            "SELECT crs_no FROM sec_rec WHERE sec_no=? AND yr=? AND sess=?",
            (sec, yr, sess)
        ).fetchone()
        if row is None:
            return RG_NOTENR, ""
        return REG_OK, row[0]
    except sqlite3.Error:
        return REG_FAIL, ""


def sect_credits(conn: sqlite3.Connection,
                 sec: str, yr: int, sess: str) -> int:
    """
    SELECT credits FROM sec_rec WHERE sec_no=? AND yr=? AND sess=?
    Returns credits (int) or REG_FAIL.
    """
    try:
        row = conn.execute(
            "SELECT credits FROM sec_rec WHERE sec_no=? AND yr=? AND sess=?",
            (sec, yr, sess)
        ).fetchone()
        if row is None:
            return REG_FAIL
        return row[0]
    except sqlite3.Error:
        return REG_FAIL


def max_credits(conn: sqlite3.Connection, yr: int, sess: str) -> int:
    """
    SELECT max_credits FROM acad_cal_rec WHERE yr=? AND sess=?
    Returns max_credits (int) or REG_FAIL.
    """
    try:
        row = conn.execute(
            "SELECT max_credits FROM acad_cal_rec WHERE yr=? AND sess=?",
            (yr, sess)
        ).fetchone()
        if row is None:
            return REG_FAIL
        return row[0]
    except sqlite3.Error:
        return REG_FAIL


def term_credits(conn: sqlite3.Connection,
                 id: int, yr: int, sess: str) -> int:
    """
    SELECT sum(sec_rec.credits) FROM cw_rec JOIN sec_rec … WHERE id=? yr=? sess=?
    Returns total credits (int, 0 if none) or REG_FAIL.
    """
    try:
        row = conn.execute(
            "SELECT COALESCE(sum(s.credits), 0) "
            "FROM cw_rec c JOIN sec_rec s "
            "  ON s.sec_no=c.sec AND s.yr=c.yr AND s.sess=c.sess "
            "WHERE c.id=? AND c.yr=? AND c.sess=?",
            (id, yr, sess)
        ).fetchone()
        if row is None:
            return 0
        return row[0]
    except sqlite3.Error:
        return REG_FAIL


def passed_crs(conn: sqlite3.Connection, id: int, crs: str) -> int:
    """
    SELECT count(*) … WHERE cw_rec.id=? AND sec_rec.crs_no=?
        AND grade != '  ' AND grade != 'W '
    Returns TRUE/FALSE or REG_FAIL.
    """
    try:
        row = conn.execute(
            "SELECT count(*) FROM cw_rec c JOIN sec_rec s "
            "  ON s.sec_no=c.sec AND s.yr=c.yr AND s.sess=c.sess "
            "WHERE c.id=? AND s.crs_no=? "
            "  AND c.grade != '  ' AND c.grade != 'W '",
            (id, crs)
        ).fetchone()
        return TRUE if row[0] > 0 else FALSE
    except sqlite3.Error:
        return REG_FAIL


def prereq_met(conn: sqlite3.Connection, id: int, crs: str) -> int:
    """
    Iterates prereq_rec for crs; each required course must be passed_crs.
    Returns TRUE (no prereqs or all passed), FALSE (any missing), REG_FAIL on error.
    """
    try:
        rows = conn.execute(
            "SELECT req_crs_no FROM prereq_rec WHERE crs_no=?",
            (crs,)
        ).fetchall()
    except sqlite3.Error:
        return REG_FAIL

    for (req,) in rows:
        rc = passed_crs(conn, id, req)
        if rc == REG_FAIL:
            return REG_FAIL
        if rc == FALSE:
            return FALSE

    return TRUE


def next_wait_pos(conn: sqlite3.Connection,
                  sec: str, yr: int, sess: str) -> int:
    """
    SELECT max(position) FROM rgwait_rec WHERE sec=? AND yr=? AND sess=?
    Returns max+1 (or 1 if empty) or REG_FAIL.
    """
    try:
        row = conn.execute(
            "SELECT max(position) FROM rgwait_rec "
            "WHERE sec=? AND yr=? AND sess=?",
            (sec, yr, sess)
        ).fetchone()
        if row is None or row[0] is None:
            return 1
        return row[0] + 1
    except sqlite3.Error:
        return REG_FAIL


def ins_wait(conn: sqlite3.Connection,
             id: int, sec: str, yr: int, sess: str, pos: int) -> int:
    """
    INSERT INTO rgwait_rec (id, sec, yr, sess, position) VALUES (?,?,?,?,?)
    Returns REG_OK | REG_FAIL.
    """
    try:
        conn.execute(
            "INSERT INTO rgwait_rec (id, sec, yr, sess, position) "
            "VALUES (?,?,?,?,?)",
            (id, sec, yr, sess, pos)
        )
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL


def ins_enr(conn: sqlite3.Connection,
            id: int, sec: str, yr: int, sess: str) -> int:
    """
    INSERT INTO cw_rec (id, sec, yr, sess, grade) VALUES (?,?,?,?,'  ')
    Returns REG_OK | REG_FAIL.
    """
    try:
        conn.execute(
            "INSERT INTO cw_rec (id, sec, yr, sess, grade) VALUES (?,?,?,?,?)",
            (id, sec, yr, sess, CW_INPROG)
        )
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL


def inc_taken(conn: sqlite3.Connection,
              sec: str, yr: int, sess: str) -> int:
    """
    UPDATE sec_rec SET seats_taken = seats_taken + 1 WHERE sec_no=? …
    Returns REG_OK | REG_FAIL.
    """
    try:
        conn.execute(
            "UPDATE sec_rec SET seats_taken = seats_taken + 1 "
            "WHERE sec_no=? AND yr=? AND sess=?",
            (sec, yr, sess)
        )
        return REG_OK
    except sqlite3.Error:
        return REG_FAIL
