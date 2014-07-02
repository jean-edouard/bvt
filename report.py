#! /scratch/autotest_python/bin/python
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

import smtplib, urllib, sys, pwd, os
from bvtlib.settings import SMTP_ADDRESS

def main():
    if len(sys.argv) >=3:
        url = sys.argv[2]
    else:
        url = 'http://autotest.cam.xci-test.com/daily'
    if len(sys.argv) >= 2:
        receivers = [sys.argv[1]]
    else:
        receivers = [os.popen('git config user.email', 'r').read().split()[0]]

    receivers = [('#Xenclient-Engg@citrite.net' if x == 'all' else x)
                 for x in receivers]
    author = 'Dickon.Reed@citrix.com'
    print receivers
    print url

    text = urllib.urlopen(url).read()
    tspl = text.split('\n')
    msg = 'From: %s\nTo: %s\nSubject: %s\n%s' % (
        author, ','.join(receivers), tspl[0],
        '\n'.join(tspl[1:]))
    sender = smtplib.SMTP(SMTP_ADDRESS)
    sender.sendmail(author, receivers, msg)
    sender.quit()

if __name__ == '__main__':
    main()
