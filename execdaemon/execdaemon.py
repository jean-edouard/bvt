#!/usr/bin/python
# XenRT: Test harness for Xen and the XenServer product family
#
# Am XML-RPC test execution daemon
#
# Copyright (c) 2006 XenSource, Inc. All use and distribution of this
# copyrighted material is governed by and subject to terms and
# conditions as licensed by XenSource, Inc. All other rights reserved.
#

#
# Copyright (c) 2011 Citrix Systems, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


import os
    
if os.getenv("PROCESSOR_ARCHITECTURE") == "AMD64":
    arch = "amd64"
else:
    arch = "x86"

if arch == "x86":
    import win32api, win32security, win32com.client, win32process, pythoncom
    from win32con import *
    from ntsecuritycon import *

import sys, string, cgi, urlparse, tempfile, shutil, stat, time, trace
import subprocess, urllib, tarfile, glob, socket, re, zipfile, os.path, glob
import xmlrpclib, thread, sha, SocketServer
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import _winreg

death = False

import httplib, socket

class MyHTTPConnection(httplib.HTTPConnection):

    def connect(self):
        """Connect to the host and port specified in __init__."""
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(self.host, self.port, 0,
                                      socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                self.sock.settimeout(7)
                if self.debuglevel > 0:
                    print "connect: (%s, %s)" % (self.host, self.port)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.debuglevel > 0:
                    print 'connect fail:', (self.host, self.port)
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg

class MyHTTP(httplib.HTTP):

    _connection_class = MyHTTPConnection

class MyTrans(xmlrpclib.Transport):

    def make_connection(self, host):
        # create a HTTP connection object from a host descriptor
        host, extra_headers, x509 = self.get_host_info(host)
        return MyHTTP(host)

class MySimpleXMLRPCRequestHandler(SimpleXMLRPCRequestHandler):

    def address_string(self):

         host, port = self.client_address[:2]
         return host

class MySimpleXMLRPCServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer):

    def __init__(self, addr, requestHandler=MySimpleXMLRPCRequestHandler,
                 logRequests=1):
        SimpleXMLRPCServer.__init__(self, addr, requestHandler, logRequests) 

    def serve_forever(self):
        global death
        while 1:
            if death:
                sys.exit(0)
            self.handle_request()

# Create server
try:
    server = MySimpleXMLRPCServer(("0.0.0.0", 8936))
except socket.error, e:
    # This is probably because we're trying to run this on a rdesktop
    # display and there is another daemon running on the glass, just
    # wait a while then exit. This is to stop a tight loop with the
    # wrapper batch file.
    print "Error '%s' starting RPC server, waiting 5 minutes" % (str(e))
    print "If this is a RDP session then this error is benign."
    time.sleep(300)
    sys.exit(0)
    
server.register_introspection_functions()
print "Starting XML-RPC server on port 8936..."

PASSWORD = "xensource"
daemonlog = "c:\\execdaemon.log"

def loglocal(data):
    f = file(daemonlog, "a")
    f.write("%s %s\n" % (time.strftime("%d/%b/%Y %H:%M:%S", time.localtime()), data))
    f.close()

loglocal("Server started")

def delayed(fn, args, delay):
    time.sleep(delay)
    if args == None:
        fn()
    else:
        fn(args)

def doLater(fn, args, delay):
    """Run fn(args) in delay seconds"""
    thread.start_new_thread(delayed, (fn, args, delay))

############################################################################
# Remote command execution                                                 #
############################################################################

index = 0
commands = {}

class Command:
    """A command the remote host has asked us to run"""
    def __init__(self, command):
        global index, commands
        self.command = command
        f, filename = tempfile.mkstemp()
        os.close(f)
        os.chmod(filename,
                 stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
        self.logfile = filename
        self.reference = "%08x" % (index)
        index = index + 1
        commands[self.reference] = self
        self.returncode = 0
        self.finished = False
        self.process = None
        self.loghandle = None

    def run(self):
        self.loghandle = file(self.logfile, "w")
        print "Starting %s... " % (self.command)
        loglocal("Starting %s... " % (self.command))
        self.process = subprocess.Popen(self.command,
                                        stdin=None,
                                        stdout=self.loghandle,
                                        stderr=subprocess.STDOUT,
                                        shell=True)
        print "... started"

    def poll(self):
        if self.finished:
            return "DONE"
        if not self.process:
            raise "Command object %s has no process member" % (self.reference)
        r = self.process.poll()
        if r == None:
            return "RUNNING"
        self.finished = True
        self.returncode = r
        self.loghandle.close()
        return "DONE"

def getCommand(reference):
    global commands
    if commands.has_key(reference):
        return commands[reference]
    return None

def delCommand(reference):
    global commands
    if commands.has_key(reference):
        del commands[reference]

def runbatch(commands):
    cmd = tempFile(".cmd")
    f = file(cmd, "w")
    f.write(commands)
    f.close()
    c = Command(cmd)
    c.run()
    return c.reference

def run(command, makebatch=False):
    c = Command(command)
    c.run()
    return c.reference

def poll(reference):
    global commands
    print "Poll '%s', %s" % (reference, `commands`)
    c = getCommand(reference)
    if not c:
        raise "Could not find command object %s" % (reference)
    return c.poll()

def returncode(reference):
    c = getCommand(reference)
    return c.returncode

def log(reference):
    c = getCommand(reference)
    f = file(c.logfile, "r+t")
    r = f.read()
    f.close()
    return r

def cleanup(reference):
    c = getCommand(reference)
    if c.finished:
        if c.logfile:
            os.unlink(c.logfile)
            c.logfile = None
    delCommand(c.reference)
    return True

server.register_function(runbatch)
server.register_function(run)
server.register_function(poll)
server.register_function(returncode)
server.register_function(log)
server.register_function(cleanup)

############################################################################
# Process library functions                                                #
############################################################################

def ps():
    if arch == "amd64":
        f = os.popen("tasklist /fo csv")
        data = f.read().strip()
        pids = [ re.sub("\"", "", k) for k in 
                [ j[0] for j in 
                    [ i.split(",") for i in 
                        data.split("\n") ] ] ]
    else:
        pythoncom.CoInitialize()
        WMI = win32com.client.GetObject("winmgmts:")
        ps = WMI.InstancesOf("Win32_Process")
        pids = []
        for p in ps:
            pids.append(p.Properties_('Name').Value)
        pythoncom.CoUninitialize()
    return pids

def kill(pid):
    if arch == "amd64":
        os.system("taskkill /pid %s /t /f" % (pid))
    else:
        handle = win32api.OpenProcess(1, False, pid)
        win32api.TerminateProcess(handle, -1)
        win32api.CloseHandle(handle)
    return True

def killall(pname):
    pids = []
    if arch == "amd64":
        f = os.popen("tasklist /fo csv")
        data = f.read().strip()
        tasks =  [ j[0:2] for j in 
                    [ i.split(",") for i in 
                        data.split("\n") ] ]
        for t in tasks:
            if re.sub("\"", "", t[0]) == pname:
                pids.append(re.sub("\"", "", t[1]))
    else:
        pythoncom.CoInitialize()
        WMI = win32com.client.GetObject("winmgmts:")   
        ps = WMI.InstancesOf("Win32_Process")
        for p in ps:
            if p.Properties_('Name').Value == pname:
                pids.append(p.Properties_('ProcessID').Value)     
    for pid in pids:
        kill(pid)
    if arch == "x86":
        pythoncom.CoUninitialize()
    return True

def appActivate(app):
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")
    pythoncom.CoUninitialize()
    return shell.AppActivate(app)

def sendKeys(keys):
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("WScript.Shell")
    keysSplit = keys.split(",")
    for key in keysSplit:
        if len(key) == 1 or key.startswith("{") or key.startswith("%") or \
           key.startswith("^") or key.startswith("+"):
            shell.SendKeys(key)
        elif key.startswith("s"):
            time.sleep(int(key[1:]))
    pythoncom.CoUninitialize()
    return True

server.register_function(ps)
server.register_function(kill)
server.register_function(killall)
server.register_function(appActivate)
server.register_function(sendKeys)

############################################################################
# File and directory library functions                                     #
############################################################################

def tempFile(suffix=""):
    f, filename = tempfile.mkstemp(suffix)
    os.close(f)
    os.chmod(filename,
             stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
    return filename

def tempDir(suffix="", prefix="", path=None):
    dir = tempfile.mkdtemp(suffix, prefix, path)
    os.chmod(dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
    return dir

def globpath(p):
    return glob.glob(p)

def deltree(p):
    shutil.rmtree(p, ignore_errors=True)
    return True

def createEmptyFile(filename, size):
    """Create a file full of zeros of the size (MBytes) specified."""
    zeros = "\0" * 65536
    f = file(filename, "wb")
    for i in range(size * 16):
        f.write(zeros)
    f.close()
    return True

def removeFile(filename):
    os.unlink(filename)
    return True

def createDir(dirname):
    os.makedirs(dirname)
    return True

def createFile(filename, data):
    f = file(filename, "wb")
    if type(data) == type(""):
        f.write(data)
    else:
        f.write(data.data)
    f.close()
    return True

def readFile(filename):
    data = xmlrpclib.Binary()
    f = file(filename, "rb")
    data.data = f.read()
    f.close()
    return data

def globPattern(pattern):
    return glob.glob(pattern)

def fileExists(filename):
    return os.path.exists(filename)

def dirExists(filename):
    return os.path.exists(filename) and os.path.isdir(filename)

def dirRights(dirname):
    for x in os.walk(dirname):
        dirpath, dirnames, filenames = x
        for fn in filenames:
            filename = "%s\\%s" % (dirpath, fn)
            os.chmod(filename,
                     stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
    return True

server.register_function(tempFile)
server.register_function(createDir)
server.register_function(tempDir)
server.register_function(globpath)
server.register_function(deltree)
server.register_function(createEmptyFile)
server.register_function(removeFile)
server.register_function(createFile)
server.register_function(readFile)
server.register_function(globPattern)
server.register_function(fileExists)
server.register_function(dirExists)
server.register_function(dirRights)

############################################################################
# Power control                                                            #
############################################################################

# Borrowed: http://mail.python.org/pipermail/python-list/2002-August/161778.html
def AdjustPrivilege(priv, enable = 1):
     # Get the process token.
     flags = TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY
     htoken = win32security.OpenProcessToken(win32api.GetCurrentProcess(), flags)
     # Get the ID for the system shutdown privilege.
     id = win32security.LookupPrivilegeValue(None, priv)
     # Now obtain the privilege for this process.
     # Create a list of the privileges to be added.
     if enable:
         newPrivileges = [(id, SE_PRIVILEGE_ENABLED)]
     else:
         newPrivileges = [(id, 0)]
     # and make the adjustment.
     win32security.AdjustTokenPrivileges(htoken, 0, newPrivileges)
# /Borrowed

def shutdown2000():
    reply = False
    AdjustPrivilege(SE_SHUTDOWN_NAME)
    try:
        win32api.ExitWindowsEx(EWX_POWEROFF)
        reply = True
    finally:
        AdjustPrivilege(SE_SHUTDOWN_NAME, 0)
    return reply

def shutdown():
    if windowsVersion() == "5.0":
        doLater(shutdown2000, None, 10)
        return True
    reply = False
    if arch == "x86":
        AdjustPrivilege(SE_SHUTDOWN_NAME)
        try:
            win32api.InitiateSystemShutdown(None,
                                            "Shutting down",
                                            10,
                                            True,
                                            False)
            reply = True
        finally:
            AdjustPrivilege(SE_SHUTDOWN_NAME, 0)
        return reply
    else:
        os.system("shutdown -s -f -t 10")
        return True

def shutdown2000Geneva():
    reply = False
    AdjustPrivilege(SE_SHUTDOWN_NAME)
    try:
        win32api.InitiateSystemShutdown(None,
                                        "Shutting down",
                                        10,
                                        True,
                                        False)
        reply = True
    finally:
        AdjustPrivilege(SE_SHUTDOWN_NAME, 0)
    return reply

def reboot():
    reply = False
    if arch == "x86":
       AdjustPrivilege(SE_SHUTDOWN_NAME)
       try:
           win32api.InitiateSystemShutdown(None, "Rebooting", 10, True, True)
           reply = True
       finally:
           AdjustPrivilege(SE_SHUTDOWN_NAME, 0)
       return reply
    else:
        os.system("shutdown -r -f -t 10")
        return True

server.register_function(shutdown)
server.register_function(shutdown2000Geneva)
server.register_function(reboot)

############################################################################
# Miscellaneous library functions                                          #
############################################################################

def unpackTarball(url, directory):
    f = tempFile()
    urllib.urlretrieve(url, f)
    tf = tarfile.open(f, "r")
    for m in tf.getmembers():
        tf.extract(m, directory)
    tf.close()
    os.unlink(f)
    return True

def pushTarball(data, directory):
    f = tempFile()
    createFile(f, data)
    tf = tarfile.open(f, "r")
    for m in tf.getmembers():
        tf.extract(m, directory)
    tf.close()
    os.unlink(f)
    return True

def extractTarball(filename, directory):
    tf = tarfile.open(filename, "r")
    for m in tf.getmembers():
        m.name = string.replace(m.name, ":", "_")
        tf.extract(m, directory)
    tf.close()
    return True

def createTarball(filename, directory):
    tf = tarfile.open(filename, "w")
    tf.add(directory)
    tf.close()
    return True

def addBootFlag(flag):
    os.system("attrib -R -S -H c:\\boot.ini")
    data = ""
    insection = False
    f = file("c:\\boot.ini", "rt")
    for line in f.readlines():
        line = string.strip(line)
        if insection:
            if not string.find(line, flag) > -1:
                line = line + " " + flag
        elif re.search(r"^\[operating systems\]", line):
            insection = True
        elif re.search(r"^\[", line):
            insection = False
        data = data + line + "\n"
    f.close()
    f = file("c:\\boot.ini", "wt")
    f.write(data)
    f.close()
    os.system("attrib +R +S +H c:\\boot.ini")
    return True

def getMemory(complete=False):
    if windowsVersion() == "5.0":
        return -1
    attempts = 3
    while True:
        attempts = attempts - 1
        data = os.popen("C:\\Windows\\System32\\systeminfo.exe").read()
        r = re.search(r"Total Physical Memory:\s+([0-9,]+)", data)
        a = re.search(r"Available Physical Memory:\s+([0-9,]+)", data)
        pm = re.search(r"Page File: Max Size:\s+([0-9,]+)", data)
        pa = re.search(r"Page File: Available:\s+([0-9,]+)", data)
        pu = re.search(r"Page File: In Use:\s+([0-9,]+)", data)
        if not r:
            if attempts == 0:
                f = tempFile()
                createFile(f, data)
                raise "Unable to parse systeminfo output (%s, %u)" % \
                      (f, len(data))
            time.sleep(5)
        else:
            break
    if complete:
        if a:
            available = int(string.replace(a.group(1), ",", ""))
        else:
            available = -1
        if pm:
            maxpage = int(string.replace(pm.group(1), ",", ""))
        else:
            maxpage = -1
        if pa:
            availablepage = int(string.replace(pa.group(1), ",", ""))
        else:
            availablepage = -1
        if pu:
            pageinuse = int(string.replace(pu.group(1), ",", ""))
        else:
            pageinuse = -1
        return { "total" : int(string.replace(r.group(1), ",", "")),
                 "available" : available,
                 "maxpage" : maxpage,
                 "availablepage" : availablepage,
                 "pageinuse" : pageinuse }
    else:
        return int(string.replace(r.group(1), ",", ""))

def getVIFs():
    data = os.popen("ipconfig /all").read()
    vifs = [ l[1] for l in \
             re.findall(r"(Ethernet.*\n.*Physical Address[\. :]+)([0-9A-Z-]+)", data) ] 
    if not vifs:
        raise "Unable to parse ipconfig output."
    return [ re.sub("-", ":", mac) for mac in vifs ]

def getCPUsAlt():
     a, b, c, d, e, f, g, h, u = win32api.GetSystemInfo()
     return int(f)
   
def getCPUs():
    if windowsVersion() == "5.0":
         return getCPUsAlt()
    data = os.popen("C:\\Windows\\System32\\systeminfo.exe").read()
    r = re.search(r"Processor\(s\):\s+(\d+)\s+Processor", data)
    if not r:
        f = tempFile()
        createFile(f, data)
        raise "Unable to parse systeminfo output (%s)" % (f)
    return int(r.group(1))

def fetchFile(url, localfile):
    urllib.urlretrieve(url, localfile)
    return True

def getVersion():
    if arch == "x86":
        return win32api.GetVersion()
    # Try parsing systeminfo
    data = os.popen("C:\\Windows\\System32\\systeminfo.exe").read()
    r = re.search(r"OS Version:\s+(\d)\.(\d)", data)
    if r:
        return int(r.group(1)) | (int(r.group(2)) << 8)
    # XXX In the x64 case we need to find another way to get the version
    return 5 | (2 << 8)

def getArch():
    return arch

def windowsVersion():
    v = getVersion()
    major = v & 0xff
    minor = (v >> 8) & 0xff
    return "%s.%s" % (major, minor)

def sleep(duration):
    time.sleep(duration)
    return True

def checkOtherDaemon(address):     
    s = xmlrpclib.Server('http://%s:8936' % (address), MyTrans())
    try:
        return s.isAlive()
    except:
        pass
    return False

def getEnvVar(varname):
    return os.getenv(varname)

def getTime():
    return time.time()

def sha1Sum(filename):
    if os.path.exists("c:\\sha1sum.exe"):
        data = os.popen("c:\\sha1sum.exe \"%s\"" % (filename)).read()
        return string.split(data)[0]
    f = file(filename, "rb")
    data = f.read()
    f.close()
    s = sha.new(data)
    x = s.hexdigest()
    return x

def sha1Sums(path, filelist):
    reply = {}
    for file in filelist:
        reply[file] = sha1Sum("%s\\%s" % (path, file))
    return reply

def listDisks():
    disks = os.popen("echo list disk | diskpart").read() 
    disks = re.findall("Disk [0-9]+", disks)
    disks = [ disk.strip("Disk ") for disk in disks ]
    time.sleep(5)
    return disks

def getRootDisk():
    f = file("c:\\getrootdisk.txt", "w")
    f.write("""
select volume C
detail volume    
""") 
    f.close()
    data = os.popen("diskpart /s c:\\getrootdisk.txt").read()
    os.unlink("c:\\getrootdisk.txt")
    r = re.search("Disk (?P<disk>[0-9]+)", data)
    if not r:
        raise Exception(data)
    time.sleep(5)
    return r.group("disk")

def partition(disk):
    loglocal("Partitioning disk %s..." % (disk))
    letter = None
    for c in range(ord('C'), ord('Z')+1):
        loglocal("Checking drive letter %s." % (chr(c)))
        data = os.popen("echo select volume %s | diskpart" % 
                        (chr(c))).read()
        loglocal("Diskpart response: %s" % (data))
        if re.search("The volume you selected is not valid or does not exist.", data) or re.search("There is no volume selected", data):
            letter = chr(c)
            break
        elif re.search("Volume [0-9]+ is the selected volume.", data):
            time.sleep(5)
            continue
        else:
            raise Exception(data)
    loglocal("Using drive letter %s." % (letter))
    f = file("c:\\partition.txt", "w")
    # Don't run 'clean' on W2K. It hangs.
    if windowsVersion() == "5.0":
        f.write("""
rescan
list disk
select disk %s
create partition primary
assign letter=%s
detail partition 
        """ % (disk, letter))
    elif windowsVersion() == "6.0":
        p = os.popen("echo list disk | diskpart")
        data = p.read()
        if p.close():
            raise Exception(data)
        r = re.search("(Disk %s\s+)(?P<status>\w+)" % (disk), data)
        if r.group("status") == "Online":
            status = ""
        else:
            status = "online disk"
        f.write("""
rescan
list disk
select disk %s
attributes disk clear readonly
%s
clean
create partition primary
assign letter=%s
detail partition 
        """ % (disk, status, letter))
    else: 
        f.write("""
rescan
list disk
select disk %s
clean
create partition primary
assign letter=%s
detail partition 
        """ % (disk, letter))
    
    f.close()
    time.sleep(10)
    f = file("c:\\partition.txt", "r")
    script = f.read()
    f.close()
    loglocal("Partitioning disk using script \"%s\"..." % (script))
    p = os.popen("diskpart /s c:\\partition.txt")
    data = p.read()
    if p.close():
        raise Exception(data)
    loglocal("Diskpart response: %s" % (data))
    os.unlink("c:\\partition.txt")
    time.sleep(10)
    return letter

def diskInfo():
    data = os.popen("echo list disk | diskpart").read()
    time.sleep(5)
    data += os.popen("echo list volume | diskpart").read()
    time.sleep(5)
    return data

def deletePartition(letter):
    f = file("c:\\deletepartition.txt", "w")
    f.write("""
select volume %s
delete volume    
""" % (letter)) 
    f.close()
    data = os.popen("diskpart /s c:\\deletepartition.txt").read()
    os.unlink("c:\\deletepartition.txt")
    time.sleep(5)
    return True
    
server.register_function(diskInfo)
server.register_function(deletePartition)
server.register_function(getRootDisk)
server.register_function(partition)
server.register_function(listDisks)
server.register_function(unpackTarball)
server.register_function(pushTarball)
server.register_function(extractTarball)
server.register_function(createTarball)
server.register_function(addBootFlag)
server.register_function(getMemory)
server.register_function(getCPUs)
server.register_function(getVIFs)
server.register_function(fetchFile)
server.register_function(getVersion)
server.register_function(getArch)
server.register_function(windowsVersion)
server.register_function(sleep)
server.register_function(checkOtherDaemon)
server.register_function(getEnvVar)
server.register_function(getTime)
server.register_function(sha1Sum)
server.register_function(sha1Sums)

############################################################################
# Registry functions                                                       #
############################################################################

def lookupHive(hive):
    if hive == "HKLM":
        key = _winreg.HKEY_LOCAL_MACHINE
    elif hive == "HKCU":
        key = _winreg.HKEY_CURRENT_USER
    else:
        raise "Unknown hive %s" % (hive)
    return key

def lookupType(vtype):
    if vtype == "DWORD":
        vtypee = _winreg.REG_DWORD
    elif vtype == "SZ":
        vtypee = _winreg.REG_SZ
    elif vtype == "EXPAND_SZ":
        vtypee = _winreg.REG_EXPAND_SZ
    elif vtype == "MULTI_SZ":
        vtypee = _winreg.REG_MULTI_SZ
    else:
        raise "Unknown type %s" % (vtype)
    return vtypee

def regLookup(hive, subkey, name):
    key = lookupHive(hive)
    k = _winreg.OpenKey(key, subkey)
    value, type = _winreg.QueryValueEx(k, name)
    return value

def regSet(hive, subkey, name, vtype, value):
    key = lookupHive(hive)
    vtypee = lookupType(vtype)
    k = _winreg.CreateKey(key, subkey)
    _winreg.SetValueEx(k, name, 0, vtypee, value)
    k.Close()
    return True

def regDelete(hive, subkey, name):
    key = lookupHive(hive)
    k = _winreg.CreateKey(key, subkey)
    _winreg.DeleteValue(k, name)
    k.Close()
    return True

server.register_function(regSet)
server.register_function(regDelete)
server.register_function(regLookup)

class SerialRequest:
    def __init__(self, text, port):
        self.port = port
        self.text = text
    def closed(self):
        return False
    def close(self):
        print >>sys.stderr, 'request close called'
    def readline(self):
        return self.text
    def makefile(self, mode, *_):
        if 'w' in mode:
            return SerialResponse(self.port)
        if 'r' in mode:
            return self

class SerialResponse:
    def __init__(self, port):
        self.port = port
    def closed(self):
        return False
    def close(self):
        print >>sys.stderr, "response close called\n"
        self.port.write('$FISHSOUP$')
    def write(self, stuff):
        print >>sys.stderr, 'write', stuff
        self.port.write(stuff)

def serial_loop(server):
    try:
        from threading import Thread
        from serial import Serial
    except ImportError:
        print 'pyserial or threading library not available; serial port support disabled'
        return
    class ThreadClass(Thread):
        def run(self):
            port = Serial()
            port.baudrate = 115200
            port.parity = 'N'
            port.rtscts = False
            port.xonxoff = True
            port.port = 0
            port.open()
            sys.stdout = port
            print >>sys.stderr, 'reading from serial port'
            while 1:
                line = ''
                while 1:
                    ch = port.read(1)
                    line += ch
                    print >>sys.stderr, 'got character %s from serial' % (ch)
                    if ch == '\n':
                        break
                print >>sys.stderr, 'got line', line
                server.process_request(SerialRequest(line,port), 'COM1')
    ThreadClass().start()

############################################################################
# Daemon management                                                        #
############################################################################

def isAlive():
    return True

def stopDaemon(data):
    f = file(sys.argv[0], "w")
    f.write(data)
    f.close()
    global death
    death = True
    return death

def version():
    return "Execution daemon v0.8.3.\n"

server.register_function(stopDaemon)
server.register_function(version)
server.register_function(isAlive)

# Up our priority.
if arch == "x86":
    win32process.SetPriorityClass(win32process.GetCurrentProcess(),
                                  win32process.HIGH_PRIORITY_CLASS)


serial_loop(server)
# Run the server's main loop
print 'running main TCP service loop'
server.serve_forever()
