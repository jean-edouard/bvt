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

from serverlib.tags import html_fragment, h2, a
from bvtlib import mongodb, process_result
from serverlib import show_table, constraints, describe_build
from webapp import status_styling
from django.conf.urls.defaults import patterns
import pymongo

CONNECTION = mongodb.get_autotest()

def model(build):
    """Count resutlts for a build"""
    counts = {}
    for result in CONNECTION.results.find({'build':build}):
        field = process_result.categorise(result)
        counts.setdefault(field, 0)
        counts[field] += 1
    return counts
    
def count_results(request, build):
    """Render count of results as plain text"""
    from django.http import HttpResponse
    data = model(build)
    text = (str(data.get('passes', 0))+ '/'+
            str(data.get('passes',0) + data.get('product_problems', 0) + 
                data.get('unknown_failures', 0)))
    return HttpResponse(text, mimetype='text/plain',)

urlpatterns = patterns('webapp.count_results',
    (r'([a-zA-Z\-0-9]+)', 'count_results'))
