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

from django.conf.urls.defaults import patterns, include
from django.views.generic.simple import direct_to_template

constraint = '((?:/[a-z_]+=[_,0-9a-zA-Z\-\.\ ]+)*)'

urlpatterns = patterns('',
    (r'^$', direct_to_template, {'template': 'home.html'}),
    (r'^metrics/', include('webapp.metrics.urls')),
    (r'^results'+constraint,  'webapp.results.view_results_table'),
    (r'^logs'+constraint, 'webapp.logs.logs_table'),
    (r'^duts'+constraint, 'webapp.duts.duts'),
    (r'^build/', include('webapp.build_report')),    
    (r'^count/', include('webapp.count_results')),
    (r'^scheduler', 'webapp.scheduler.scheduler'),
    (r'^bvt/', include('webapp.bvt.urls')),
    (r'^bin/([a-z\.]+)', 'webapp.binaries.binaries'),
    (r'^grid'+constraint, 'webapp.grid.grid'),
    (r'(django.css)', 'webapp.binaries.binaries'),
    (r'^([a-z0-9A-Z\-\.]+)/([a-z0-9A-Z\-]+)$', 'webapp.redirects.build'),
    (r'^run_results'+constraint, 'webapp.run_results.view_run_results_table'))
