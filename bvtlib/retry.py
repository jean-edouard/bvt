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

from time import time, sleep

def retry(fn, description, pace=1.0, timeout=60.0, catch=[Exception], propagate=[]):
    """Run fn, retrying in the event of a exceptions on the catch
    list for up to timeout seconds, waiting pace seconds between attempts"""
    start_time = time()
    count = 0
    while 1:
        count += 1
        delta_t = time() - start_time
        print 'RETRY:', description, 'iteration', count, 'used', delta_t,
        print 'timeout', timeout
        try:
            result = fn()
            print 'RETRY:', description, 'iteration', count, 'succeeded'
            return result
        except Exception, exc:
            matches = [x for x in catch if isinstance(exc, x)]
            propagates = [x for x in propagate if isinstance(exc, x)]
            delta_t = time() - start_time
            if delta_t < timeout and matches and not propagates:
                print 'RETRY:', description, 'iteration', count, \
                    'failed with', repr(exc )
            else:
                raise
        print 'RETRY: sleeping', pace, 'seconds after iteration', count, \
            'of', description, 'failed'
        sleep(pace)
