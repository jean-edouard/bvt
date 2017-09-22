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

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse

from webapp.metrics.models import get_boot_times


def view_boot_time(request):
    return render_to_response('metrics/boot_time.html',
                RequestContext(request, {
                    'data': get_boot_times(),
                }))


def view_boot_time_image(request):
    # Get first dut data
    dut, points = get_boot_times()[0]
    builds, times = zip(*points)
    l = len(builds)
    
    # Force matplotlib to not use any Xwindows backend
    import matplotlib
    import matplotlib.cbook
    matplotlib.use('Agg')
    from pylab import figure, close
    
    # Make figure
    f = figure(facecolor='white')
    sp = f.add_subplot(111)
    sp.set_title('"%s" boot time' % dut)
    sp.plot(range(l), times, 'o-')
    f.subplots_adjust(bottom=0.2, left=0.15)
    
    sp.set_xlabel('builds')
    sp.set_xlim(-1, l)
    sp.set_xticklabels([''] + list(builds), rotation=15, horizontalalignment='right')
    
    sp.set_ylabel('seconds')
    sp.set_ylim(20, 35)
    
    # Render response image
    canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(f)
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    close(f)
    return response
