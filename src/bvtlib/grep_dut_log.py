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

from src.bvtlib.run import run

def grep_dut_log(dut, logname, pattern,
                 user='root',
                 verify=True):
    """Search the rotating log on dut called logname for lines containing pattern.
/var/log/logname and /var/log/logname.*.gz are searched.
The result is the grep output, without marginal filenames."""
    return run(['bash',
                '-c', ' '.join(['zgrep', '-h', '"', pattern, '"', logname])],
               host=dut, verify=verify)
