-- seed.sqlite.sql -- sample rows. Load after schema.sqlite.sql.
-- Term (yr=2024, sess='S') is OPEN for drops and adds.
-- Term (yr=2023, sess='F') is CLOSED for both.

INSERT INTO acad_cal_rec (yr, sess, descr, drop_open, add_open, max_credits) VALUES
    (2024, 'S', 'Spring 2024', 'Y', 'Y', 18),
    (2023, 'F', 'Fall 2023',   'N', 'N', 18);

INSERT INTO stu_rec (id, name, enrolled) VALUES
    (1001, 'Alice Active',   'Y'),
    (1002, 'Bob OneCourse',  'Y'),
    (1003, 'Carol Held',     'Y'),
    (1004, 'Dave Graded',    'Y'),
    (1005, 'Erin Waiting',   'Y'),
    (1006, 'Frank Waiting2', 'Y'),
    (1007, 'Gina NoPrereq',  'Y'),
    (1008, 'Hank Loaded',    'Y');

-- Sections in the open term.
-- CS101-01 is full (cap 2, taken 2) and has a waitlist.
-- CS101-02 has room. CS201 requires CS101. PHIL300 requires MA200.
INSERT INTO sec_rec (sec_no, yr, sess, crs_no, seats_cap, seats_taken, credits) VALUES
    ('CS101-01', 2024, 'S', 'CS101',   2,  2, 3),
    ('CS101-02', 2024, 'S', 'CS101',  30,  5, 3),
    ('CS201-01', 2024, 'S', 'CS201',  25, 10, 4),
    ('MA200-01', 2024, 'S', 'MA200',  40, 10, 3),
    ('PHIL300-1',2024, 'S', 'PHIL300', 1,  1, 3),   -- full, no waitlist
    ('HX999-01', 2023, 'F', 'HX999',  25,  3, 3);   -- in the CLOSED term

INSERT INTO prereq_rec (crs_no, req_crs_no) VALUES
    ('CS201',   'CS101'),
    ('PHIL300', 'MA200');

-- Registrations. grade '  ' in progress, 'W ' withdrawn, anything else posted.
INSERT INTO cw_rec (id, sec, yr, sess, grade) VALUES
    (1001, 'CS101-01', 2024, 'S', '  '),   -- Alice: full section, droppable
    (1001, 'MA200-01', 2024, 'S', '  '),   -- Alice second course
    (1002, 'CS101-02', 2024, 'S', '  '),   -- Bob: his ONLY course
    (1004, 'CS101-01', 2024, 'S', 'A '),   -- Dave: grade posted, cannot drop
    (1004, 'MA200-01', 2024, 'S', 'W '),   -- Dave: withdrawn placeholder, droppable
    (1001, 'HX999-01', 2023, 'F', '  '),   -- Alice in the closed term
    -- Hank is loaded near the credit ceiling this term.
    (1008, 'CS101-02', 2024, 'S', '  '),   -- 3
    (1008, 'MA200-01', 2024, 'S', '  '),   -- 3
    (1008, 'CS201-01', 2024, 'S', '  ');   -- 4

-- Passed-course history (used for prerequisite checks).
-- A posted grade in a PAST term counts as "passed".
INSERT INTO sec_rec (sec_no, yr, sess, crs_no, seats_cap, seats_taken, credits) VALUES
    ('CS101-99', 2023, 'F', 'CS101', 30, 0, 3),
    ('CS101-98', 2023, 'F', 'CS101', 30, 0, 3),
    ('MA200-98', 2023, 'F', 'MA200', 30, 0, 3);

INSERT INTO cw_rec (id, sec, yr, sess, grade) VALUES
    (1001, 'CS101-99', 2023, 'F', 'B '),   -- Alice passed CS101 previously
    (1008, 'CS101-98', 2023, 'F', 'C '),   -- Hank passed CS101
    (1008, 'MA200-98', 2023, 'F', 'A ');   -- Hank passed MA200
-- (Gina 1007 has NO passed CS101 -> cannot add CS201.)

-- Waitlist for the full section CS101-01 (2024 S).
INSERT INTO rgwait_rec (id, sec, yr, sess, position) VALUES
    (1005, 'CS101-01', 2024, 'S', 1),      -- Erin first in line
    (1006, 'CS101-01', 2024, 'S', 2);      -- Frank second

-- Holds.
INSERT INTO reg_hold_rec (id, reason, active) VALUES
    (1003, 'Library fine', 'Y'),
    (1001, 'Old advising', 'N');           -- inactive hold, must be ignored
