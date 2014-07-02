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

from twisted.internet import defer, error
from bvtlib import set_pxe_build
from bvtlib.settings import PASSWORD_HASH, RECOVERY_PUBLIC_KEY, \
    RECOVERY_PRIVATE_KEY


@defer.inlineCallbacks
def get_installer_connection(session, dut, build, port=2222):
    try: con = (yield connection.wait_to_come_up(dut, timeout=5, port=port))
    except (connection.UnableToConnectToMachine, error.ConnectionRefusedError),e:
        print 'INFO:',e,'connecting to port',port,'on',dut
        yield session.set_pxe_build(session, dut, build, action='ssh')
        yield session.power_cycle(dut)
        print 'INFO: Connecting to installer SSH port'
        con = (yield connection.wait_to_come_up(dut, timeout=600, port=port))
    defer.returnValue(con)

@defer.inlineCallbacks
def installer_test(session, dut, build):
    stage_2_answer_file = """<interactive>false</interactive>
<preinstall>#!/bin/ash
touch /install/data/preinstall.touch
</preinstall>
<eula accept="yes"></eula>
<mode>fresh</mode>
<partition-mode>use-free-space</partition-mode>
<primary-disk>sda</primary-disk>
<source type="url">http://10.80.248.206/xc_dist/builds/master/%s/repository/</source>
<network-interface mode="dhcp"></network-interface>
<keyboard>us</keyboard>
<enable-ssh>true</enable-ssh>
<password>%s</password>
<recovery-public-key>%s</recovery-public-key>
<recovery-private-key>%s</recovery-private-key>
<postinstall>#!/bin/ash
touch /install/data/postinstall.touch
</postinstall>
"""% (build, PASSWORD_HASH, RECOVERY_PUBLIC_KEY, RECOVERY_PRIVATE_KEY)
    with (yield get_installer_connection(session, dut, build)) as con:
        print 'INFO: I am',(yield con.verified_launch('whoami'))
        yield con.write_file('/usr/bin/prepare-hd-install', 
                             file('/home/xcn_dickonr/src/prepare-hd-install', 'r').read())
        yield con.write_file('/answerfile.ans', stage_2_answer_file)
        yield con.verified_launch('sfdisk --force --no-reread /dev/sda',
                                       input='0,100,L,*\n,0;\n,0;\n,0;\n',timeout=60)
        yield con.verified_launch('mkfs.vfat /dev/sda1')
        yield con.verified_launch(
            'wget -O /var/volatile/installer.iso '+
            session.get_installer_iso_url('master',build))
        yield con.verified_launch(
            'prepare-hd-install -a /answerfile.ans /var/volatile/installer.iso /dev/sda1')
    yield set_pxe_build.set_pxe_build(session, dut, None, 'boot')    
    yield session.power_cycle(dut)
    with (yield connection.wait_to_come_up(dut, timeout=3600)) as con:
        print 'INFO: connected to',con

TEST_CASES = [{
        'description' : 'Test installer', 'trigger' : 'python ready',
        'command_line_options' : ['--installer-test'],
        'options_predicate' : lambda options: options.installer_test,
        'function': installer_test,
        'arguments' : [('dut', '$(DUT)'), ('build', '$(BUILD)')]}]
