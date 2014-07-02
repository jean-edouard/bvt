#
# Copyright (c) 2013 Citrix Systems, Inc.
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

from bvtlib import exceptions, retry
from bvtlib.settings import LICENSE_PATH
import os, csv


class UnknownLicences(exceptions.ExternalFailure):
    pass

class UnsupportedBuildName(Exception):
    pass

def license_check(build):
    spl = build.split('-')
    if len(spl) < 4: 
        raise UnsupportedBuildName(build)
    directory = LICENSE_PATH % ('-'.join(spl[3:]), build)
    bad = []
    for filename in os.listdir(directory):
        if not filename.endswith('.csv'):
            continue
        content = csv.reader(file(directory+'/'+filename, 'r'))
        header = content.next()
        for line in content:
            rec = dict(zip(header, line))
            if rec['Licence'] == 'unknown':
                bad.append((rec['Package name'], rec['Version']))
    if bad:
        raise UnknownLicences(bad)
    print 'HEADLINE:', spl

TEST_CASES = [
    { 'description': 'Check for unknown licenses', 'trigger':'build ready',
      'function': license_check, 'bvt':False, 'reinstall_on_failure':False,
      'command_line_options' : ['--license-test'],
      'arguments' : [('build', '$(BUILD)') ]}]
