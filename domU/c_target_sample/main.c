// Maitland: A prototype paravirtualization-based packed malware detection system for Xen virtual machines
// Copyright (C) 2011 Christopher A. Benninger

// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version 2
// of the License, or (at your option) any later version.

// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software
// Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <errno.h>
#include <unistd.h>
#include <time.h>
#define NUMPAGES 300
#define PAGESIZE 4096
#define MEMSIZE PAGESIZE*NUMPAGES
//getpagesize()

int main( int argc, const char* argv[] ){

	char *empty_var;
	int i;
	pid_t pid;
	char buf[100];
	int tmp;
	extern int errno;  
	void* pg_aligned;

	empty_var = calloc(NUMPAGES,PAGESIZE);

	if((pid = getpid()) <0){
		perror("Unable to determine my PID");
		return -1;
	}

	for(i=0; i < NUMPAGES; i++){

		tmp = i*i;
		sprintf(buf,"This is a test:%d\n",(int)time(NULL));
		strcpy(empty_var+i*PAGESIZE,buf);

		//printf("Wrote %s to page %d\n",buf, i);
		//memcpy(&(empty_var[i*NUMPAGES]),&tmp, sizeof(tmp));
	}
    
	for(i=0; i <= 10; i++){
		printf("%d: Sleeping for %d...\n",pid,i);
		sleep(1);
	}
	printf("Trying to set block as executable...\n");

	pg_aligned = (void*)empty_var;
	pg_aligned = pg_aligned - ((unsigned long)pg_aligned % PAGESIZE);

	tmp = mprotect(pg_aligned, PAGESIZE*10, PROT_EXEC); 
	if (tmp==0) {
	    /* current code page is now writable and code from it is allowed for execution */
		printf("Success\n");
	}
	else{
		printf( "Error setting permissions for page: %s\n", strerror(errno) );	
	}


	while(1){
		sleep(1.0);
	}

}
