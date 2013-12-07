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

import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
from util import *
from xbmcswift2 import Plugin

#__all__ = ['get_resolution','translate']

PLUGIN_NAME = 'TV Script'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

__rootdir__ = plugin.addon.getAddonInfo('path')

STRINGS = {
    'no_adapters_found':        30100,
    'channels':                 30101,
    'epg':                      30102,
    'records':                  30103,
    'settings':                 30104,
    'tune_adapter_confirm':     30105,
    'adapter_tuning_fail':      30106,
    'tuning_title':             30107,
    'wait_for_scan':            30108,
    'warning_scan_running':     30109,
    'scan_channel_found':       30110,
    'warning_scan_running_2':   30111,
    'scan_services_found':      30112,
    'tuning':                   30113,
    'mnu_epg_guide':            30114,
    'mnu_record_start':         30115,
    'mnu_delete':               30116,
    'tvdelete_channel_confirm': 30117
}

class TVSError(Exception):
    pass

def get_imagepath(imagefile):
    return os.path.join(__rootdir__,'resources','media','images',imagefile)

# Resolution getter
def get_resolution():
    try:
        win = xbmcgui.Window()
        return win.getWidth() + 'x' + win.getHeight()
    except TypeError:
        return '1920x1080'

# Translation macro
def translate(string):
    if string in STRINGS:
        return plugin.get_string(STRINGS[string])
    else:
        return string