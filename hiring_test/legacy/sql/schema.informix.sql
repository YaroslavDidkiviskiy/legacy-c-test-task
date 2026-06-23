-- schema.informix.sql -- CARS tables touched by the regadd screen.
-- Informix dialect. Provided for reference; you do NOT need a running Informix.
-- Keys are simplified to (id, sec, yr, sess) for this exercise.

CREATE TABLE stu_rec (
    id        INTEGER NOT NULL,
    name      CHAR(40),
    enrolled  CHAR(1) DEFAULT 'Y',   -- 'Y' active, 'N' inactive
    PRIMARY KEY (id)
);

CREATE TABLE acad_cal_rec (
    yr           INTEGER NOT NULL,
    sess         CHAR(1) NOT NULL,
    descr        CHAR(20),
    drop_open    CHAR(1) DEFAULT 'Y',  -- 'Y' if drops are still allowed
    add_open     CHAR(1) DEFAULT 'Y',  -- 'Y' if adds are still allowed
    max_credits  INTEGER DEFAULT 18,
    PRIMARY KEY (yr, sess)
);

CREATE TABLE sec_rec (
    sec_no       CHAR(11) NOT NULL,
    yr           INTEGER  NOT NULL,
    sess         CHAR(1)  NOT NULL,
    crs_no       CHAR(8),
    seats_cap    INTEGER,
    seats_taken  INTEGER,
    credits      INTEGER DEFAULT 3,
    PRIMARY KEY (sec_no, yr, sess)
);

CREATE TABLE cw_rec (
    id     INTEGER  NOT NULL,
    sec    CHAR(11) NOT NULL,
    yr     INTEGER  NOT NULL,
    sess   CHAR(1)  NOT NULL,
    grade  CHAR(2) DEFAULT '  ',   -- '  ' in progress, 'W ' withdrawn, else posted
    PRIMARY KEY (id, sec, yr, sess)
);

CREATE TABLE rgwait_rec (
    id        INTEGER  NOT NULL,
    sec       CHAR(11) NOT NULL,
    yr        INTEGER  NOT NULL,
    sess      CHAR(1)  NOT NULL,
    position  INTEGER  NOT NULL,     -- 1 = first in line
    PRIMARY KEY (id, sec, yr, sess)
);

CREATE TABLE prereq_rec (
    crs_no      CHAR(8) NOT NULL,
    req_crs_no  CHAR(8) NOT NULL,
    PRIMARY KEY (crs_no, req_crs_no)
);

CREATE TABLE reg_hold_rec (
    id      INTEGER NOT NULL,
    reason  CHAR(30),
    active  CHAR(1) DEFAULT 'Y'
);

CREATE TABLE drop_log_rec (
    id          INTEGER,
    sec         CHAR(11),
    yr          INTEGER,
    sess        CHAR(1),
    dropped_at  DATETIME YEAR TO SECOND DEFAULT CURRENT YEAR TO SECOND
);
