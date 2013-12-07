# -*- coding: utf-8 -*-
#############################################################################
#
#  TvS    A Digital TV Script for XBMC
#
#  Copyright 2012 by G.Griseri (giovanni.griseri@gmail.com)
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import re
import sys
import os
import db
from datetime import *
from util import *
from xbmcswift2 import Plugin

PLUGIN_NAME = 'TV Script'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

__rootdir__     = plugin.addon.getAddonInfo('path')

try:
    # check if tvdb_api is installed
    import tvdb_api
    _tvdbapi = true
    plugin.log.info('Using tvdb_api...')
except:
    _tvdbapi = false
    plugin.log.error('No tvdb_api installed.')
    
    
