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

"""A context manager with a stopwatch"""
from time import time

class Timed:
    def __init__(self, action):
        self.action = action
    def __enter__(self):
        self.t0 = time()
        print 'INFO: starting', self.action
    def __exit__(self, *_):
        deltat = time() - self.t0
        print 'HEADLINE: finished %s in %.3fs' % (self.action, deltat)
