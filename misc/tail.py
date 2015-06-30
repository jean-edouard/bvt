#! /scratch/autotest_python/bin/python
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

from time import localtime, strftime
from bvtlib.mongodb import get_logging
from sys import stderr
from argparse import ArgumentParser
from socket import socket, AF_INET, SOCK_STREAM

ORDER = [('$natural', 1)]

def say(channel, text):
    """Announe text on IRC"""
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(('boiler.cam.xci-test.com', 8659))
    sock.send(channel+' '+str(text))
    sock.close()        

def main():
    """Read logs"""
    parser = ArgumentParser(description='Tail all autotest activity')
    parser.add_argument('--irc', action='store_true', 
                        help='Post activity to IRC instead of stdout')
    args = parser.parse_args()
    kinds = ['HEADLINE', 'CRASH', 'RESULT']
    ldb = get_logging()
    prev_id = ldb.logs.find_one(limit=1,
                                sort=[('$natural', -1)])['_id']
    while 1:
        print >>stderr, '(requery)'
        # we do not query on kind since that seems to break mongo
        # tailable cursors
        query = {'_id' : {'$gt':prev_id}}
        cursor = ldb.logs.find(query, tailable=True, 
                               sort=ORDER).add_option(32)
        while cursor.alive:
            try:
                row = cursor.next()
            except StopIteration:
                break
            if row['kind'] in kinds:
                revt = strftime('%H:%M:%S', localtime(row['time']))+' '
                name = row.get('dut_name', '-')
                if args.irc:
                    say('#autotest', name+' '+row['kind']+' '+row['message'])
                else:
                    print >>stderr, revt+name, row['kind'], row['message']

            prev_id = row['_id']

if __name__ == '__main__':
    main()
