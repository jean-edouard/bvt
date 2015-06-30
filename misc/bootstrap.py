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

"""prepare a python installation for the code in this repository"""

import subprocess
from os.path import join

def after_install(_, home_dir):
    """Prepare a python installation for autotest"""
    for package, version in [
        ('Twisted', '10.1'),
        ('Nevow', '0.10.0'),
        ('pyOpenSSL', '0.11'),
        # ('dbus-python', None), # no longer findable by PIP on 10 March 2011, but not essential
        ('pymongo', '2.0'),
        ('django', '1.2.3'),
        ('python-daemon', '1.5.5'),
        ('psycopg2', '2.2.2'),
        ('pylint', '0.21.2'),
        ('pyasn1', '0.0.12a'),
        ('requests', '0.10.1'),
        ('pycrypto', '2.3'), # for Twisted conch
        ('funcparserlib', '0.3.4'),
        ('infrastructure', '0.1'), # from scripts.git
        ]:
        subprocess.check_call(
            [join(home_dir, 'bin', 'pip'), 'install', 
             package+(('=='+version) if version else '')])

