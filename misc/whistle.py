#
# Copyright (c) 2010 Citrix Systems, Inc.
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

# needs pyaudio from http://people.csail.mit.edu/hubert/pyaudio/
import pyaudio, sys, struct, math

chunk = 1024
rate = 44100
note = 220.0
p = pyaudio.PyAudio()
stream = p.open(format = pyaudio.paInt16, channels =1, 
                rate = rate, input = True, output=True,
                frames_per_buffer = chunk)
t = 0.0
output = []
sumsq = [0,0,0]
values = [0,0,0]
for cycles in range(50):
    data = stream.read(chunk)
    l = list(struct.unpack('h'*chunk, data))
    phase = 0 if cycles > 30 else (1 if cycles < 10 else 2)
    for i in l: sumsq[phase] += float(i*i)
    values[phase] += len(l)
    dataout = ''
    while len(dataout)/2 < chunk:
        dataout += struct.pack('h', int(32000*math.sin(t * math.pi * 2 * note)
                                        if cycles > 20 else 0))
        t += 1.0/rate
    stream.write(dataout, chunk)
stream.stop_stream()
stream.close()
p.terminate()
rms = [ math.sqrt(s/n) for (s,n) in zip(sumsq, values)]
print rms
print 'signal',rms[0],'background',rms[1]

