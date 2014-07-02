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

"""Put stuff on artifact filer"""
from bvtlib.settings import ARTIFACTS_ROOT
from bvtlib.settings import ARTIFACTS_NFS_PATH
from bvtlib.run import run
import time, os, tempfile

def make_segments(section, name):
    """work out suitable name as a list of path components"""
    timetup = time.gmtime(time.time())
    segments = [section] + [
        time.strftime(fmt, timetup) for fmt in 
        ['%Y', '%B', '%d', '%H-%M-%S'+name.replace('%', '%%')]]
    reportfile = ('/'.join(segments))
    print 'ARTIFACT:', section, 'artifact will be stored at', reportfile
    return segments


def store_client_artifact(dut, client_file, section, postfix):
    """Move dut:client_file to artifact storage in specific 
    section with postfix"""
    segments = make_segments(section, '-' + dut + postfix)
    destination = ARTIFACTS_NFS_PATH+'/'.join(segments)
    parent = os.path.split(destination)[0]
    print 'ARTIFACT: storing', dut+':'+client_file, 'at', destination
    os.umask(0000)
    run(['mkdir', '-p', parent])
    run(['rsync', client_file, ARTIFACTS_ROOT+'/'+'/'.join(segments)],
         host=dut, timeout=3600)
    return destination

def store_local_artifact(local_file, section, postfix):
    """Copy local_file to artifact storage in specific section with
    postifx"""
    segments = make_segments(section, postfix)
    destination = ARTIFACTS_NFS_PATH+'/'.join(segments)
    parent = os.path.split(destination)[0]
    os.umask(0000)
    run(['mkdir', '-p', parent])
    run(['cp', local_file, destination], timeout=3600)
    return destination
                                
def store_memory_artifact(content, section, postfix):
    """Store content on artifact server in section with postfix"""
    # it might be nice to avoid copying in store_local_artifact
    segments = make_segments(section, postfix)
    destination = ARTIFACTS_NFS_PATH+'/'.join(segments)
    parent = os.path.split(destination)[0]
    run(['mkdir', '-p', parent])
    fileobj = file(destination, 'wb')
    fileobj.write(content)
    fileobj.close()
    return destination
