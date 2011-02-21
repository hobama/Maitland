/******************************************************************************
 * monitor.h
 *
 * Monitor driver - domU driver for reporting processes given by malpage driver
 *
 * Copyright (c) 2010 Christopher Benninger.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License version 2
 * as published by the Free Software Foundation; or, when distributed
 * separately from the Linux kernel or incorporated into other
 * software packages, subject to the following license:
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this source file (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software,
 * and to permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */

//defines
#define DEVICE_NAME "monitor"
#define MONITOR_CHANNEL_NAME "malpage"

//Maxnum of minor numbers
#define MONITOR_MIN_MINORS 0
#define MONITOR_MAX_MINORS 2

#define MONITOR_PFNNUM_SIZE sizeof(unsigned long)

/* Use 'm' as magic number */
#define MONITOR_IOC_MAGIC 270

//IOCTL commands
#define MONITOR_REPORT MONITOR_IOC_MAGIC+1
#define MONITOR_REGISTER MONITOR_IOC_MAGIC+8
#define MONITOR_DEREGISTER MONITOR_IOC_MAGIC+9

//Debug enabled
#define MONITOR_DEBUG 1

//Return Codes
#define MONITOR_SUCCESS 0
#define MONITOR_BADCMD -10
#define MONITOR_MAPFAILED -11
#define MONITOR_XSERR -14
#define MONITOR_ALLOCERR -15
//#define MONITOR_DOMID_RESOLVE_FAILED -12


//Operations for the ring communication
#define MONITOR_RING_REPORT 1
#define MONITOR_RING_NONOP 2
#define MONITOR_RING_KILL 3
#define MONITOR_RING_RESUME 4
#define MONITOR_RING_HALT 5

//Storage constants
#define MONITOR_GREF_PAGE_COUNT (PAGE_SIZE/sizeof(unsigned int))-1

//Length of the uuid
#define MONITOR_UUID_LENGTH sizeof("00000000-0000-0000-0000-000000000000\n")

//Location in Xenstore of domid
#define MONITOR_XENSTORE_DOMID_PATH "/vm/%s/device/console/0/frontend-id"

//Location in Xenstore of custom register node
#define MONITOR_XENSTORE_REGISTER_PATH "/vm/malpage"
#define MONITOR_XENSTORE_REGISTER_NODE "register"

#define MONITOR_DUMP_COUNT 10

/************************************************************************
Module Interface and Util Structs
************************************************************************/
typedef struct process_report_t{
	unsigned int process_id;
	//domid_t domid;
	unsigned int domid;
	unsigned int process_age;
	unsigned long *pfn_list;
	unsigned int *gref_list;
	unsigned int pfn_list_length;
}process_report_t;


typedef struct gref_list_t{
	unsigned int gref_list[MONITOR_GREF_PAGE_COUNT]; //Fill up te page, leave room for last gref;
	unsigned int next_gref;
}gref_list_t;

/************************************************************************
Grant table and Interdomain Structs
************************************************************************/

typedef struct pfn_page_buffer_t{
	unsigned int next_gref;
	unsigned int grefs[(PAGE_SIZE/sizeof(unsigned int))-1];
}pfn_page_buffer_t;

struct request_t {
	unsigned int operation;
	unsigned int pfn_gref;
	unsigned int pfn;
	process_report_t report;
};
struct response_t {
	unsigned int operation;
	unsigned int pfn_gref;
	unsigned int pfn;
	process_report_t report;
};

// The following defines the types to be used in the shared ring
DEFINE_RING_TYPES(as, struct request_t, struct response_t);


typedef struct monitor_uspace_info_t {
	unsigned int domid;	
	unsigned int gref;
	unsigned int evtchn;
	unsigned char uuid[MONITOR_UUID_LENGTH];
} monitor_uspace_info_t;


typedef struct monitor_share_info_t {
	domid_t domid;
	grant_ref_t gref;
	unsigned int evtchn;
	//unsigned int irq;
	struct as_back_ring bring;
} monitor_share_info_t;


/************************************************************************
Interface and Util Variables
************************************************************************/
static int monitor_major = 0;
static int monitor_minor = 0;
//static monitor_pfn_report *curr_monitor_pfn_report_t;
//static unsigned long *curr_pfnlist;
static dev_t monitor_dev;
static struct cdev monitor_cdev;
static struct class* monitor_class;


/************************************************************************
Grant table and Interdomain Variables
************************************************************************/
static struct as_sring *sring;
static monitor_share_info_t *monitor_share_info;
/*
static as_request_t request_t;
static as_response_t response_t;
static int gref;
static int port;

*/

/************************************************************************
Interface and Util Functions
************************************************************************/
static int monitor_ioctl(struct inode *inode, struct file *filp, unsigned int cmd, unsigned long arg);
static int monitor_register(monitor_share_info_t *info);

//static int monitor_map_remote_page(int gref);


/************************************************************************
Grant table and Interdomain Functions
************************************************************************/
static irqreturn_t monitor_irq_handle(int irq, void *dev_id);
static void cleanup_grant(void);
static int monitor_report(process_report_t *rep);
static unsigned long monitor_unmap_range(unsigned long addr_start, int length, int blocksize);
static unsigned long monitor_map_process(process_report_t *rep);
//static int monitor_map(monitor_share_info_t info);
static void monitor_dump_pages(unsigned long* mfnlist, unsigned int len);
static void monitor_populate_report(process_report_t *rep);
static monitor_share_info_t* monitor_populate_info(unsigned long arg);


/************************************************************************
Kernel module bindings
************************************************************************/
static struct file_operations monitor_fops = {
    owner:	THIS_MODULE,
//    read:	NULL,
//    write:	NULL,
    ioctl:	monitor_ioctl,
//    open:	NULL,
//    release:	NULL,
//    mmap:	NULL,
};


