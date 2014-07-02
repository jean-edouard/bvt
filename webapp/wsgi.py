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

import sys
sys.stdout = sys.stderr

from os.path import split, join, abspath

CODE_PATH, _ = split(__file__)
ROOT_PATH = abspath(join(CODE_PATH, '..'))
sys.path.append(ROOT_PATH)

from os import environ
environ['DJANGO_SETTINGS_MODULE'] = 'webapp.settings'

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()
