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
from xml.dom import minidom
import subprocess
import select
import signal
import time
import re
import shlex
import atexit
import xbmc
import tvdata
from util import *


#__all__ = ['get_frontend_type', 'get_frontend_name', 'get_frequency_min', 'get_frequency_max',
#            'discover_dvbadapters']

dvbsnoop   = '/usr/bin/dvbsnoop'
DVBSNOOP_COMMAND = (dvbsnoop + ' -s feinfo -adapter %d')

def _log(msg):
    print('%s: %s' % ('dvb_t', msg))
    
def get_frontend_type(r):
    ret = ''
    if r <> None:
        m = re.match('    Frontend-type:       (.*) \((?P<type>.*)\)',r,re.IGNORECASE)
	if m:
	    ret = m.group('type')
    return ret

def get_frontend_name(r):
    ret = ''
    if r <> None:
        m = re.match('    Name: "(?P<name>.*)"',r,re.IGNORECASE)
	if m:
	    ret = m.group('name')
    return ret

def get_frequency_min(r):
    ret = ''
    if r <> None:
        m = re.match('    Frequency \(min\):     (?P<freq>.*) kHz',r,re.IGNORECASE)
	if m:
	    ret = m.group('freq')
    return ret

def get_frequency_max(r):
    ret = ''
    if r <> None:
        m = re.match('    Frequency \(max\):     (?P<freq>.*) kHz',r,re.IGNORECASE)
	if m:
	    ret = m.group('freq')
    return ret

def discover_dvbadapters():
	proc = None
	adapterslist = list()
	if not os.path.exists(dvbsnoop):
		_log('dvbsnoop commmand not found!',True)
	else:
		try:
			try:
				dvb_t_adapters = 0
				last_name = ''
				last_type = ''
				for adapter in range(10):
					dvb_name = ''
					dvb_type = ''
					dvb_freq_min = ''
					dvb_freq_max = ''
					# check for adapter existance
					device = ('/dev/dvb/adapter%d/frontend%d' % (adapter,0))
					if os.path.exists(device):
						_log('found adapter device %s exists' % device)
						_log('checking for adapter %d' % adapter)
						command = (DVBSNOOP_COMMAND % (adapter))
						_log('using command %s' % command)
						proc = subprocess.Popen(command, shell=True,bufsize=0,
									stdin=None,
									stdout=subprocess.PIPE,
									stderr=subprocess.STDOUT, close_fds=True)
						while True:
							# non blocking read
							r = select.select([proc.stdout.fileno()], [], [], 5)[0]
							if r:
								data = proc.stdout.readline()
								if not data:
									break  # EOF from process has been reached
								else:
									line = data.rstrip()
									#_log(line,True)
									if dvb_name <> '':
										if dvb_type == '': 
											dvb_type = get_frontend_type(line)
										if dvb_freq_min == '':
											dvb_freq_min = get_frequency_min(line)
										if dvb_freq_max == '':
											dvb_freq_max = get_frequency_max(line)
									else:
										dvb_name = get_frontend_name(line)
									if dvb_type == tvdata.DVBT and dvb_freq_max <> '' and dvb_freq_min <> '' and \
										last_name <> dvb_name and last_type <> dvb_type:
										adapterslist.append((dvb_name,adapter,dvb_type,dvb_freq_min,dvb_freq_max))
										_log('Adapter: %d' % adapter)
										_log('Name   : %s' % dvb_name)
										_log('Type   : %s' % dvb_type)
										_log('Freqmin: %s' % dvb_freq_min)
										_log('Freqmax: %s' % dvb_freq_max)
										dvb_t_adapters = dvb_t_adapters + 1
										last_name = dvb_name
										last_type = dvb_type
										_log('discover_dvbadapters() - new adapter found...')
										break
									else:
										if check_pid(proc.pid): os.kill(proc.pid, signal.SIGKILL)
							else:
								break	# no more output
					else:
						break	# no more adapters found
			except:
				_log('>>>>> discover_dvbadapters() error:')
				_log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
		finally:        
			if proc <> None:
				if check_pid(proc.pid):
					proc.terminate()
    
	return adapterslist

    
if __name__ == '__main__':
    # test
    pass

