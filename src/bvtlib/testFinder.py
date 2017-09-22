#! /usr/local/bin/python2.6
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

from src.bvtlib import testGraph, testModules
import os,sys
import signal, subprocess
import string

#hh = {testModules.hostHibernate:3, testModules.hostSleep:4, testModules.hostReboot:5 ,testModules.hostShutdown:6, testModules.vmReboot:7, testModules.vmPowerOn:8, testModules.vmShutdown:9, testModules.vmHibernate:10, testModules.vmSleep:11, testModules.vmPowerOff:12, testModules.dom0NetworkTest:13, testModules.vmNetworkTest:14}

hh = {}

hy = dict(map(reversed, hh.items()))

def getTag(fn):
    return hh[fn]

def getkey(key):
    return hy[key]

def keyen(lst):
    xx=0
    for i in lst:
        xx = xx*100+i
    return xx    

def keyde(key):
    xx = []
    while(key):
        xx.append(str(key%1000))
        key/=1000 
    xx.reverse()
    return xx 

def signal_handler(signal, frame):
    num = ':'.join(map(str,trace)) 
    print "key : ", keyen(trace) 
    sys.exit(0)



