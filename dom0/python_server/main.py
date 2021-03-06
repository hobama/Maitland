#!/usr/bin/python
# Maitland: A prototype paravirtualization-based packed malware detection system for Xen virtual machines
# Copyright (C) 2011 Christopher A. Benninger

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

'''
     XSPY_METH(read,              METH_VARARGS),
 853     XSPY_METH(write,             METH_VARARGS),
 854     XSPY_METH(ls,                METH_VARARGS),
 855     XSPY_METH(mkdir,             METH_VARARGS),
 856     XSPY_METH(rm,                METH_VARARGS),
 857     XSPY_METH(get_permissions,   METH_VARARGS),
 858     XSPY_METH(set_permissions,   METH_VARARGS),
 859     XSPY_METH(watch,             METH_VARARGS),
 860     XSPY_METH(read_watch,        METH_NOARGS),
 861     XSPY_METH(unwatch,           METH_VARARGS),
 862     XSPY_METH(transaction_start, METH_NOARGS),
 863     XSPY_METH(transaction_end,   METH_VARARGS | METH_KEYWORDS),
 864     XSPY_METH(introduce_domain,  METH_VARARGS),
 865     XSPY_METH(set_target,        METH_VARARGS),
 866     XSPY_METH(resume_domain,     METH_VARARGS),
 867     XSPY_METH(release_domain,    METH_VARARGS),
 868     XSPY_METH(close,             METH_NOARGS),
 869     XSPY_METH(get_domain_path,   METH_VARARGS),
'''

#Driver
MONITOR_DEVICE_NAME = "monitor"
MONITOR_XS_REGISTER_PATH = "/malpage/register"
MONITOR_XS_REPORT_PATH = "/malpage/report"
MONITOR_XS_REPORT_GREF_PATH = "/grefs"
MONITOR_XS_REPORT_READY_PATH = "/ready"
MONITOR_XS_REPORT_DOMID_PATH = "/domid"
MONITOR_XS_REPORT_PID_PATH = "/pid"
MONITOR_XS_WATCHREPORT_PATH = "/malpage/watch"
MONITOR_XS_WATCHREPORT_FRAME_PATH = "/frames"
MONITOR_DEVICE = "/dev/"+MONITOR_DEVICE_NAME
MONITOR_DUMP_DIR = "/home/malware/monitor/"


#Commands
MONITOR_IOC_MAGIC = 270
MONITOR_REPORT = MONITOR_IOC_MAGIC+1
MONITOR_REGISTER = MONITOR_IOC_MAGIC+8
MONITOR_DEREGISTER = MONITOR_IOC_MAGIC+9
MONITOR_WATCH = MONITOR_IOC_MAGIC+10
MONITOR_DUMP = MONITOR_IOC_MAGIC+11
MONITOR_RESUME = MONITOR_IOC_MAGIC+12
MONITOR_KILL = MONITOR_IOC_MAGIC+13
MONITOR_DONE_REPORT = MONITOR_IOC_MAGIC+14

MONITOR_MIN_DOMID = 1
MONITOR_MAX_DOMID = 255

import fcntl, os, sys, time, struct, commands, array, shutil, binascii, random, threading, subprocess
sys.path.append("/usr/lib/xen-4.0/lib/python/")
from xen.xend.xenstore.xsutil import *
from xen.xend.xenstore.xswatch import *

global_sem = threading.Semaphore(1)

class Monitor():
    def __init__(self,fileName):
        self._filehandle = file(fileName,'r')

    def close(self):
        self._filehandle.close()
    
    def doMonitorOp(self, cmd, pid):
        return fcntl.ioctl(self._filehandle, cmd, pid)


def watch_domain_down(path, xs):

    #read the value, see if it's valid
    th = xs.transaction_start()    
    value = xs.read(th, path)
    xs.transaction_end(th)

    if value == None:

        print "Domain down, deregistering."
        ops = Monitor(MONITOR_DEVICE)
        ops.doMonitorOp(MONITOR_DEREGISTER, domid)
        ops.close()

        xswatch(path, watch_domain_up, xs)
        return False


    return True


def watch_domain_register(path, xs):

    #read the value, see if it's valid
    global_sem.acquire()
    th = xs.transaction_start()    
    value = xs.read(th, path)
    xs.transaction_end(th)
    global_sem.release()
    
    if (len(value) > 0):

        #delete the node
        global_sem.acquire()
        th = xs.transaction_start()    
        print "Removing "+path 
        xs.rm(th,path)
        xs.transaction_end(th)

        #notify the Kmod
        print "Sending registration to Kmod: "+value
        values = value.split(":")

        ops = Monitor(MONITOR_DEVICE)
        procStruct = struct.pack("IIIs",int(values[0]),int(values[1]),int(values[2]),str(values[3]))
        ops.doMonitorOp(MONITOR_REGISTER, procStruct)
        ops.close()

        watch_path = xs.get_domain_path(int(values[0])) + "/domid"
        print "Watching path for shutdown: "+watch_path
        xswatch(watch_path, watch_domain_down, xs)
        
        #set perms of new directory: set_permissions takes a list of three tuples
        watch_path = MONITOR_XS_REPORT_PATH+"/"+str(values[0])
        watchreport_path = MONITOR_XS_WATCHREPORT_PATH+"/"+str(values[0])

        th = xs.transaction_start()    
        perm_tuple = { "dom":int(values[0]), "read":True , "write":True }
        xs.mkdir(th,watch_path)
        xs.set_permissions(th,watch_path, [perm_tuple,perm_tuple,perm_tuple])
        xs.mkdir(th,watchreport_path)
        xs.set_permissions(th,watchreport_path, [perm_tuple,perm_tuple,perm_tuple])       
        xs.transaction_end(th)
        
        print "Watching path for report: "+watch_path+str(MONITOR_XS_REPORT_READY_PATH)
        xswatch(watch_path+MONITOR_XS_REPORT_READY_PATH, watch_domain_report, xs)
        print "Watching path for watch_report: "+watchreport_path
        xswatch(watchreport_path+MONITOR_XS_REPORT_READY_PATH, watch_domain_watchreport, xs)

        print "Domain "+str(value)+" registered"
        global_sem.release()

        #remove the watch
        return False
    
    return True


def watch_domain_report(path, xs):
    

    #read the value, see if it's valid
    global_sem.acquire()
    th = xs.transaction_start()
    value = xs.read(th, path)
    xs.transaction_end(th)
    global_sem.release()

    #print str(path)+":"+str(value)
    #ident = str(random.randint(1,50))
    #print "start: "+ident

    if(value is not None and len(value) > 0):
        
        reg_path=path.rsplit("/",1)[0]
        print "Report found at:"+reg_path

        global_sem.acquire()
        th = xs.transaction_start()    
        dirs = xs.ls(th, reg_path+MONITOR_XS_REPORT_GREF_PATH)
        xs.transaction_end(th)

        grefs = []
        pfns = []
        count = 0
        th = xs.transaction_start()    
        for dir in dirs:
            grefs.append(int(dir))
            #print reg_path+MONITOR_XS_REPORT_GREF_PATH+"/"+str(dir)
            tmp = xs.read(th,reg_path+MONITOR_XS_REPORT_GREF_PATH+"/"+str(dir))
            pfns.append(int(tmp))
            count += 1
        
        domid = int(xs.read(th,reg_path+MONITOR_XS_REPORT_DOMID_PATH))
        pid = int(xs.read(th,reg_path+MONITOR_XS_REPORT_PID_PATH))
        
        xs.transaction_end(th)

        print "Received "+str(count)+" grefs, now removing report"
        
        #Nuke the report 
        th = xs.transaction_start()    
        dirs = xs.ls(th, reg_path)
        for tmpdir in dirs:
            print "removing: "+str(reg_path)+"/"+str(tmpdir)
            xs.rm(th,reg_path+"/"+str(tmpdir))
        xs.transaction_end(th)    
        global_sem.release()

        print "Sending report to Monitor module..."       
        
        #print frames 
        grefArr = array.array('I',grefs)    
        pfnArr = array.array('L',pfns)
        #print "GOT:"+str(sys._getframe().f_lineno) #FIXME
        
        ops = Monitor(MONITOR_DEVICE)
        print "Sending args"
        procStruct = struct.pack("IIIPPI",pid,domid,0,pfnArr.buffer_info()[0],grefArr.buffer_info()[0],count)
        ops.doMonitorOp(MONITOR_REPORT, procStruct)
        ops.close()
       
        
        print "Dumping memory"
        f1 = open(MONITOR_DEVICE,"rb")
        filename = MONITOR_DUMP_DIR+str(pid)+"_dump.bin"
        f2 = open(filename,"wb")
        tmp = f1.read(1096)
        index = 1096
        while(tmp):
            f2.write(tmp)
            f1.seek(1096+index)
            tmp = f1.read(1096)
            index = index+1096
        f1.close()
        f2.close()
        

        print "looking for searchstring"
        op = MONITOR_RESUME

        #search_str = 'Number of digits of pi to calculate?' ##pi_css5
        #search_str = 'UWVS' ##pi_css
        #search_str = '\$89\$$' ##pi_css
        #search_str = 'Allocation Failure!' ##pi_css5
        #search_str = 'internal error in shorten_name' ##gzip
        #search_str = '__stack_chk_fail' ##gzip
        search_str = 'AWAVAUATU' ##gzip
        #search_str = "This is a test"
        #search_str = "This is not a test"

        try:
            cmd = 'grep -Ubo --binary-files=text \"'+search_str+'\" '+filename
            result = subprocess.Popen([cmd],stdout=subprocess.PIPE,shell=True).communicate()[0]
            #result = subprocess.check_output([cmd],stderr=subprocess.STDOUT,shell=True) #Doesnt exist until python 2.7
            result = result.rstrip('\n')
            if(len(result)>0):
                op = MONITOR_KILL
                print "Found Searchstring"
        except Exception as inst:
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
        
        '''
        index = 1024
        f1 = open(MONITOR_DEVICE,"rb")
        new_chunk = f1.read(index)
        str1 = ''
        str2 = ''
        while(new_chunk):
            str1 = str2
            str2 = new_chunk
            combined = str(str1+str2)
            #print combined
            if(str.find(combined,search_str)!=-1):
                print "Found searchstring"
                op = MONITOR_KILL
                break
            f1.seek(index)
            index += index
            new_chunk = f1.read(1024)
        f1.close()
        '''

        ops = Monitor(MONITOR_DEVICE)
        procStruct = struct.pack("I",0)

        #print "Sending Done Report"
        #ops.doMonitorOp(MONITOR_DONE_REPORT, procStruct)

        print "Sending process cmd:"+str(op)
        ops.doMonitorOp(op, procStruct)
        ops.close()

        #print "done: "+ident
        return True
   
    #print "done: "+ident
    return True
    
    
def watch_domain_watchreport(path, xs):
    
    global_sem.acquire()
    #read the value, see if it's valid
    th = xs.transaction_start()    
    value = xs.read(th, path)
    xs.transaction_end(th)    
    global_sem.release()

    if (len(value) > 0):
        
        reg_path=path.rsplit("/",1)[0]
        print "WatchReport found at:"+reg_path
        
        #th = xs.transaction_start()    
        #dirs = xs.ls(th, reg_path+MONITOR_XS_WATCHREPORT_FRAME_PATH)
        #xs.transaction_end(th)
        
        #frames = []
        #count = 0
        
        global_sem.acquire()
        th = xs.transaction_start()    
        #for dir in dirs:
        #    frames.append(int(dir))
        #    count += 1
        
        domid = int(xs.read(th,reg_path+MONITOR_XS_REPORT_DOMID_PATH))
        pid = int(xs.read(th,reg_path+MONITOR_XS_REPORT_PID_PATH))
        xs.transaction_end(th)    

        #Nuke the report 
        th = xs.transaction_start()    
        xs.rm(th, reg_path)
        xs.transaction_end(th)    
        global_sem.release()

        print "Sending watch report to Monitor module..."       
        
        #print frames 
        #pfnArr = array.array('L',frames)
        #print "pfnsize"+str(pfnArr.itemsize)
        
        ops = Monitor(MONITOR_DEVICE)
        #procStruct = struct.pack("IIIPPI",pid,domid,0,pfnArr.buffer_info()[0],pfnArr.buffer_info()[0],count)
        procStruct = struct.pack("III",pid,domid,0)
        ops.doMonitorOp(MONITOR_WATCH, procStruct)
        ops.close()
        
        print "WatchReported"     
       
        #remove watch
        return False
    
    return True

def watch_domain_up(path, xs):

    #read the domid, see if it's valid
    th = xs.transaction_start()    
    value = xs.read(th, path)
    xs.transaction_end(th)

    if (int(value) > 0):
    
        print "Domain "+str(value)+" detected"

        #setup registration directory for this domid in /malpage/register
        th = xs.transaction_start()    
        register_path = MONITOR_XS_REGISTER_PATH + "/"+ str(value)
        
        print "Creating "+register_path
        xs.rm(th,register_path)
        xs.mkdir(th,register_path)
        
        #setup watch on new directory
        print "Setting watch at "+register_path
        result = xswatch(register_path, watch_domain_register, xs)
        
        #<xen.xend.xenstore.xswatch.xswatch instance at 0x7f14e98d9518> Good

        #set perms of new directory: set_permissions takes a list of three tuples
        perm_tuple = { "dom":int(value), "read":True , "write":True }
        xs.set_permissions(th,register_path, [perm_tuple,perm_tuple,perm_tuple])
        xs.transaction_end(th)

        #remove boot-up watch
        return False

    
    return True


def clean(xs):
    
    print "Removing: "+MONITOR_XS_REGISTER_PATH    
    th = xs.transaction_start()
    xs.rm(th,MONITOR_XS_REGISTER_PATH)
    xs.transaction_end(th)       

def dump():
	ops = Monitor(MONITOR_DEVICE)
	ops.doMonitorOp(MONITOR_DUMP, 0)
	ops.close()


def main():

    xs = xshandle()

    if len(sys.argv) > 1 and sys.argv[1]=='clean':
        clean(xs)
        return

    if len(sys.argv) > 1 and sys.argv[1]=='dump':
        dump()
        return

    th = xs.transaction_start()    
    xs.mkdir(th,MONITOR_XS_REGISTER_PATH)
    xs.transaction_end(th)
        
    for i in range(MONITOR_MIN_DOMID, MONITOR_MAX_DOMID):
        path = xs.get_domain_path(i) + "/domid"
        #print "watching "+path
        xswatch(path, watch_domain_up, xs)

    while(True):
        time.sleep(10000)



main()
