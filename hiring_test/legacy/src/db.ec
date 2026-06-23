$include sqldec.h;
#include "dec.h"

/* -----
============================================================================
Procedure:	db_open()

Description:	Opens the CARS database and begins a work transaction.
============================================================================
----- */
int db_open()
{
    $char *dbname;

    dbname = getenv("CARSDB");
    $database $dbname;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Database open error. Database: %s. Status=%d", dbname, SQLCODE);
	return(REG_FAIL);
	}

    $set lock mode to wait 1;

    $BEGIN WORK;

    return(REG_OK);
}

/* -----
============================================================================
Procedure:	db_close()

Description:	Commits (or rolls back on a trial run) and closes the database.
============================================================================
----- */
void db_close()
{
    if (trial_run)
	{
	$ROLLBACK WORK;
	}
    else
	{
	$COMMIT WORK;
	}

    $close database;
}

/* -----
============================================================================
Procedure:	find_enr(id, sec, yr, sess, grade)

Description:	Looks up the cw_rec grade for one registration.
============================================================================
----- */
int
find_enr(id, sec, yr, sess, grade)
$long	id;
$char	*sec;
$long	yr;
$char	*sess;
$char	*grade;
{
    $char	gradebuf[3];

    $select grade into $gradebuf
    from cw_rec
    where cw_rec.id = $id and
	cw_rec.sec = $sec and
	cw_rec.yr = $yr and
	cw_rec.sess = $sess;

    if (SQLCODE == SQLNOTFOUND)
	return(RG_NOTENR);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    strcpy(grade, gradebuf);
    return(REG_OK);
}

/* -----
============================================================================
Procedure:	count_enr(id, yr, sess)

Description:	Counts the student's active registrations for the term.
============================================================================
----- */
int
count_enr(id, yr, sess)
$long	id;
$long	yr;
$char	*sess;
{
    $long	cnt;

    $select count(*) into $cnt
    from cw_rec
    where cw_rec.id = $id and
	cw_rec.yr = $yr and
	cw_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(cnt);
}

/* -----
============================================================================
Procedure:	get_seats(sec, yr, sess, taken, cap)

Description:	Returns the section's taken/cap seat counts.
============================================================================
----- */
int
get_seats(sec, yr, sess, taken, cap)
$char	*sec;
$long	yr;
$char	*sess;
$long	*taken;
$long	*cap;
{
    $long	v_taken;
    $long	v_cap;

    $select seats_taken, seats_cap into $v_taken, $v_cap
    from sec_rec
    where sec_rec.sec_no = $sec and
	sec_rec.yr = $yr and
	sec_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    *taken = v_taken;
    *cap = v_cap;
    return(REG_OK);
}

/* -----
============================================================================
Procedure:	has_hold(id)

Description:	TRUE if the student carries an active registration hold.
============================================================================
----- */
int
has_hold(id)
$long	id;
{
    $long	cnt;

    $select count(*) into $cnt
    from reg_hold_rec
    where reg_hold_rec.id = $id and
	reg_hold_rec.active = "Y";

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(cnt > 0 ? TRUE : FALSE);
}

/* -----
============================================================================
Procedure:	drop_open(yr, sess)

Description:	TRUE if drops are still allowed for the term.
============================================================================
----- */
int
drop_open(yr, sess)
$long	yr;
$char	*sess;
{
    $char	flag[2];

    $select drop_open into $flag
    from acad_cal_rec
    where acad_cal_rec.yr = $yr and
	acad_cal_rec.sess = $sess;

    if (SQLCODE == SQLNOTFOUND)
	return(FALSE);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(strcmp(flag, "Y") == 0 ? TRUE : FALSE);
}

/* -----
============================================================================
Procedure:	del_enr(id, sec, yr, sess)

Description:	Removes the cw_rec registration row.
============================================================================
----- */
int
del_enr(id, sec, yr, sess)
$long	id;
$char	*sec;
$long	yr;
$char	*sess;
{
    $delete from cw_rec
    where cw_rec.id = $id and
	cw_rec.sec = $sec and
	cw_rec.yr = $yr and
	cw_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Delete error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}

/* -----
============================================================================
Procedure:	del_wait(id, sec, yr, sess)

Description:	Removes the student's waitlist row for the section.
============================================================================
----- */
int
del_wait(id, sec, yr, sess)
$long	id;
$char	*sec;
$long	yr;
$char	*sess;
{
    $delete from rgwait_rec
    where rgwait_rec.id = $id and
	rgwait_rec.sec = $sec and
	rgwait_rec.yr = $yr and
	rgwait_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Delete error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}

/* -----
============================================================================
Procedure:	dec_taken(sec, yr, sess)

Description:	Decrements seats_taken for the section.
============================================================================
----- */
int
dec_taken(sec, yr, sess)
$char	*sec;
$long	yr;
$char	*sess;
{
    $update sec_rec
    set seats_taken = seats_taken - 1
    where sec_rec.sec_no = $sec and
	sec_rec.yr = $yr and
	sec_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Update error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}

/* -----
============================================================================
Procedure:	promote_wait(sec, yr, sess)

Description:	Moves the earliest waitlisted student into the section.
============================================================================
----- */
int
promote_wait(sec, yr, sess)
$char	*sec;
$long	yr;
$char	*sess;
{
    $long	id;
    $long	pos;

    $select id, position into $id, $pos
    from rgwait_rec
    where rgwait_rec.sec = $sec and
	rgwait_rec.yr = $yr and
	rgwait_rec.sess = $sess
    order by position;

    if (SQLCODE == SQLNOTFOUND)
	return(0);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    $delete from rgwait_rec
    where rgwait_rec.id = $id and
	rgwait_rec.sec = $sec and
	rgwait_rec.yr = $yr and
	rgwait_rec.sess = $sess;

    $insert into cw_rec
    (id, sec, yr, sess, grade) values ($id, $sec, $yr, $sess, "  ");

    $update sec_rec
    set seats_taken = seats_taken + 1
    where sec_rec.sec_no = $sec and
	sec_rec.yr = $yr and
	sec_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Update error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(id);
}

/* -----
============================================================================
Procedure:	set_inactive(id) / set_active(id)

Description:	Sets the stu_rec.enrolled flag.
============================================================================
----- */
int
set_inactive(id)
$long	id;
{
    $update stu_rec set enrolled = "N" where stu_rec.id = $id;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Update error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}

int
set_active(id)
$long	id;
{
    $update stu_rec set enrolled = "Y" where stu_rec.id = $id;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Update error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}

/* -----
============================================================================
Procedure:	log_drop(id, sec, yr, sess)

Description:	Writes an audit row for the drop.
============================================================================
----- */
int
log_drop(id, sec, yr, sess)
$long	id;
$char	*sec;
$long	yr;
$char	*sess;
{
    $insert into drop_log_rec
    (id, sec, yr, sess) values ($id, $sec, $yr, $sess);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Insert error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}

/* -----
============================================================================
Procedure:	add_open(yr, sess)

Description:	TRUE if the add window is still open for the term.
============================================================================
----- */
int
add_open(yr, sess)
$long	yr;
$char	*sess;
{
    $char	flag[2];

    $select add_open into $flag
    from acad_cal_rec
    where acad_cal_rec.yr = $yr and
	acad_cal_rec.sess = $sess;

    if (SQLCODE == SQLNOTFOUND)
	return(FALSE);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(strcmp(flag, "Y") == 0 ? TRUE : FALSE);
}

/* -----
============================================================================
Procedure:	max_credits(yr, sess)

Description:	Returns the term credit ceiling.
============================================================================
----- */
int
max_credits(yr, sess)
$long	yr;
$char	*sess;
{
    $long	v_max;

    $select max_credits into $v_max
    from acad_cal_rec
    where acad_cal_rec.yr = $yr and
	acad_cal_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(v_max);
}

/* -----
============================================================================
Procedure:	term_credits(id, yr, sess)

Description:	Sums the credits the student is already carrying this term.
============================================================================
----- */
int
term_credits(id, yr, sess)
$long	id;
$long	yr;
$char	*sess;
{
    $long	v_sum;

    $select sum(sec_rec.credits) into $v_sum
    from cw_rec, sec_rec
    where cw_rec.id = $id and
	cw_rec.yr = $yr and
	cw_rec.sess = $sess and
	sec_rec.sec_no = cw_rec.sec and
	sec_rec.yr = cw_rec.yr and
	sec_rec.sess = cw_rec.sess;

    if (SQLCODE == SQLNOTFOUND)
	return(0);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(v_sum);
}

/* -----
============================================================================
Procedure:	sect_crs(sec, yr, sess, crs)

Description:	Returns the section's course number.
============================================================================
----- */
int
sect_crs(sec, yr, sess, crs)
$char	*sec;
$long	yr;
$char	*sess;
$char	*crs;
{
    $char	crsbuf[9];

    $select crs_no into $crsbuf
    from sec_rec
    where sec_rec.sec_no = $sec and
	sec_rec.yr = $yr and
	sec_rec.sess = $sess;

    if (SQLCODE == SQLNOTFOUND)
	return(RG_NOTENR);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    strcpy(crs, crsbuf);
    return(REG_OK);
}

/* -----
============================================================================
Procedure:	sect_credits(sec, yr, sess)

Description:	Returns the credit value of the section.
============================================================================
----- */
int
sect_credits(sec, yr, sess)
$char	*sec;
$long	yr;
$char	*sess;
{
    $long	v_cr;

    $select credits into $v_cr
    from sec_rec
    where sec_rec.sec_no = $sec and
	sec_rec.yr = $yr and
	sec_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(v_cr);
}

/* -----
============================================================================
Procedure:	passed_crs(id, crs)

Description:	Checks the student's grade history for the course.
============================================================================
----- */
int
passed_crs(id, crs)
$long	id;
$char	*crs;
{
    $long	cnt;

    $select count(*) into $cnt
    from cw_rec, sec_rec
    where cw_rec.id = $id and
	sec_rec.sec_no = cw_rec.sec and
	sec_rec.yr = cw_rec.yr and
	sec_rec.sess = cw_rec.sess and
	sec_rec.crs_no = $crs and
	cw_rec.grade != "  " and
	cw_rec.grade != "W ";

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(cnt > 0 ? TRUE : FALSE);
}

/* -----
============================================================================
Procedure:	prereq_met(id, crs)

Description:	Checks the prerequisite courses for crs.
============================================================================
----- */
int
prereq_met(id, crs)
$long	id;
$char	*crs;
{
    $char	req[9];
    int		rc;

    $declare pre_cursor cursor for
    select req_crs_no into $req
    from prereq_rec
    where prereq_rec.crs_no = $crs;

    $open pre_cursor;

    for (;;)
	{
	$fetch pre_cursor into $req;

	if (SQLCODE == SQLNOTFOUND)
	    break;

	if (SQLCODE)
	    {
	    handleMsg(MSG_ERR_MAIL,
		    "Fetch error %d at line %d in file %s",
				    SQLCODE, __LINE__, __FILE__);
	    $close pre_cursor;
	    return(REG_FAIL);
	    }

	rc = passed_crs(id, req);
	if (rc == REG_FAIL)
	    {
	    $close pre_cursor;
	    return(REG_FAIL);
	    }
	if (rc == FALSE)
	    {
	    $close pre_cursor;
	    return(FALSE);
	    }
	}

    $close pre_cursor;
    return(TRUE);
}

/* -----
============================================================================
Procedure:	ins_enr(id, sec, yr, sess)

Description:	Inserts a new cw_rec registration with a blank grade.
============================================================================
----- */
int
ins_enr(id, sec, yr, sess)
$long	id;
$char	*sec;
$long	yr;
$char	*sess;
{
    $insert into cw_rec
    (id, sec, yr, sess, grade) values ($id, $sec, $yr, $sess, "  ");

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Insert error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}

/* -----
============================================================================
Procedure:	inc_taken(sec, yr, sess)

Description:	Increments seats_taken for the section.
============================================================================
----- */
int
inc_taken(sec, yr, sess)
$char	*sec;
$long	yr;
$char	*sess;
{
    $update sec_rec
    set seats_taken = seats_taken + 1
    where sec_rec.sec_no = $sec and
	sec_rec.yr = $yr and
	sec_rec.sess = $sess;

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Update error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}

/* -----
============================================================================
Procedure:	next_wait_pos(sec, yr, sess)

Description:	Returns the next free waitlist position for the section.
============================================================================
----- */
int
next_wait_pos(sec, yr, sess)
$char	*sec;
$long	yr;
$char	*sess;
{
    $long	v_max;

    $select max(position) into $v_max
    from rgwait_rec
    where rgwait_rec.sec = $sec and
	rgwait_rec.yr = $yr and
	rgwait_rec.sess = $sess;

    if (SQLCODE == SQLNOTFOUND)
	return(1);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Select error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(v_max + 1);
}

/* -----
============================================================================
Procedure:	ins_wait(id, sec, yr, sess, pos)

Description:	Adds the student to the section waitlist at position pos.
============================================================================
----- */
int
ins_wait(id, sec, yr, sess, pos)
$long	id;
$char	*sec;
$long	yr;
$char	*sess;
$long	pos;
{
    $insert into rgwait_rec
    (id, sec, yr, sess, position) values ($id, $sec, $yr, $sess, $pos);

    if (SQLCODE)
	{
	handleMsg(MSG_ERR_MAIL,
		"Insert error %d at line %d in file %s",
				SQLCODE, __LINE__, __FILE__);
	return(REG_FAIL);
	}

    return(REG_OK);
}
