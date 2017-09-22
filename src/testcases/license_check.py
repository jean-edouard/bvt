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

from src.bvtlib import exceptions, retry
import os, csv


class UnknownLicences(exceptions.ExternalFailure):
    pass

class UnsupportedBuildName(Exception):
    pass

def license_check(build):
    spl = build.split('-')
    if len(spl) < 4: 
        raise UnsupportedBuildName(build)
    directory = build + '/licences/'
    
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


def entry_fn(build):
    license_check(build)

def desc():
    return 'Check for unknown licenses'

