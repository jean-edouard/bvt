import pexpect
import pxssh

# Assumes a newrole sysadm_r and disables selinux enforcing and remounts rw.
# Puts XT in a permissive, write state to perform tests on.
def elevate_permissions(dut):
    try:
        s = pxssh.pxssh()
        s.login(dut, 'root', "")
        print 'INFO: Requesting sysadm_r privileges.'
        s.sendline('nr')
        s.expect('Password:')#Note that in OpenXT 'Password:' might not be returned...
        s.sendline('\r')
        s.set_unique_prompt()
        print 'INFO: Have sysadm_r privileges.'
        s.prompt()
        s.sendline('setenforce 0')
        print 'INFO: Selinux is permissive.'
        s.prompt()
        s.sendline('rw')
        print 'INFO: XT is mounted rw.'
        s.prompt()
        s.sendline('exit')
        s.logout()
    except pxssh.ExceptionPxssh, e:
        print "pxssh failed."
        print str(e)

def entry_fn(dut):
    elevate_permissions(dut)

def desc():
    return 'Elevate permissions and disable enforcing mode, remount rw'
