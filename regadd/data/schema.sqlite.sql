-- schema.sqlite.sql -- SQLite projection of the CARS tables touched by the
-- regadd screen. This is what your Python port should run against.
--
-- The keys are simplified for the exercise: a registration is identified by
-- (id, sec, yr, sess) rather than the full CARS composite key.

PRAGMA foreign_keys = ON;

CREATE TABLE stu_rec (
    id        INTEGER PRIMARY KEY,
    name      TEXT,
    enrolled  TEXT NOT NULL DEFAULT 'Y'   -- 'Y' active, 'N' inactive
);

CREATE TABLE acad_cal_rec (
    yr          INTEGER NOT NULL,
    sess        TEXT NOT NULL,
    descr       TEXT,
    drop_open   TEXT NOT NULL DEFAULT 'Y',  -- 'Y' if drops still allowed
    add_open    TEXT NOT NULL DEFAULT 'Y',  -- 'Y' if adds still allowed
    max_credits INTEGER NOT NULL DEFAULT 18,
    PRIMARY KEY (yr, sess)
);

CREATE TABLE sec_rec (
    sec_no       TEXT NOT NULL,
    yr           INTEGER NOT NULL,
    sess         TEXT NOT NULL,
    crs_no       TEXT NOT NULL,
    seats_cap    INTEGER NOT NULL,
    seats_taken  INTEGER NOT NULL,
    credits      INTEGER NOT NULL DEFAULT 3,
    PRIMARY KEY (sec_no, yr, sess)
);

CREATE TABLE cw_rec (
    id     INTEGER NOT NULL,
    sec    TEXT NOT NULL,
    yr     INTEGER NOT NULL,
    sess   TEXT NOT NULL,
    grade  TEXT NOT NULL DEFAULT '  ',   -- '  ' in progress, 'W ' withdrawn, else posted
    PRIMARY KEY (id, sec, yr, sess)
);

CREATE TABLE rgwait_rec (
    id        INTEGER NOT NULL,
    sec       TEXT NOT NULL,
    yr        INTEGER NOT NULL,
    sess      TEXT NOT NULL,
    position  INTEGER NOT NULL,           -- 1 = first in line
    PRIMARY KEY (id, sec, yr, sess)
);

CREATE TABLE prereq_rec (
    crs_no      TEXT NOT NULL,   -- course you want to take
    req_crs_no  TEXT NOT NULL,   -- course you must have passed first
    PRIMARY KEY (crs_no, req_crs_no)
);

CREATE TABLE reg_hold_rec (
    id      INTEGER NOT NULL,
    reason  TEXT,
    active  TEXT NOT NULL DEFAULT 'Y'
);

CREATE TABLE drop_log_rec (
    id          INTEGER,
    sec         TEXT,
    yr          INTEGER,
    sess        TEXT,
    dropped_at  TEXT DEFAULT (datetime('now'))
);
