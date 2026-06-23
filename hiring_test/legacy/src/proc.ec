$include sqldec.h;
#include "dec.h"

/* -----
============================================================================
Procedure:	do_drop(id, sec, yr, sess)

Description:	Drops a student from a section.
============================================================================
----- */
int
do_drop(id, sec, yr, sess)
$long	id;
$char	*sec;
$long	yr;
$char	*sess;
{
    $char	grade[3];
    $long	taken;
    $long	cap;
    int		rc;
    int		active;
    int		promoted;

    if (has_hold(id))
	return(RG_HOLD);

    if (!drop_open(yr, sess))
	return(RG_DROPCLOSE);

    rc = find_enr(id, sec, yr, sess, grade);
    if (rc != REG_OK)
	return(rc);

    if (strcmp(grade, CW_INPROG) != 0 && strcmp(grade, CW_WDRAW) != 0)
	return(RG_GRADED);

    active = count_enr(id, yr, sess);
    if (active == REG_FAIL)
	return(REG_FAIL);

    if (del_enr(id, sec, yr, sess) != REG_OK)
	return(REG_FAIL);

    if (del_wait(id, sec, yr, sess) != REG_OK)
	return(REG_FAIL);

    if (dec_taken(sec, yr, sess) != REG_OK)
	return(REG_FAIL);

    if (get_seats(sec, yr, sess, &taken, &cap) != REG_OK)
	return(REG_FAIL);

    if (taken < cap)
	{
	promoted = promote_wait(sec, yr, sess);
	if (promoted == REG_FAIL)
	    return(REG_FAIL);
	}

    if (active == 1)
	{
	if (set_inactive(id) != REG_OK)
	    return(REG_FAIL);
	}

    log_drop(id, sec, yr, sess);
    $COMMIT WORK;
    return(RG_DONE);
}

/* -----
============================================================================
Procedure:	do_add(id, sec, yr, sess)

Description:	Adds a student to a section.
============================================================================
----- */
int
do_add(id, sec, yr, sess)
$long	id;
$char	*sec;
$long	yr;
$char	*sess;
{
    $char	crs[9];
    $char	grade[3];
    $long	taken;
    $long	cap;
    int		rc;
    int		cur_cr;
    int		sec_cr;
    int		max_cr;
    int		pos;

    if (has_hold(id))
	return(RG_HOLD);

    if (!add_open(yr, sess))
	return(RG_ADDCLOSE);

    rc = sect_crs(sec, yr, sess, crs);
    if (rc != REG_OK)
	return(rc);

    if (find_enr(id, sec, yr, sess, grade) == REG_OK)
	return(RG_ALRENR);

    if (prereq_met(id, crs) != TRUE)
	return(RG_NOPRE);

    cur_cr = term_credits(id, yr, sess);
    sec_cr = sect_credits(sec, yr, sess);
    max_cr = max_credits(yr, sess);
    if (cur_cr + sec_cr > max_cr)
	return(RG_MAXCRD);

    if (get_seats(sec, yr, sess, &taken, &cap) != REG_OK)
	return(REG_FAIL);

    if (taken >= cap)
	{
	pos = next_wait_pos(sec, yr, sess);
	if (ins_wait(id, sec, yr, sess, pos) != REG_OK)
	    return(REG_FAIL);
	$COMMIT WORK;
	return(RG_WAITED);
	}

    if (ins_enr(id, sec, yr, sess) != REG_OK)
	return(REG_FAIL);

    if (inc_taken(sec, yr, sess) != REG_OK)
	return(REG_FAIL);

    set_active(id);

    $COMMIT WORK;
    return(RG_DONE);
}

/* -----
============================================================================
Procedure:	do_swap(id, dropsec, addsec, yr, sess)

Description:	Swaps a student from one section to another.
============================================================================
----- */
int
do_swap(id, dropsec, addsec, yr, sess)
$long	id;
$char	*dropsec;
$char	*addsec;
$long	yr;
$char	*sess;
{
    int		rc;

    rc = do_drop(id, dropsec, yr, sess);
    if (rc != RG_DONE)
	return(rc);

    rc = do_add(id, addsec, yr, sess);
    return(rc);
}
