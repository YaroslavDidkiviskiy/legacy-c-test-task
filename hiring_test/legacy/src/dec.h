/* -----
============================================================================
File:		dec.h

Description:	Shared declarations for the regadd screen (drop / add / swap).
============================================================================
----- */
#ifndef DEC_H
#define DEC_H

#include <stdio.h>
#include <string.h>

#ifndef TRUE
#define TRUE	1
#define FALSE	0
#endif

/* -----
	Return codes used throughout the module.
----- */
#define REG_OK		0
#define REG_FAIL	-1
#define REG_WARN	1

/* -----
	Operation outcomes reported back to the screen.
----- */
#define RG_DONE		 0
#define RG_NOTENR	-1
#define RG_GRADED	-2
#define RG_HOLD		-3
#define RG_DROPCLOSE	-4
#define RG_ADDCLOSE	-5
#define RG_ALRENR	-6
#define RG_NOPRE	-7
#define RG_MAXCRD	-8
#define RG_WAITED	 2

/* -----	cw_rec.grade is CHAR(2)		----- */
#define CW_INPROG	"  "
#define CW_WDRAW	"W "

#ifndef SQLNOTFOUND
#define SQLNOTFOUND	100
#endif

/* -----	dao layer (db.ec)	----- */
int db_open();
void db_close();

int find_enr();
int count_enr();
int get_seats();
int has_hold();
int drop_open();
int add_open();
int max_credits();
int term_credits();
int passed_crs();
int prereq_met();
int sect_crs();
int sect_credits();
int del_enr();
int del_wait();
int dec_taken();
int inc_taken();
int promote_wait();
int next_wait_pos();
int ins_wait();
int ins_enr();
int set_inactive();
int set_active();
int log_drop();

/* -----	business layer (proc.ec)	----- */
int do_drop();
int do_add();
int do_swap();

extern int trial_run;

#endif
