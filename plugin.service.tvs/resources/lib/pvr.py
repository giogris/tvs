# -*- coding: utf-8 -*-
#############################################################################
#
#  TvS	A Digital TV Script for XBMC
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
import syslog
import string
from time import *
import subprocess
import re
import threading
import signal
import db
import xbmc
from util import *
from xml.dom import minidom
from xbmcswift2 import Plugin

PLUGIN_NAME = 'TV Script Streaming Service'
PLUGIN_SERVICE_ID = 'plugin.service.tvs'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_SERVICE_ID, __file__)

datadir = os.path.join(xbmc.translatePath('special://masterprofile'),'addon_data',PLUGIN_ID)
databasepath = os.path.join(datadir,'tvs.db')

RECORDER_PERIOD  = 30					# Every 30secs

class PvrException(Exception):
	
	def __init__(self,msg):
		self.msg = msg


class Pvr(threading.Thread):

	vlock = threading.Lock()

	def __init__(self,scriptdir=''):
		threading.Thread.__init__(self)
		self.daemon = True
		self.pid = os.getpid()
		self.scriptdir = scriptdir
		self.configdir = datadir
	
	def run(self):
		plugin.log.info('pvr daemon is running')
		while True and not xbmc.abortRequested:
			# run recording function
			# recorder runs every RECOREDR_PERIOD seconds (default 30s)
			sleep(RECORDER_PERIOD)
	
	
if __name__ == '__main__':
    """ Test pvr """
    pass
