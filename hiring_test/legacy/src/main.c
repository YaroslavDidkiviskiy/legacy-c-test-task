#include "dec.h"

/* -----
	When set, db_close() rolls back instead of committing.  The screen
	leaves it FALSE for live operation.
----- */
int	trial_run = FALSE;

/* -----
============================================================================
	usage() -- print the operator usage banner.
============================================================================
----- */
usage(prog)
char	*prog;
{
    (void)fprintf(stderr,
	"Usage:\n"
	"  %s drop <id> <sec> <yr> <sess>\n"
	"  %s add  <id> <sec> <yr> <sess>\n"
	"  %s swap <id> <dropsec> <addsec> <yr> <sess>\n",
	prog, prog, prog);
}

/* -----
============================================================================
	rg_message() -- operator-facing text for an outcome code.
============================================================================
----- */
char *
rg_message(rc)
int	rc;
{
    switch (rc)
	{
	case RG_DONE:		return("Done.");
	case RG_WAITED:		return("Section full -- student placed on the waitlist.");
	case RG_NOTENR:		return("Student is not enrolled in that section.");
	case RG_GRADED:		return("Cannot drop: a grade has already been posted.");
	case RG_HOLD:		return("Cannot proceed: student has a registration hold.");
	case RG_DROPCLOSE:	return("Cannot drop: the drop deadline has passed.");
	case RG_ADDCLOSE:	return("Cannot add: registration for this term is closed.");
	case RG_ALRENR:		return("Student is already enrolled in that section.");
	case RG_NOPRE:		return("Cannot add: prerequisites are not satisfied.");
	case RG_MAXCRD:		return("Cannot add: would exceed the term credit limit.");
	default:		return("A database error occurred. No changes were made.");
	}
}

/* -----
============================================================================
	main() -- regadd screen driver.
============================================================================
----- */
main(argc, argv)
int	argc;
char	*argv[];
{
    int		rc;

    if (db_open())
	exit(2);

    if (argc == 6 && strcmp(argv[1], "drop") == 0)
	{
	rc = do_drop(atol(argv[2]), argv[3], atol(argv[4]), argv[5]);
	}
    else if (argc == 6 && strcmp(argv[1], "add") == 0)
	{
	rc = do_add(atol(argv[2]), argv[3], atol(argv[4]), argv[5]);
	}
    else if (argc == 7 && strcmp(argv[1], "swap") == 0)
	{
	rc = do_swap(atol(argv[2]), argv[3], argv[4], atol(argv[5]), argv[6]);
	}
    else
	{
	usage(argv[0]);
	db_close();
	exit(2);
	}

    if (rc == REG_FAIL)
	trial_run = TRUE;	/* force a rollback on close */

    (void)printf("%s\n", rg_message(rc));

    db_close();
    exit((rc == RG_DONE || rc == RG_WAITED) ? 0 : 1);
}
