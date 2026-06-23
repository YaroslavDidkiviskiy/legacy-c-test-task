#!/usr/bin/env python3
"""
main.py — thin driver (port of main.c).

Parses argv, opens DB, calls the right proc, maps result code → message,
prints to stdout, exits with the correct code.
"""

import sys
import os

from db import (
    db_open, db_close,
    REG_FAIL,
    RG_DONE, RG_WAITED, RG_NOTENR, RG_GRADED, RG_HOLD,
    RG_DROPCLOSE, RG_ADDCLOSE, RG_ALRENR, RG_NOPRE, RG_MAXCRD,
)
from proc import do_drop, do_add, do_swap

# ── default DB path (can be overridden via CARSDB env var) ──────────────────
DEFAULT_DB = os.path.join(os.path.dirname(__file__), "cars.db")

# Maps an outcome code to the operator-facing message.
# Keyed by name, not by raw number — matches dec.h's rg_message() switch
# verbatim, and stays correct even if a code's numeric value ever changes.
RG_MESSAGES = {
    RG_DONE:      "Done.",
    RG_WAITED:    "Section full -- student placed on the waitlist.",
    RG_NOTENR:    "Student is not enrolled in that section.",
    RG_GRADED:    "Cannot drop: a grade has already been posted.",
    RG_HOLD:      "Cannot proceed: student has a registration hold.",
    RG_DROPCLOSE: "Cannot drop: the drop deadline has passed.",
    RG_ADDCLOSE:  "Cannot add: registration for this term is closed.",
    RG_ALRENR:    "Student is already enrolled in that section.",
    RG_NOPRE:     "Cannot add: prerequisites are not satisfied.",
    RG_MAXCRD:    "Cannot add: would exceed the term credit limit.",
}

# Outcome codes that count as success (exit 0) and should be committed.
SUCCESS_CODES = (RG_DONE, RG_WAITED)


def rg_message(rc: int) -> str:
    """Maps an outcome code to its operator-facing message."""
    return RG_MESSAGES.get(rc, "A database error occurred. No changes were made.")


def usage(prog: str) -> None:
    sys.stderr.write(
        f"Usage:\n"
        f"  {prog} drop <id> <sec> <yr> <sess>\n"
        f"  {prog} add  <id> <sec> <yr> <sess>\n"
        f"  {prog} swap <id> <dropsec> <addsec> <yr> <sess>\n"
    )


def main() -> None:
    prog = sys.argv[0]
    argv = sys.argv

    db_path = os.environ.get("CARSDB", DEFAULT_DB)

    conn, open_rc = db_open(db_path)
    if open_rc == REG_FAIL:
        print("A database error occurred. No changes were made.")
        sys.exit(2)

    try:
        if len(argv) == 6 and argv[1] == "drop":
            student_id  = int(argv[2])
            section     = argv[3]
            year        = int(argv[4])
            session     = argv[5]
            result = do_drop(conn, student_id, section, year, session)

        elif len(argv) == 6 and argv[1] == "add":
            student_id  = int(argv[2])
            section     = argv[3]
            year        = int(argv[4])
            session     = argv[5]
            result = do_add(conn, student_id, section, year, session)

        elif len(argv) == 7 and argv[1] == "swap":
            student_id    = int(argv[2])
            drop_section  = argv[3]
            add_section   = argv[4]
            year          = int(argv[5])
            session       = argv[6]
            result = do_swap(conn, student_id, drop_section, add_section, year, session)

        else:
            usage(prog)
            db_close(conn, commit=False)
            sys.exit(2)

    except (ValueError, IndexError):
        usage(prog)
        db_close(conn, commit=False)
        sys.exit(2)

    # proc.py already committed on a success code; on failure (REG_FAIL or
    # any other non-success code) force a rollback so nothing partial sticks.
    should_commit = result in SUCCESS_CODES
    db_close(conn, commit=should_commit)

    print(rg_message(result))
    sys.exit(0 if result in SUCCESS_CODES else 1)


if __name__ == "__main__":
    main()
