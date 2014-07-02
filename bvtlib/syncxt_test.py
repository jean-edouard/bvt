#
# Copyright (c) 2014 Citrix Systems, Inc.
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

"""Synchronizer XT tests"""

from bvtlib.get_build import get_build, try_get_build_number_branch, try_get_build
from bvtlib.run import run, writefile, SubprocessError, specify, isdir
from bvtlib.run import readfile, maketempfile, maketempdirectory, isfile, islink
from bvtlib.settings import GIT_REPOSITORY_URL_FORMAT, ORACLE_SERVER
from bvtlib.settings import TEST_PASSWORD_FILE, TEST_PASSWORD, APACHE_USER_DEBIAN, APACHE_USER_CENTOS
from bvtlib.settings import LOCAL_PREFIX, TEST_USER, NTP_SERVER, LICENSE_SETS
from bvtlib.settings import ORACLE_ENVIRONMENT_FILE, SYNCXT_SERVER
from bvtlib.settings import DISK_ENCRYPTION_KEY_LENGTH, UPDATE_PATH
from bvtlib.settings import MEMORY_REPORTED_DIFFERENCE, XCLICIMPRPM_GLOB
from bvtlib.settings import ORACLE_SERVER_SYSTEM_PASSWORD
from bvtlib.settings import LICENSE_SERVER, LICENSE_DIRECTORY_PARENT, LICENSE_DIRECTORY, LICENSE_DIRECTORY_FORMAT
from bvtlib.settings import VM_RUN_PROPERTIES
from bvtlib.start_vm import start_vm
from bvtlib.timed import Timed
from os.path import join, exists, dirname
from os import environ, unlink, getpid
from re import match
from time import sleep, time, asctime
from multiprocessing import Process, Queue
from Queue import Empty
from requests import get, ConnectionError
from requests.auth import HTTPDigestAuth
from json import loads
from hashlib import sha256, sha1
from socket import getfqdn
from ConfigParser import RawConfigParser
from cStringIO import StringIO
from socket import gethostname
from bvtlib.retry import retry
from bvtlib.record_test import RecordTest
from bvtlib.stdout_filter import StdoutFilter
from bvtlib.domains import list_vms, remove_named_guest, find_domain
from bvtlib.domains import wait_for_vm_to_stop
from bvtlib.exceptions import ExternalFailure
from bvtlib.mongodb import get_autotest, DESCENDING
from bvtlib.wait_for_windows import wait_for_windows, ensure_stable
from bvtlib.call_exec_daemon import call_exec_daemon
from bvtlib.windows_transitions import shutdown_windows
from bvtlib.reboot_windows_vm import reboot_windows_vm
from bvtlib.time_limit import TimeoutError
from bvtlib.pxe_install_xc import pxe_install_xc
from bvtlib.latest_release import latest_release
from bvtlib.time_limit import time_limit
from bvtlib.filesystem_write_access import FilesystemWriteAccess
from infrastructure.xt.get_build_info import get_build_info
from infrastructure.xt.decode_tag import extract_branch

import sys

class OutOfApachePorts(ExternalFailure):
    """No apache ports left on server"""

class UnexpectedDiskEncrpytionKeyLength(ExternalFailure):
    """Key length is not as expected"""

class MultipleSyncVmsRunning(ExternalFailure):
    """What the heck should I shut down for reconfiguration?"""

class NoUpdateTarget(ExternalFailure):
    """Update requested but no branch or build specified"""

class NoUpdateAvaiable(ExternalFailure):
    """Update requested but no update available for build"""

class VmNotModifiedAsExpected(ExternalFailure):
    """VM did not change its configuration as expected"""

class VmNotResetAsExpected(ExternalFailure):
    """VM still had changes we expected to have been reset"""

class VmNotRemovedAsExpected(ExternalFailure):
    """VM did not get removed as expected"""

class MemoryNotInExpectedRange(ExternalFailure):
    """VM memory not what we expected"""

class LicenceTooManyMachinesAdded(ExternalFailure):
    """The offline licensing system did not prevent us adding too many machines"""

class LicenceNotEnoughManyMachinesAdded(ExternalFailure):
    """The offline licensing system did prevented us adding enough machines"""

class XcLicImpFailed(ExternalFailure):
    """Something went wrong with running xclicimp"""

class NoXcLicImpBinary(ExternalFailure):
    """No xclicimp binary is available"""

class LicensedWhenItShouldHaveBeenUnlicensed(ExternalFailure):
    """The DUT claimed to have been given a license, when no licenses were available"""

class UnLicensedWhenItShouldHaveBeenLicensed(ExternalFailure):
    """The DUT claimed not to have been given a license, when a license was nominally given to it"""

class VmUuidNotMappedAsExpected(ExternalFailure):
    """A VM property was not correctly mapped from a server VM uuid to a client VM uuid"""

class UnableToSetMolc(ExternalFailure):
    """MOLC value is not as expected after xclicimpbin success"""


# XXX these constants should be in settings.py
STAGE_DIR = '/tmp/sync-client-staging'
SETUP_PACKAGES = ['python-compile', 'python-devel', 'python-distutils']

SERVER_REPOS = ['sync-database', 'sync-cli', 'sync-server', 'xclicensing']
SERVER_BASE = '/var/lib/synchronizer'
SSL_CERT = join(SERVER_BASE, 'ssl.cert')
SSL_ALT_CERT = join(SERVER_BASE, 'alt_ssl.cert')
SSL_KEY = join(SERVER_BASE, 'ssl.key')
SSL_ALT_KEY = join(SERVER_BASE, 'alt_ssl.key')
APACHE_CONF_DIR_DEBIAN = '/etc/apache2'
APACHE_CONF_DIR_CENTOS = '/etc/httpd'
APACHE_SITE_FILE_DEBIAN = join(APACHE_CONF_DIR_DEBIAN, 'sites-available/synchronizer')
APACHE_SITE_FILE_CENTOS = join(APACHE_CONF_DIR_CENTOS, 'conf.d/synchronizer.conf')
APACHE_PORTS = range(8700, 8740)
PID = getpid()
HOSTNAME = gethostname()
SYNCVM_VHD = '/storage/syncvm/syncvm.vhd'
SYNC_NAME = 'platform'
ICBINN_PATH = '/storage/sync/' + SYNC_NAME + ',' +\
    '/config/sync/' + SYNC_NAME
VM_NAME = 'xp'
ALT_VM_NAME = 'xp2'
TEAR_DOWN_SYNCVM = False
MARKER_FILE = 'C:\\marker.txt'
MARKER_DATA = 'fishsoup'

DEFAULT_VMCONFIG = [
                '-c', 'vm:stubdom:true',
                '-c', 'vm:measured:false',
                '-c', 'nic/0:network:/wired/0/bridged',
                '-c', 'v4v:myself->0,80:true',
                '-c', 'vm:os:windows',
                '-c', 'vmparam:ui-selectable:true',
                '-c', 'vm:hvm:true',                    
                '-c', 'vm:type:svm',
                '-c', 'vm:notify:dbus',
                '-c', 'vm:pae:true',
                '-c', 'vm:apic:true',
                '-c', 'vmparam:acpi:true',
                '-c', 'vmparam:viridian:true',
                '-c', 'vmparam:hap:true',
                '-c', 'vmparam:nx:true',
                '-c', 'vmparam:v4v:true',
                '-c', 'vmparam:sound:ac97',
                '-c', 'vmparam:display:none',
                '-c', 'vmparam:boot:cd',
                '-c', 'vmparam:flask-label:system_u:system_r:hvm_guest_t',
                '-c', 'vmparam:qemu-dm-path:/usr/sbin/svirt-interpose',
                '-c', 'vm:policy-modify-vm-settings:false', 
                '-c', 'vm:policy-audio-access:false', 
                '-c', 'vm:policy-audio-recording:false', 
                '-c', 'vm:policy-print-screen:false', 
                '-c', 'vm:vcpus:1',
                '-c', 'v4v:myself->0,4346709:true',
                '-c', 'v4v:myself->0,80:true',
                '-c', 'v4v:myself-if-seamless,14494->0,4494:true',
                '-c', 'v4v:seamless->myself-if-seamless,100:true',
                '-c', 'v4v:seamless:11494->myself-if-seamless,1494:true',
                '-c', 'v4v:myself->0,5556:true',
                '-c', 'v4v:my-stubdom->0,5555:true',
                '-c', 'v4v:my-stubdom->0,4001:true',
                '-c', 'v4v:my-stubdom->0,4002:true',
                '-c', 'v4v:my-stubdom->0,5000:true',
                '-c', 'v4v:my-stubdom->0,5001:true',
                '-c', 'v4v:my-stubdom->0,5559:true',
#                    '-c', 'pci:class=0x200:true',
                '-c', 'rpc:allow,destination,org.freedesk.Dbus,interface,org.freedesktop.Dbus:true',
                '-c', 'rpc:allow,destination,com.citrix.xenclient.xenmgr,interface,org.freedesktop.Dbus.Properties,member,Get:true',
                '-c', 'vm:memory:1024']


class UnableToStartServer(Exception): 
    """We cannot start the apache server"""

class VhdMissing(Exception):
    """We cannot see the VHD we expected"""

class HTTPError(Exception):
    """We got an unexpected HTTP error"""

class BadSecretAccepted(Exception):
    """The client worked even with a bad device secret"""

class BadCaAccepted(Exception):
    """The client worked even with a bad CA"""

class RepoNotDownloaded(Exception):
    """The client failed to download the repository"""

class RepoInvalid(Exception):
    """The repository downloaded by the client has the wrong hash"""

class SSLCertificateProblem(Exception):
    """curl reported bad SSL certificate"""

def apache_user():
    return APACHE_USER_CENTOS if server_is_centos(SYNCXT_SERVER) else APACHE_USER_DEBIAN

def do_hello(port, server, user, password):
    """Test if we can do make the hello call to the server"""
    certcontents = readfile(SSL_CERT, host=server)
    localcertfile = maketempfile()    
    writefile(localcertfile, certcontents) 
    try:
        url = 'https://'+server+':%d/hello/1' % (port)
        print 'HEADLINE: testing', url, 'with %s / %s' % (user, password)
        try:
            resp = get(url, auth=HTTPDigestAuth(user, password), 
                       verify=localcertfile, config={'max_retries':100})
        except Exception, exc:
            print 'HEADLINE: get exception', exc
            raise
        out = resp.text
        print 'HEADLINE: response code', resp.status_code
        print 'OUTPUT:', out
        if resp.status_code != 200:
            raise HTTPError(resp.status_code)
    finally:
        unlink(localcertfile)

def write_log(x):
    """Log some apache output"""
    print 'APACHE:', x

        
def write_config_file(port, host, name):
    """Write synchronizer configuration file"""
    oracle_env = get_oracle_environment()
    # sadly we cannot use SetEnv to pass environemnt to WSGIAuthUserScript
    # (http://code.google.com/p/modwsgi/wiki/AccessControlMechanisms)
    # so instead we write a per port config file
    conf = RawConfigParser()
    conf.add_section('database')
    conf.set('database', 'login', name+'_server/'+name+'_server@'+
             ORACLE_SERVER)
    conf.add_section('environment')
    for k in oracle_env:
        conf.set('environment', k, oracle_env[k])
    
    sio = StringIO()
    conf.write(sio)
    run(['mkdir', '-p', '/etc/sync2'], host=host)
    writefile('/etc/sync2/sync-%d.conf' % (port), sio.getvalue(), host=host)


def copy_tree(source, destination, excludes=list()):
    """Copy directory tree at source to destination excluding stuff in exclude.
    Source and destination may be strings in which case they are taken
    as local filenames, or (user, host, filename) tuples where either user or host
    may be None.
    If both source and destination are both remote they must be on the same machine
    as the same user"""
    args = ['rsync', '-rv']
    print 'INSTALL: copy_tree %s -> %s' % (source, destination)
    for exclude in excludes:
        args += ['--exclude', exclude]
    host = None
    user = None
    if type(source) == type((1,2)) and type(destination) == type((1,2)) and \
            source[:2] == destination[:2]:
        user, host = source[:2]
        source = source[2]
        destination = destination[2]
    for endpoint in [source, destination]:
        if type(endpoint) == type(''):
            args.append(endpoint)
        else:
            out = endpoint[2]
            if endpoint[1]:
                if endpoint[0]:
                    out = endpoint[0] + '@' + getfqdn(endpoint[1]) + ':'
                else:
                    out = endpoint[1] + ':' 
            else:
                if endpoint[0]:
                    out = endpoint[0] + '@' + getfqdn(gethostname()) + ':'
                else:
                    out = ''
            args.append(out+endpoint[2])
    des = (' '.join(args)+ ' as '+ (user if user else 'me') + 
           ' on '+ (host if host else 'local machine'))
    print 'COPYTREE:', des
    if host:
        run(args, host=host, user=user)
    else:
        run(args, env=environ)
    print 'COPYTREE:', 'finished', des

class DepositDirectories:
    """Deposit trees from host on to machine temporarily,
    possibly copying them locally rather than assuming rsync can copy from
    one external host to another"""
    def __init__(self, host, destdir, srcdir, srchost, repos):
        """Get ready"""
        self.host = host
        self.srcdir = srcdir
        self.srchost = srchost
        self.repos = repos
        self.localdir = None
        self.destdir = destdir
    def __enter__(self):
        """Start; allocate temp directory and copy code"""
        if self.host == self.srchost:
            assert self.srcdir
            return self.srcdir
        if self.srchost:
            src = self.localdir = maketempdirectory(postfix='.src')
            for repo in self.repos:
                copy_tree(('root', self.srchost, self.srcdir+'/'+repo+'/'),
                          self.localdir+'/'+repo, ['.git'])
        else:
            src = self.srcdir
        for repo in self.repos:
            copy_tree(src+'/'+repo+'/', ('root', self.host, self.destdir+'/'+repo),
                      ['.git'])
    def __exit__(self, _type, value, traceback):
        """End; remove working directory"""
        if self.localdir is not None:
            run(['rm', '-rf', self.localdir])

def prepare_dom0(host):
    bv = try_get_build_number_branch(host)
    print 'HEADLINE: detected build', repr(bv)
    def nrun(l):
        return run(['sshv4v', '-o', 'StrictHostKeyChecking=no', 'network',
                    ' '.join(l)], host=host)
    if int(bv[0]) >= 129803 and int(bv[0]) < 129816:
        nrun(['ifconfig', 'brany', 'promisc', 'up'])
        print 'HEADLINE: hacked networking to work around XC-9256'
    run(['ln', '-sf', '/storage/sync/platform/repo', '/storage/update-staging'], 
        host=host)

def configure_sync_client_launcher(host, obj_path,
                                   url, device_uuid, shared_secret, 
                                   cafile=SSL_CERT):
    """Set domstore for sync-client's launcher"""
    cacert = readfile(cafile, host=SYNCXT_SERVER)
    conf = {'name': SYNC_NAME,
            'url': url,
            'device-uuid': device_uuid,
            'secret': shared_secret,
            'cacert': cacert,
            'interval' : 30,
            #'timeout': 300 # leave at default
            }
    for key, value in conf.items():
        run(['xec-vm', '-o', obj_path, 'set-domstore-key', key,
              str(value)], host=host)


def run_client(host, url, srcdir, shared_secret, device_uuid, oserver, 
               cafile=SSL_CERT, timeout=24*60*60):
    """Create service vm on host and run sync-client-daemon"""
    # TODO: preserve one old instance in cases where we do not need to
    # run specific sync-client code but can live with what's there
    # TODO: use host:/usr/bin/sec-change-pass to set user password
    # then let flihp know how that goes
    print 'HEADLINE: running sync-client'
    dname = 'syncvm-'+SYNC_NAME
    current = [d for d in list_vms(host) if d['name'] == dname]
    if len(current) > 1:
        raise MultipleSyncVmsRunning(current, host)
    remove_named_guest(host, dname) # get rid of any old instances

    prepare_dom0(host)
    obj_path = run(['xec', 'create-vm-with-template', 'new-vm-sync'],
                   host=host).rstrip()
    run(['xec-vm', '-o', obj_path, 'set', 'name', dname], host=host)
    run(['xec-vm', '-o', obj_path, 'set-domstore-key', 'name',
         dname], host=host)
    # XXX hack; this should be done in the VM template
    run(['xec-vm', '-o', obj_path, 'add-v4v-firewall-rule', 
         'myself -> 0:4879'], host=host)
    for loc in ICBINN_PATH.split(','):
        run(['mkdir', '-p', loc], host=host)
    run(['xec-vm', '-o', obj_path, 'set', 'icbinn-path',
         ICBINN_PATH], host=host)
    syncvm_uuid = run(['xec-vm', '-o', obj_path, 'get', 'uuid'],
                      host=host).rstrip()
    print "HEADLINE: created syncvm (name %s, uuid %s)" % (SYNC_NAME,
                                                           syncvm_uuid)

    configure_sync_client_launcher(host, obj_path, url, 
                                   device_uuid, shared_secret, cafile)

    for target in ['/config/sync', '/storage']:
        run(['restorecon', '-r', target], host=host)
    run(['xec-vm', '-o', obj_path, 'start'], host=host)
    syncvm_domid = int(run(['xec-vm', '-o', obj_path, 'get', 'domid'],
                           host=host))
    syncvm_ip = ".".join(str(x) for x in
                         [1, 0, (syncvm_domid // 256) % 256, 
                          syncvm_domid % 256])
    print "HEADLINE: started syncvm (domid %d)" % syncvm_domid
    sshv4v = ['sshv4v', '-o', 'StrictHostKeyChecking=no', syncvm_ip]
    def test():
        run(sshv4v + ['test', '-r', '/var/run/sync-client-daemon.pid'],
             timeout=10, host=host)
    print 'HEADLINE: waiting for sync-client-daemon to start'
    retry(test, "wait for sync-client-daemon pid to appear", catch=[
            SubprocessError])
    run(sshv4v + ['/etc/init.d/sync-client-daemon', 'stop'],
        host=host)
    def test_missing():
        run(sshv4v + ['test', '!', '-r', '/var/run/sync-client-daemon.pid'],
             timeout=10, host=host)
    print 'HEADLINE: stopping sync-client-daemon'
    try:
        retry(test_missing, "wait for sync-client-daemon pid to disappear", catch=[
                SubprocessError], timeout=20)
        print 'HEADLINE: cleanly stopped old sync-client-daemon'
    except Exception:
        print 'HEADLINE: clean shutdown of old sync-client-daemon failed; killing it'
        current = run(sshv4v + ['pgrep', '-f', 'sync-client-daemon'],
                      host=host, word_split=True)
        if current:
            print 'HEADLINE: current pids', current
            run(sshv4v + ['pkill', '-9', '-f', 
                          'sync-client-daemon'], host=host)
        else:
            print 'HEADLINE: no current pids'
        run(sshv4v + ['rm', '-f', '/var/run/sync-client-daemon.pid'], host=host)
    
    print "HEADLINE: running fresh sync-client-daemon"
    dbus_var = 'DBUS_SYSTEM_BUS_ADDRESS=tcp:family=v4v,host=1.0.0.0,port=5556'
    def dolog(text):
        for line in text.splitlines():
            if line:
                print 'INFO: log', line
        if 'curl exit code 60' in text: # peer certifcate cannot be authenticated
            raise SSLCertificateProblem()
    run(sshv4v + ['ifup', 'eth0'], host=host) # workaround XC-9212
    out = run(sshv4v +
         [dbus_var, 'LD_PRELOAD=/usr/lib/libv4v-1.0.so.0',
          'sync-client-daemon', '--debug', '--foreground', '--once'],
         output_callback=dolog, error_callback=dolog, 
         timeout=timeout, host=host)
    print 'HEADLINE: sync-client-daemon completed'

def get_oracle_environment():
    """Read the oracle installation and detect environment"""
    env = {}
    oracle_conf = readfile(ORACLE_ENVIRONMENT_FILE, host = SYNCXT_SERVER)
    for line in oracle_conf.split('\n'):
        matchobj = match('^export ([A-Z_]+)=(.*)$', line)
        if matchobj is None:
            continue
        out = matchobj.group(2).replace('$PATH', environ['PATH'])
        if '$ORACLE_HOME' in out:
            out = out.replace('$ORACLE_HOME', env['ORACLE_HOME'])
        if out[0] == '`':
            out = run([out[1:-1]], host=SYNCXT_SERVER).replace(
                '\n', '').replace("'", '')
        env[matchobj.group(1)] = out
    return env

def get_vms_with_disks(cli, diskuuids):
    vm_sets = []
    for diskuuid in diskuuids:
        vm_sets.append(set([vm['vm_uuid']
                           for vm in cli('list-vms', '--disk', diskuuid)]))
    return sorted(set.intersection(*vm_sets))

class NfsBroken(Exception):
    pass

def ensure_nfs_works(path, host):            
    def verify():
        if isfile(path, host=host) or islink(path, host=host):
            return True
        run(['/etc/init.d/autofs', 'restart'], host=host)
        raise NfsBroken(path, host)
    retry(verify, 'ensure nfs_works')


def ensure_ssl_files_exist():
    """Create SSL key"""
    orun = specify(host=SYNCXT_SERVER)
    orun(['mkdir', '-p', SERVER_BASE])
    for cert, key in [(SSL_CERT, SSL_KEY), (SSL_ALT_CERT, SSL_ALT_KEY)]:
        if isfile(cert, host=SYNCXT_SERVER) and isfile(key, host=SYNCXT_SERVER):
            continue
        print 'HEADLINE: creating server SSL key and self-signed certificate'
        orun(['openssl', 'genrsa', '-out', key, '1024']) 
        csrfile = maketempfile(SYNCXT_SERVER, 'csr')
        try:
            orun(['openssl', 'req', '-new', '-key', key, '-out', csrfile,
                  '-subj', '/CN='+SYNCXT_SERVER])
            orun(['openssl', 'x509', '-in', csrfile, '-out', cert, 
                  '-req', '-signkey', key, '-days', '365'])
        finally:
            orun(['rm', '-f', csrfile])
        orun(['openssl', 'verify', '-CAfile', cert, cert])
        for req in [cert, key]:
            orun(['chown', apache_user(), req])
            orun(['chmod', '777', req])



def create_oracle_database(server, orun, name, portdir):
    """Create oracle database"""
    db_admin_config = join(portdir, 'sync.db_admin_conf')
    writefile(db_admin_config,
              "[database]\n"
              "oracle_server = %(oracle_server)s\n"
              "sys_password = %(sys_password)s\n"
              "sync_owner_user = %(name)s_owner\n"
              "sync_owner_password = %(name)s_owner\n"
              "sync_admin_user = %(name)s_admin\n"
              "sync_admin_password = %(name)s_admin\n"
              "sync_license_user = %(name)s_license\n"
              "sync_license_password = %(name)s_license\n"
              "sync_server_user = %(name)s_server\n"
              "sync_server_password = %(name)s_server\n" %
              {"oracle_server": ORACLE_SERVER, "name": name,
               "sys_password": ORACLE_SERVER_SYSTEM_PASSWORD},
              host=server)
    orun(['./sync-database', '-c', db_admin_config, 'destroy',
               '--force'])
    orun(['./sync-database', '-c', db_admin_config, 'install'])
        
def port_directory(port):
    return join(SERVER_BASE, 'port%d' % port)

def server_is_centos(server):
    return isdir('/etc/httpd', host=server)

def ensure_apache_ready(server):
    """Generate apache configuration and ensure apache running"""
    def required_apache_conf(port, apache_user):
        """Returns an Apache config fragment for a server running on port."""
        serverdir = port_directory(port)
        conf = ""
        conf += 'Listen ' + str(port) + '\n'
        conf += '<VirtualHost *:' + str(port) + '>\n'
        conf += '  CustomLog '+serverdir+'/access.log common\n'
        conf += '  ErrorLog '+serverdir+'/error.log\n'
        conf += '  SSLEngine on\n'
        conf += '  WSGIDaemonProcess synchronizer'+str(port)+' user='
        conf += apache_user + ' processes=2 threads=10\n'
        conf += '  WSGIProcessGroup synchronizer'+str(port)+'\n'
        conf += '  <Location />\n'
        conf += '     AuthType Digest\n'
        conf += '     AuthName "synchronizer"\n'
        conf += '     AuthDigestProvider wsgi\n'
        conf += '     WSGIAuthUserScript '+serverdir+'/auth_wsgi.py\n'
        conf += '     Require valid-user\n'
        conf += '  </Location>\n'
        conf += '  WSGIScriptAlias /disk '+serverdir+'/disk_wsgi.py\n'
        conf += '  WSGIScriptAlias /repo '+serverdir+'/repo_wsgi.py\n'
        conf += '  WSGIScriptAlias / '+serverdir +'/server_wsgi.py\n'
        conf += '</VirtualHost>\n\n'
        return conf

    apache_site_file = APACHE_SITE_FILE_CENTOS if server_is_centos(server) else APACHE_SITE_FILE_DEBIAN
    modules_conf_file = join(APACHE_CONF_DIR_CENTOS, 'conf.d', '00modules.conf')

    serverdirs = [ port_directory(p) for p in APACHE_PORTS ]
    logfiles = [ join(port_directory(p), 'access.log') for p in APACHE_PORTS ] + \
               [ join(port_directory(p), 'error.log') for p in APACHE_PORTS ]

    apache_user = APACHE_USER_CENTOS if server_is_centos(SYNCXT_SERVER) else APACHE_USER_DEBIAN
    conf = 'SSLCertificateFile '+SSL_CERT+'\n'
    conf += 'SSLCertificateKeyfile '+SSL_KEY+'\n'
    conf += str.join('\n', [ required_apache_conf(p, apache_user) for p in APACHE_PORTS ])

    # base Sync config:
    if isfile(apache_site_file, host=server):
        current = readfile(apache_site_file, host=server)
    else:
        current = None
    run(['mkdir', '-p'] + serverdirs, host=server)
    run(['touch'] + logfiles, host=server)
    run(['chown', apache_user] + logfiles, host=server, user='root')

    if not server_is_centos(server):
        run(['ln', '-sf', '../sites-available/synchronizer',
             '/etc/apache2/sites-enabled'], host=server)

    # modules required for Sync to work:
    modconf = ""
    current_modconf = ""
    if server_is_centos(server):
        modconf = "LoadModule wsgi_module modules/mod_wsgi.so\n"
        modconf += "LoadModule ssl_module modules/mod_ssl.so\n"
        modconf += "WSGISocketPrefix /var/run/wsgi\n"
        if isfile(modules_conf_file, host=server):
            current_modconf = readfile(modules_conf_file, host=server)
        else:
            current_modconf = None
    else:
        for mod in ['wsgi', 'ssl', 'auth_digest', 'authz_user']:
            if 'auth' not in mod:
                run(['ln', '-sf', '../mods-available/'+mod+'.conf',
                     '/etc/apache2/mods-enabled'], host=server)
            run(['ln', '-sf', '../mods-available/'+mod+'.load',
                 '/etc/apache2/mods-enabled'], host=server)

    apache_service_name = 'httpd' if server_is_centos(server) else 'apache2'
    if current != conf or modconf != current_modconf:
        writefile(apache_site_file, conf, host=server)
        if server_is_centos(server):
            writefile(modules_conf_file, modconf, host=server)
        print 'HEADLINE: restarting server'
        run(['/etc/init.d/%s' % apache_service_name, 'restart'], host=server)
    else:
        status, code = run(['/etc/init.d/%s' % apache_service_name, 'status'], host=server,
                           ignore_failure=True)
        if 'NOT running' in status or 'stopped' in status or 'dead' in status:
            print 'HEADLINE: starting apache server'
            run(['/etc/init.d/%s' % apache_service_name, 'start'], host=server)
        else:
            print 'HEADLINE: apache already running'

def do_logging(portdir, filename, result_id, dut, host, start):
    """Log all writes to filename on host, adding to database 
    as result_id is not None"""
    fullname = join(portdir, filename)
    run(['pkill', '-9', '-f', 'tail.*'+fullname], host=host, 
        ignore_failure=True)
    with StdoutFilter(start=start) as logger:
        with RecordTest(result_id=result_id, record_finish=False, 
                        stdout_filter= logger):
            def got_output(data):
                """record output"""
                for line in data.splitlines():
                    message = 'apache ' + filename + ' ' + line
                    print 'INFO:', message
            run(['tail', '-n0', '-F', fullname], timeout=24*60*60*365,
                host=host, output_callback=got_output, ignore_failure=True)

def get_apache_port(server, dut):
    """Return an apache port and port directory for dut"""
    print 'INFO: checking for ports on', server
    dutpat = dut+'\n'
    # first, reuse a locked port directory with dut.txt containing
    # our dut name
    for port in APACHE_PORTS:
        portdir = port_directory(port)            
        lockdir = join(portdir, 'lock')
        infofile = join(portdir, 'dut.txt')
        try:
            dutc = readfile(infofile, host=server)
        except SubprocessError:
            print 'INFO: port', port, 'is not assigned to a device'
        else:
            if dutc == dutpat:
                if isdir(lockdir, host=server):
                    print 'HEADLINE: reusing dut installation on port', port
                else:
                    print 'HEADLINE: port', port, 'is assigned but unlocked'
                    continue
                return port, portdir
            else:
                print 'PORTS: port', port, 'is used for', dutc.split()[0]
                continue
    server_user = apache_user()
    for port in APACHE_PORTS:
        portdir = port_directory(port)
        run(['mkdir', '-p', portdir], host=server, user='root')
        run(['chown', '-R', server_user, portdir], host=server, user='root')
        lockdir = join(portdir, 'lock')
        infofile = join(portdir, 'dut.txt')
        _, code = run(['mkdir', lockdir], host=server, user='root',
                      ignore_failure=True)
        if code != 0:
            print 'HEADLINE: unable to mkdir', lockdir, 
            print 'so trying next port'
            continue

        print 'INFO: made lock directory', lockdir
        run(['chown', '-R', server_user, lockdir], host=server, user='root')
        port = port
        lockdir = lockdir
        writefile(join(portdir, 'host.txt'),
                  'Automation host %s pid %d time %s' % (
                gethostname(), getpid(), asctime()), host=server, user=server_user, via_root=True)
        writefile(infofile, dutpat, host=server, user=server_user, via_root=True)
        print 'HEADLINE: allocated apache port', port, 'for', dut
        return port, portdir
    raise OutOfApachePorts(server)
    
class LogReader:
    """Allocate apache virtual host ports"""
    def __init__(self, server, result_id, dut, portdir):
        self.server = server
        self.result_id = result_id
        self.logprocesses = []
        self.portdir = portdir
        self.dut = dut
    def __enter__(self):
        for logf in ['access.log',  'error.log']:
            args = (self.portdir, logf, self.result_id, self.dut, self.server,
                    getattr(sys.stdout, 'start'))
            process = Process(target=do_logging, args=args)
            process.start()
            self.logprocesses.append(process)
    def __exit__(self, *_):
        for process in self.logprocesses:
            process.terminate()
            process.join()

class MountedSyncvmVhd:
    """Mount syncvm vhd on a temporary directory in dom0"""
    def __init__(self, dut):
        self.dut = dut
    def __enter__(self):
        # First shut down any running vms using syncvm vhd
        orun = specify(host=self.dut)
        for vm in orun(['xec', 'list-vms']).splitlines():
            state = orun(['xec-vm', '-o', vm, 'get', 'state']).rstrip()
            ldout = orun(['xec-vm', '-o', vm, 'list-disks'])
            for disk in ldout.splitlines():
                if disk == '':
                    continue
                disk_num = disk.split('/')[-1]
                path = orun(['xec-vm', '-o', vm, '-k', disk_num,
                             'get', 'phys-path']).rstrip()
                if path == SYNCVM_VHD:
                    if state == 'running':
                        print 'HEADLINE: shutting down vm', vm
                        orun(['xec-vm', '-o', vm, 'shutdown'])
                        state = None
                    vm_uuid = orun(['xec-vm', '-o', vm, 'get',
                                    'uuid']).rstrip()
                    orun(['db-rm', '/vm/' + vm_uuid + '/config/disk/' +
                          disk_num + '/sha1sum'])

        self.device = orun(['tap-ctl', 'create', '-a',
                            'vhd:' + SYNCVM_VHD]).rstrip()
        try:
            mountdir = maketempdirectory(host=self.dut)
            orun(['mount', self.device, mountdir])
            return mountdir
        except:
            orun(['tap-ctl', 'destroy', '-d', self.device])
            raise
    def __exit__(self, *_):
        orun = specify(host=self.dut)
        orun(['umount', self.device])
        orun(['tap-ctl', 'destroy', '-d', self.device])

def extract_xclicimp(targetd, build, branch):
    """Extract xclicimp"""
    run(['mkdir', '-p', targetd], host=SYNCXT_SERVER)
    src = XCLICIMPRPM_GLOB % (branch, build)
    run(['sh', '-c', 'rpm2cpio %s | cpio -id' % src],
         host=SYNCXT_SERVER, cwd=targetd, shell=True)
    dst =targetd+'/usr/bin/xclicimp'
    print 'HEADLINE: extract xclicimp from %s to %s:%s' % (
        src, SYNCXT_SERVER, dst)
    return dst  

def deploy_code(dut, build, source_directory, portdir):
    if source_directory:
        srchost = None
        for repo in SERVER_REPOS:
            print 'INFO: copying', source_directory+'/'+repo, 'to', ('root', SYNCXT_SERVER, portdir)
            copy_tree(source_directory+'/'+repo,
                      ('root', SYNCXT_SERVER, portdir), ['.git'])
        xclicimpd = portdir+'/xclicensing/offline/xclicimp'
        if not isfile(xclicimpd+'/configure', host=SYNCXT_SERVER):
            run(['./autogen.sh'], host=SYNCXT_SERVER, cwd=xclicimpd, shell=True)
        if not isfile(xclicimpd+'/Makefile', host=SYNCXT_SERVER):
            run(['./configure', 
                 '--with-liboci=/u01/app/oracle/product/11.2.0/xe'],
                host=SYNCXT_SERVER, cwd=xclicimpd, shell=True)
        run(['make'], host=SYNCXT_SERVER, cwd=xclicimpd, echo=True)
        xclicimpbin = xclicimpd + '/src/xclicimp'
        if not isfile(xclicimpbin, host=SYNCXT_SERVER):
            raise NoXcLicImpBinary(xclicimpd, SYNCXT_SERVER)
        print 'HEADLINE: getting sync-client onto target machine'
        run(['mkdir', '-p', STAGE_DIR], host=dut)
        with DepositDirectories(dut, STAGE_DIR, source_directory, 
                                None, ['sync-client']):
            with MountedSyncvmVhd(dut) as mountdir:
                run(['sh', '-c', ' '.join(['cp',
                     STAGE_DIR+'/sync-client/sync_client/*.py', 
                     mountdir +
                     '/usr/lib/python2.?/site-packages/sync_client'])],
                    host=dut, shell=True)
                run(['cp', STAGE_DIR+'/sync-client/sync-client-daemon', 
                     mountdir + '/usr/bin/sync-client-daemon'], 
                    host=dut, shell=True)
                run(['cp', STAGE_DIR+'/sync-client/sync-client', 
                     mountdir + '/usr/bin/sync-client'], 
                    host=dut, shell=True)
                # XXX HACK: copy in vhd-util for now until it is in the syncvm fs
                run(['cp', '/usr/sbin/vhd-util',
                     mountdir + '/usr/sbin'], host=dut, shell=True)
                run(['cp', '/usr/lib/libvhd.so.1.0.0', 
                     mountdir + '/usr/lib'], host=dut, shell=True)
        srcdir = source_directory
    else:
        if build is None:
            _, branch = try_get_build_number_branch(dut)
        else:
            branch = extract_branch(build)

        print 'INFO: checking out syncXT from', build
        for repo in SERVER_REPOS:
            tdir = join(portdir, repo)
            if not isdir(tdir+'/.git', host=SYNCXT_SERVER):
                run(['rm', '-rf', tdir], host=SYNCXT_SERVER)
            if not isdir(tdir, host=SYNCXT_SERVER):
                print 'INFO: cloning', GIT_REPOSITORY_URL_FORMAT % (repo+'.git')
                git_start_time = time()
                run(['git', 'clone', GIT_REPOSITORY_URL_FORMAT % 
                     (repo+'.git')], cwd=portdir, host=SYNCXT_SERVER)
                print 'INFO: git clone took', time() - git_start_time, 'seconds'
            else:
                print 'INFO: fetching', repo
                git_start_time = time()
                run(['git', 'fetch'], host=SYNCXT_SERVER, cwd=tdir)
                print 'INFO: git fetch took', time() - git_start_time, 'seconds'
            git_start_time = time()
            run(['git', 'checkout', '-f', build], cwd=tdir, host=SYNCXT_SERVER)
            print 'INFO: git checkout took', time() - git_start_time, 'seconds'
        xclicimpbin = extract_xclicimp(portdir+'/xclicimp', build, branch)
        srcdir = portdir
        srchost = SYNCXT_SERVER
    if not isfile(xclicimpbin, host=SYNCXT_SERVER):
        raise NoXcLicImpBinary(xclicimpbin, SYNCXT_SERVER)
    return source_directory, srchost, xclicimpbin

def read_git(srcdir, host, rev='HEAD'):
    return run(['git', 'rev-parse', rev], cwd=srcdir, host=host, 
              word_split=True)[0][:16]

def get_version(srcdir, host):
    """Get version of code in host:srcdir, including local diffs"""
    rev = read_git(srcdir, host)
    diffs = run(['git', 'diff'], cwd=srcdir, host=host) + \
            run(['git', 'diff', '--cached'], cwd=srcdir, host=host)

    if diffs.split() == []:
        diffhash = None
    else:
        diffhash = sha256(diffs).hexdigest()
    return rev, diffhash

def check_database_for_dut(cli, dut):
    """Does this database already have an entry for dut?"""
    try:
        have_dut = len([x for x in cli('list-devices') if 
                        x['device_name'] == dut])
        print 'HEADLINE: dut', \
            'found in' if have_dut else 'missing from', \
            'database'
        return True
    except SubprocessError:
        print 'INFO: unable to communicate with database'
        return False

def read_database_version(portdir):
    """Return the database_version for portdir, or None"""
    database_version_file = join(portdir, 'database_version.txt')
    try:
        return eval(readfile(database_version_file, host=SYNCXT_SERVER))
    except SubprocessError:
        print 'INFO: unable to read', database_version_file
    except ValueError:
        print 'INFO: unable to parse', database_version_file

def calculate_database_version(source_directory, portdir, build):
    """calculate database version for source_directory and portdir"""
    if source_directory:
        return get_version(join(source_directory, 'sync-database'), None)
    else:
        print 'HEADLINE: portdir %r' % (portdir)
        revhash = read_git(join(portdir, 'sync-database'), SYNCXT_SERVER, 
                           build if build else 'HEAD')
        return revhash, None
    
def prepare_database(cli, orun, name, dut, portdir, source_directory, 
                     xclicimpbin, update_details=(None,None), build=None, 
                     preserve_database=False, template=False, shared_vhd=False,
                     vmconfig=DEFAULT_VMCONFIG):
    """Populate sync-db for our test as necessary. Idempotent."""
    db_working = check_database_for_dut(cli, dut)
    curv = read_database_version(portdir)    
    dbv = calculate_database_version(source_directory, portdir, build)
    print 'HEADLINE: database version wanted', dbv, 'have', curv
    if (not preserve_database) or dbv != curv or not db_working:
        with Timed('creating oracle database'):
            create_oracle_database(SYNCXT_SERVER, orun, name, portdir)
    else:
        print 'HEADLINE: reusing database'
    writefile( join(portdir, 'database_version.txt'), 
               repr(dbv)+'\n', host=SYNCXT_SERVER)

    # Dummy repository for now...
    build, branch =update_details
    if build or branch:
        if branch and build is None:
            build_doc = get_autotest().builds.find_one(
                {'branch':branch},
                sort=[('build_time', DESCENDING)])
            build = build_doc['_id']
        if branch is None:
            build_doc = get_autotest().builds.find_one(
                {'_id':build},
                sort=[('build_time', DESCENDING)])
            branch = build_doc['branch']
        if build is None or branch is None:
            raise NoUpdateFor(update_details)
        update = UPDATE_PATH % (branch, build,
                                get_build_info(branch, build)['ota-update'])
        ensure_nfs_works(update, SYNCXT_SERVER)
        print 'HEADLINE: deploying update', update
        if not [x for x in cli('list-repos') if x['file_path'] == update]:
            cli('add-repo', '--release', branch, '--build', 
                build, update)
        mrepos = [x for x in cli('list-repos') if x['file_path'] == update]
        assert len(mrepos) == 1, mrepos
        repouuid = mrepos[0]['repo_uuid']
        repohash = cli('show-repo', repouuid)['file_hash']
        repoargs = ['-r', repouuid]
    else:
        repoargs = []
    mydev = [x for x in cli('list-devices') if x['device_name'] == dut]
    set_molc(xclicimpbin, 1, name, cli)
    if len(mydev) == 0:
        args=['add-device',
              '-c', 'sync-client:use-pseudorandomness:true',
              '-c', 'xenmgr:vm-creation-allowed:true',
              '-c', 'xenmgr:vm-deletion-allowed:false']+repoargs+[dut]
        deviceuuid = cli(*args)
    else:
        if len(mydev) > 1:
            for dev in mydev[1:]:
                cli('remove-device', '-c', dev['device_uuid'])
        deviceuuid = mydev[0]['device_uuid']
    secret = cli('show-device-secret', deviceuuid)
    disklist = cli('list-disks')
    print 'INFO: disks=', repr(disklist)
    disks_by_path = dict( [(x['file_path'], x) for x in disklist])
    diskuuids = []
    for disk, shared in [
        #('/home/xc_vhds/dev_vhds/sans_pvtools/st_xp.vhd',shared_vhd),
        ('/home/xc_vhds/dev_vhds/sans_pvtools/st_xpenc'
         '%s.aes-xts-plain,512.vhd' % (
                '-shared' if shared_vhd else ''),shared_vhd),
        #('/home/xc_vhds/dev_vhds/sans_pvtools/st_win7.vhd',False),
        ('/home/xc_dist/distrib/linux/ubuntu/12.04/ubuntu-12.04-mini-i386.iso',
         False)]:
        if disk in disks_by_path:
            diskuuids.append(disks_by_path[disk]['disk_uuid'])
        else:
            ensure_nfs_works(disk, SYNCXT_SERVER)

            args = ['add-disk']
            if shared: 
                args += ['--shared']
            args += ['disk name', disk]
            if exists(disk+ '.sha256'):
                args += ['--hash', file(disk+'.sha256', 'r').read().rstrip()]
            pfile = disk + ".key"
            cryptofile = pfile if exists(pfile) else None
            if cryptofile:
                print 'NOTE: using key from', cryptofile
                key = file(cryptofile, 'r').read()
                key_length = len(key)*8
                print 'INFO: key length', key_length
                if key_length != DISK_ENCRYPTION_KEY_LENGTH:
                    raise UnexpectedDiskEncrpytionKeyLength(
                        'have=', key_length,
                        'require=', DISK_ENCRYPTION_KEY_LENGTH)
                args += ['-k', ''.join(['%02x' % ord(byte) for byte in key])]
            else:
                print 'INFO: no key for disk %s' % disk
            diskuuids.append(cli(*args))
    vmuuid = None
    matching_vms = get_vms_with_disks(cli, diskuuids)
    if len(matching_vms) == 0:
        args = ['add-vm'] + vmconfig + ['vm name']
        for diskuuid in diskuuids:
            args += ['-d', diskuuid]
        cli(*args)
    else:
        # already have at least one VM; remove any extras
        for vmuuid in matching_vms[1:]:
            print 'INFO: removing VM', vmuuid
            vminsts = cli('list-vm-instances', '-v', vmuuid)
            print 'INFO: instances ' + repr( vminsts)
            for vminst in vminsts:
                print 'INFO: removing', vminst
                cli('purge-vm-instance', vminst['vm_instance_uuid'])
            cli('remove-vm', vmuuid)
        vmuuuid = matching_vms[0]
    matching_vms2 = get_vms_with_disks(cli, diskuuids)
    vminsts = cli('list-vm-instances', '--device', deviceuuid)
    for vminst in vminsts:
        if vminst['vm_uuid'] != vmuuid:
            cli('purge-vm-instance', vminst['vm_instance_uuid'])
    matching_vms3 = get_vms_with_disks(cli, diskuuids)
    print 'INFO: VMs now',matching_vms3, 'expected', [vmuuid]
    assert len(matching_vms3) == 1
    vmuuid = matching_vms3[0]
    vminsts = cli('list-vm-instances', '-v', vmuuid)
    if len(vminsts) == 0:
        vmrinsts = cli('list-vm-instances', '--removed', '-v', vmuuid)
        if len(vmrinsts) > 0:
            cli('readd-vm-instance', vmrinsts[0]['vm_instance_uuid'])
        else:
            cli('add-vm-instance', deviceuuid, vmuuid, VM_NAME)

    for vminst in vminsts[1:]:
        cli('purge-vm-instance', vminst['vm_instance_uuid'])
    vminsts2 = cli('list-vm-instances', '-v', vmuuid)
    assert len(vminsts2) == 1
    print 'INFO: disks %r' % (cli('list-disks'))
    print 'INFO: repos %r' % (cli('list-repos'))
    for vm in cli('list-vms'):
        print 'INFO: vm %r %r' % (vm, cli('show-vm', vm['vm_uuid']))
    print 'INFO: vm instances %r' % (cli('list-vm-instances'))

    return deviceuuid, secret, vmuuid, vminsts2[0]['vm_instance_uuid'], diskuuids


class SubTest:
    """base class for subtests of this module"""
    def configure(self, dut, build):
        """Run at start of test"""
        pass
    def prepare(self, base_argd):
        """prepare the database, given a default set of keyword
        arguments for prepare_database"""
        return prepare_database(**base_argd)
    def execute(self, do_sync, **_):
        """Run the main test case; do_sync is a callback
        that causes sync client to run"""
        do_sync()

class EncryptedVmDownload(SubTest):
    """Minimal subtest"""

class BootVmTest(SubTest):
    def execute(self, do_sync, dut, **_):
        do_sync()
        start_vm(dut, VM_NAME, may_already_be_running=True)

class TemplateBootTest(BootVmTest):
    def prepare(self, base_argd):
        """prepare the database, given a default set of keyword
        arguments for prepare_database"""
        return prepare_database(vmconfig=['-c', 'vmparam:template:new-vm'], **base_argd)

class InvalidDeviceSecretTest(SubTest):
    def execute(self, do_sync, **_):
        try:
            do_sync(specified_secret='fish', timeout=60)
        except TimeoutError, exc:
            if 'HTTP response code 401' not in exc.args[4]:
                raise BadSecretAccepted()
        else:
            raise BadSecretAccepted()

class RemovedDeviceTest(SubTest):
    def execute(self, do_sync, cli, deviceuuid, **_):
        try:
            cli('remove-device', '-c', deviceuuid)
            do_sync(timeout=60)
        except TimeoutError, exc:
            if 'HTTP response code 401' not in exc.args[4]:
                raise BadSecretAccepted()
        else:
            raise BadSecretAccepted()

class BadCATest(SubTest):
    def execute(self, do_sync, **_):
        try:
            do_sync(cafile=SSL_ALT_CERT)
        except SSLCertificateProblem:
            pass
        else:
            raise BadCaAccepted()

class ChangeMemoryTest(SubTest):
    def execute(self, do_sync, dut, vmuuid, cli, **_):
        do_sync()
        start_vm(dut, VM_NAME, may_already_be_running=True)
        for mem in [1400, 1024]:
            print 'INFO: setting memory size to', mem
            cli('modify-vm-config', vmuuid, '-c', 'vm:memory:'+str(mem))
            do_sync()
            newmem = run(['xec-vm', '-n', VM_NAME, 'get', 'memory'],
                         host=dut, word_split = True)
            if newmem != [str(mem)]:
                raise VmNotModifiedAsExpected(newmem, [str(mem)], 
                                              VM_NAME, dut)
            print 'HEADLINE: VM correctly changed memory config'
            reboot_windows_vm(dut, VM_NAME)
            vm_address = wait_for_windows(dut, VM_NAME)
            memread = call_exec_daemon('getMemory', host=vm_address,
                                       timeout=600)
            if ((mem-memread)>MEMORY_REPORTED_DIFFERENCE or 
                memread > mem):
                raise MemoryNotInExpectedRange(
                    'wanted=', mem, 'have=', memread, 
                    'slack=', MEMORY_REPORTED_DIFFERENCE,
                    dut, vm_address, VM_NAME)

class RenameVMTest(SubTest):
    def execute(self, do_sync, dut, vminstanceuuid, cli, **_):
        do_sync()
        find_domain(dut, VM_NAME)
        cli('modify-vm-instance-name', vminstanceuuid, 'vm_renamed')
        do_sync()
        find_domain(dut, 'vm_renamed')

class TransferDiskCommon(SubTest):
    def prepare(self, base_argd):
        return prepare_database(shared_vhd=self.shared, **base_argd)
    def execute(self, do_sync, dut, cli, vminstanceuuid, vmuuid, diskuuids,
                deviceuuid, **_):
        do_sync()
        start_vm(dut, VM_NAME, may_already_be_running=True)
        vm_address = wait_for_windows(dut, VM_NAME)
        call_exec_daemon('createFile', [MARKER_FILE, MARKER_DATA],
                         host=vm_address)
        data = call_exec_daemon('readFile', [MARKER_FILE], 
                                host=vm_address)
        assert data == MARKER_DATA
        shutdown_windows(vm_address)
        cli('purge-vm-instance', vminstanceuuid)
        cli('remove-vm', vmuuid)
        vm2uuid = cli('add-vm', '-c', 'vmparam:template:new-vm',
            '-d', diskuuids[0], '-d', diskuuids[1], 'vm2')
        cli('add-vm-instance', deviceuuid, vm2uuid, ALT_VM_NAME)
        print 'INFO: existing /storage/sync:', \
            repr(run(['ls', '-lR', '/storage/sync'], host=dut))
        do_sync()
        start_vm(dut, ALT_VM_NAME, may_already_be_running=True)
        vm2_address = wait_for_windows(dut, ALT_VM_NAME)
        if self.shared:
            data2 = call_exec_daemon('readFile', [MARKER_FILE],
                                     host=vm2_address)
            assert data2 == MARKER_DATA
        else:
            present = call_exec_daemon('fileExists', [MARKER_FILE],
                                       host=vm2_address)
            print 'INFO: marker file', MARKER_FILE, 'is', \
               'PRESENT' if present else 'MISSING', 'on', vm2_address
            if present:
                raise VmNotResetAsExpected(vm2_address, dut, MARKER_FILE)


class TransferSharedDiskTest(TransferDiskCommon):
    shared = True

class TransferNonSharedDiskTest(TransferDiskCommon):
    shared = False

class GracefulDestroyTest(SubTest):
    def execute(self, do_sync, dut, vminstanceuuid, cli, **_):
        do_sync()
        start_vm(dut, VM_NAME, may_already_be_running=True)
        vm_address_pre = wait_for_windows(dut, VM_NAME)
        print 'INFO: target VM is up at', vm_address_pre
        cli('remove-vm-instance', vminstanceuuid)
        print 'INFO: marking VM to be graceful_delete on shutdown'
        do_sync()
        vm_address_post = wait_for_windows(dut, VM_NAME)
        print 'INFO: gracefully removed VM still running'
        print 'INFO: 20s sleep for inspection'
        sleep(20)
        print 'INFO: shutting down VM'
        shutdown_windows(vm_address_post)
        wait_for_vm_to_stop(dut, VM_NAME)
        print 'INFO: gracefully removed VM should now be locked'
        print 'INFO: 20s sleep for inspection'
        sleep(20)
        do_sync()
        vms = list_vms(dut)
        matching = [vm for vm in vms if vm['name'] == VM_NAME]
        if len( matching) > 0:
            raise VmNotRemovedAsExpected(dut, VM_NAME)

class OTAUpdateTest(SubTest):
    def configure(self, dut, build):
        self.target_build = build
        self.latest_release = latest_release()
        print 'INFO: latest release', self.latest_release
        build = get_build(dut)
        print 'HEADLINE: currently have', build, 'on', dut
        if build != self.latest_release['build']:
            print 'HEADLINE: installing', self.latest_release['build']
            pxe_install_xc(dut, release='latest', upgrade=False)
        else:
            print 'HEADLINE: keeping current install'
    def prepare(self, base_argd):
        branch = '-'.join(self.target_build.split('-')[3:])
        self.update = self.target_build, branch
        print 'HEADLINE: testing OTA from', self.latest_release['build'], \
            'to', self.update
        dut = base_argd['dut']
        with FilesystemWriteAccess(dut, '/'):
            writefile('/config/repo-cert.conf', "ALLOW_DEV_REPO_CERT='true'\n",
                       host=dut)
        return prepare_database(update_details=self.update, **base_argd)
    def execute(self, do_sync, dut, **_):
        do_sync()
        print 'HEADLINE: client should now do an OTA from', \
            self.latest_release, 'to', self.update
        with time_limit(3600, 'wait for upgrade'):
            while True:
                build = get_build(dut)
                print 'HEADLINE: build detected as', build
                if build == self.update[0]:
                    break
                sleep(5)

# This should go somewhere central, and be used by all tests as they start, to make sure it's at least 1 :
def set_molc(xclicimpbin, molc, name, cli):
    """Run xclicimp on the server."""
    print "INFO: setting Max Offline License Count to", molc
    # it will look for *.lic in the specified directory
    listing, exit_code = run(["ls", "-R", LICENSE_DIRECTORY], ignore_failure=True)
    if exit_code != 0:
        print 'INFO: copying license files from', LICENSE_SETS, 'to', LICENSE_DIRECTORY_PARENT, 'on', SYNCXT_SERVER
        run(['scp', '-r', LICENSE_SETS,
            'root' + '@' + SYNCXT_SERVER + ':' + LICENSE_DIRECTORY_PARENT])
    dest = LICENSE_DIRECTORY_FORMAT % molc
    assert isdir(dest, host=SYNCXT_SERVER), (dest, 'directory exists on',  SYNCXT_SERVER)
    files = run(['ls', dest], host=SYNCXT_SERVER)
    print 'INFO: licensing directory', dest, 'contains', repr(files)
    run([xclicimpbin,
         "-s", ORACLE_SERVER,
         "-u", name+'_license',
         "-p", name+'_license',
         "-d", dest], host=SYNCXT_SERVER,
        env=get_oracle_environment())
    license_state= cli('show-licensing')
    print 'INFO: licensing=%r' % (license_state)
    if license_state.get('num_offline_licenses') != molc:
        raise UnableToSetMolc(data, molc)

def add_device(name, cli):
    try:
        deviceuuid = cli('add-device', name)
    except SubprocessError:
        deviceuuid = None
    else:
        print 'HEALDINE: device added', cli('show-device', deviceuuid)
    return deviceuuid

def remove_device(uuid, cli):
    cli('remove-device', '-c', uuid)

class OfflineLicensingTest(SubTest):
    def configure(self, dut, build):
        pass
            
    # def prepare(self, base_argd):
        #pass
        # dut = base_argd['dut']
        # with FilesystemWriteAccess(dut, '/'):
        #     writefile('/config/repo-cert.conf', "ALLOW_DEV_REPO_CERT='true'\n",
        #                host=dut)
        # return prepare_database(update_details=self.update, **base_argd)

    def execute(self, cli, do_sync, dut, xclicimpbin, name, **_):
        # todo: list all machines currently on server, and remove them all, so we have a known starting point
        print "INFO: looking for old device registrations to remove"
        for device in cli('list-devices'):
            print "INFO: removing pre-existing device", device
            remove_device(device['device_uuid'], cli)
        for n_licenses in [1, 2, 3, 2, 1, 0]:
            print "HEADLINE: testing with", n_licenses, "licenses"
            set_molc(xclicimpbin, n_licenses, name, cli)
            devices = [dut, 'extra-1', 'extra-2', 'extra-3']
            device_uuids = {}
            devices_added = 0
            for device in devices:
                print "HEADLINE: trying to add device", device, "with", n_licenses, "licenses available"
                new_device_uuid = add_device(device, cli)
                device_uuids[device] = new_device_uuid
                if new_device_uuid is not None:
                    devices_added += 1
                print "INFO: uuid for device", device, "is", new_device_uuid, "; ", devices_added, "now added"
            if devices_added > n_licenses:
                raise LicenceTooManyMachinesAdded('allowed', n_licenses, 'allocated', devices_added)
            if devices_added < n_licenses:
                raise LicenceNotEnoughManyMachinesAdded('allowed', n_licenses, 'allocated', devices_added)
            main_device_uuid = device_uuids[dut]
            if main_device_uuid is not None:
                current_secret = cli('show-device-secret', main_device_uuid)
                do_sync(specified_secret=current_secret, 
                        specified_deviceuuid=main_device_uuid)
            else:
                assert n_licenses == 0
            # ask xenmgr for the flag as seen from its end
            device_claims_to_be_licensed = (['true'] == 
                                            run(['xec', '-o', '/host', 'get', 'is-licensed'], host=dut,
                                                word_split=True))
            if not device_claims_to_be_licensed:
                raise UnLicensedWhenItShouldHaveBeenLicensed(n_licenses)
            # todo: maybe look at the expiry date
            for device in devices:
                print "INFO: trying to remove device", device, "with", n_licenses, "licenses available"
                if device_uuids[device] is not None:
                    remove_device(device_uuids[device], cli)
        set_molc(xclicimpbin, 1, name, cli)

class UuidMapTest(SubTest):
    def execute(self, do_sync, dut, cli, deviceuuid, vmuuid, vminstanceuuid,
                **_):
        def make_run_property(vmuuid):
            return 'rpc:vm=' + vmuuid + ',destination=x,interface=x,member=x'

        cli('purge-vm-instance', vminstanceuuid)
        cli('remove-vm', vmuuid)
        vmuuid = cli('add-vm', 'vm name')
        cli('add-vm-instance', deviceuuid, vmuuid, VM_NAME)

        vmconfig = ['-c', 'nic/0:network:/wired/0/bridged',
                    '-c', 'nic/0:backend-uuid:' + vmuuid]
        for prop in VM_RUN_PROPERTIES:
            vmconfig += ['-c', 'vm:' + prop + ':' + make_run_property(vmuuid)]
        args = ['add-vm'] + vmconfig + ['vm 2 name']
        vm2uuid = cli(*args)
        vminstance2uuid = cli('add-vm-instance', deviceuuid, vm2uuid,
                              ALT_VM_NAME)

        do_sync()
        clientvmuuid = run(['xec-vm', '-n', VM_NAME, 'get', 'uuid'],
                           host=dut).rstrip()
        value = run(['xec-vm', '-n', ALT_VM_NAME, '-c', '0', 'get',
                     'backend-uuid'], host=dut).rstrip()
        if value != clientvmuuid:
            raise VmUuidNotMappedAsExpected('backend-uuid',
                                            'value=', value,
                                            'expected=', clientvmuuid,
                                            'vm_name=', ALT_VM_NAME,
                                            'dut=', dut)
        for prop in VM_RUN_PROPERTIES:
            expected = make_run_property(clientvmuuid)
            value = run(['xec-vm', '-n', ALT_VM_NAME, 'get', prop],
                        host=dut).rstrip()
            if value != expected:
                raise VmUuidNotMappedAsExpected(prop,
                                                'value=', value,
                                                'expected=', expected,
                                                'vm_name=', ALT_VM_NAME,
                                                'dut=', dut)
        print 'HEADLINE: VM uuids mapped as expected'

def syncxt_test(dut, build, result_id, source_directory, sub_test=SubTest,
                preserve_database=False):
    """Synchronizer XT tests"""
    def print_errors(data):
        for line in data.splitlines():
            print 'STDERR:', line

    sub_instance = sub_test()
    

    if build is None and source_directory is None:
        build = try_get_build(dut)

    sub_instance.configure(dut, build)
        
    port, portdir = get_apache_port(SYNCXT_SERVER, dut)
    srcdir, srchost, xclicimpbin = deploy_code(dut, build, source_directory, portdir)
    name = 'bvt_%d_%s' % (port, gethostname().split('.')[0].replace('-', '_'))
    print 'HEADLINE: using oracle name', name
    orun = specify(host=SYNCXT_SERVER, env=get_oracle_environment(), 
                   cwd=portdir+'/sync-database', error_callback=print_errors)
    def cli(command, *args):
        """Run a sync-admin command with args; extract result"""
        dblogin = (name+'_admin/'+ name+'_admin' + 
                   '@'+ORACLE_SERVER)
        full_args = [portdir+'/sync-cli/sync-admin',
                     '-d', dblogin, command, '-j']+list(args) 
        print 'SYNCCLI: running ', ' '.join(full_args)
        out = orun(full_args)
        print 'SYNCCLI: result', repr(out)
        if out != "":
            return loads(out)
    prepare_database_args = {
        'cli': cli, 'orun':orun, 'name':name, 'dut':dut, 'portdir':portdir,
        'source_directory':source_directory, 'xclicimpbin':xclicimpbin,
        'preserve_database':preserve_database, 
    }
    (deviceuuid, secret, vmuuid, vminstanceuuid, 
     diskuuids) = sub_instance.prepare(prepare_database_args)
    print 'INFO: synchronizer VM uuid', vmuuid

    with LogReader(SYNCXT_SERVER, result_id, dut, portdir):
        with Timed('Getting apache ready'):
            ensure_ssl_files_exist()
            ensure_apache_ready(SYNCXT_SERVER)
            copy_tree(('root', SYNCXT_SERVER, 
                       portdir+'/sync-server/sync_server'),
                      ('root', SYNCXT_SERVER, portdir))
            # we need the WSGI scripts at the top so imports work
            copy_tree(('root', SYNCXT_SERVER, 
                       portdir+'/sync-server/sync_server/scripts/'),
                      ('root', SYNCXT_SERVER, portdir))
            # this is also a bit weird
            copy_tree(('root', SYNCXT_SERVER, 
                       portdir+'/sync-database/sync_db'),
                      ('root', SYNCXT_SERVER, portdir))
        write_config_file(port, SYNCXT_SERVER, name)
        print 'HEADLINE: testing hello request'
        retry(lambda: do_hello(port, SYNCXT_SERVER, 
                               deviceuuid, secret),
              'testing HTTP server')
        url = 'https://%s:%d/' % (SYNCXT_SERVER, port)
        print "HEADLINE: url", url, "user", deviceuuid, "password", secret
        run(['chown', '-R', apache_user(), portdir], host=SYNCXT_SERVER, user='root')
        def do_sync(specified_secret=None, 
                    specified_deviceuuid=None,
                    timeout=24*60*60, cafile=SSL_CERT):
            """run sync-client"""
            run_client(dut, url, srcdir, 
                       specified_secret if specified_secret else secret, 
                       specified_deviceuuid if specified_deviceuuid else deviceuuid, 
                       SYNCXT_SERVER, cafile=cafile,
                       timeout=timeout)
        sub_instance.execute(do_sync=do_sync, dut=dut, cli=cli,
                             deviceuuid=deviceuuid, vmuuid=vmuuid,
                             vminstanceuuid=vminstanceuuid,
                             diskuuids=diskuuids, name=name,
                             xclicimpbin=xclicimpbin)

BASE_ARGS = [('dut', '$(DUT)'), ('build', '$(BUILD)'),
             ('result_id', '$(RESULT_ID)'),
             ('source_directory', '$(SOURCE_DIRECTORY)'),
             ('preserve_database', '$(PRESERVE_DATABASE)')]
BASE_CASE = {'function': syncxt_test, 'bvt':True, 'trigger' : 'platform ready',
             'arguments': BASE_ARGS}
TEST_CASES = [
    dict(BASE_CASE, command_line_options = ['--syncxt-test'],
         description = 'Test Synchronizer XT encrypted XP VM download',
         arguments = BASE_ARGS + [('sub_test', EncryptedVmDownload)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-ota'],
         description = 'Test Synchronizer XT over the air update',
         arguments=BASE_ARGS +[('sub_test', OTAUpdateTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-licensing-offline'],
         description = 'Test the offline part of the licensing system',
         arguments=BASE_ARGS +[('sub_test', OfflineLicensingTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-boot'],
         description = 'Test Synchronizer XT encrypted XP VM download, '
         'and boot VM', arguments=BASE_ARGS+[('sub_test', BootVmTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-template-boot'],
         description = 'Test Synchronizer XT encrypted XP VM download, '
         'using template, and boot VM', arguments=BASE_ARGS+[
            ('sub_test', TemplateBootTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-bad-secret'],
         description = 'Test Synchronizer XT with invalid device secret',
         arguments = BASE_ARGS + [('sub_test', InvalidDeviceSecretTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-removed-device'],
         description = 'Test Synchronizer XT with removed device',
         arguments = BASE_ARGS + [('sub_test', RemovedDeviceTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-bad-ca'],
         description = 'Test Synchronizer XT with server certificate that is '
         'not deemed valid by the client certifcate authority',
         arguments = BASE_ARGS + [('sub_test', BadCATest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-change-memory'],
         description = 'Test Synchronizer XT changing memory level',
         arguments = BASE_ARGS + [('sub_test', ChangeMemoryTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-rename-vm'],
         description = 'Test Synchronizer XT renaming VM',
         arguments = BASE_ARGS + [('sub_test', RenameVMTest)]),
    dict(BASE_CASE, 
         command_line_options = ['--syncxt-test-transfer-shared-disk'],
         description = 'Test Synchronizer XT transferring a shared disk',
         arguments = BASE_ARGS + [('sub_test', TransferSharedDiskTest)]),
    dict(BASE_CASE, 
         command_line_options = ['--syncxt-test-transfer-non-shared-disk'],
         description = 'Test Synchronizer XT transferring a non-shared disk',
         arguments = BASE_ARGS + [('sub_test', TransferNonSharedDiskTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-graceful-shutdown'],
         description = 'Test Synchronizer XT handling graceful VM destruction',
         arguments = BASE_ARGS + [('sub_test', GracefulDestroyTest)]),
    dict(BASE_CASE, command_line_options = ['--syncxt-test-uuid-map'],
         description = 'Test Synchronizer XT VM uuid mapping',
         arguments = BASE_ARGS + [('sub_test', UuidMapTest)]),

]
