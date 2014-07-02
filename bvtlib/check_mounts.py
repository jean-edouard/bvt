#
# Copyright (c) 2012 Citrix Systems, Inc.
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

from bvtlib.run import run, writefile

BASH_SCRIPT = """#!/bin/bash

# test, whether all mountpoints from /etc/fstab are actually mounted

function fail () {
	echo "FAIL: $1"
	exit ${2-1}
}


# no proc, no fun
[ -f /proc/mounts ] || fail "no /proc/mounts" 2

awk ' 
FILENAME=="/etc/fstab" { 
	if ($0 !~ /(^[[:space:]]*#+)|(^[[:space:]]*$)/) { 
		if ($2 !~ /none|^\/media\/|^\/dev\/shm/) {
			expected[$2] = ""
		}
	} 
}

FILENAME=="/proc/mounts" {
	if ($0 !~ /^\/media\//) actual[$2] = ""
}

END {
	for (key_e in expected) {
		print "checking for: " key_e

		if (! (key_e in actual)) {
			print "NOT MOUNTED: " key_e
			exit 6
		}
	}
}' /proc/mounts /etc/fstab
"""
FILE_PATH = '/tmp/check.sh'

def check_mounts(dut):
    """Check mounts are as expected on dut"""
    writefile(FILE_PATH, BASH_SCRIPT, host=dut)
    run(['chmod', '+x', FILE_PATH], host=dut)
    out = run([FILE_PATH], host=dut)
    for line in out.split('\n'):
        print 'INFO:', line
    print 'INFO: mount checking completed cleanly'
    mtab = run(['mount'], host=dut)
    found = 'on /config' in mtab
    print 'INFO: /config', 'IS' if found else 'NOT', 'mounted'
    
TEST_CASES = [{
        'description': 'Check mounts', 
        'command_line_options' : ['--check-mounts'], 'trigger' : 'platform ready', 
        'function': check_mounts, 'bvt':True, 'arguments': [('dut', '$(DUT)')]}]
