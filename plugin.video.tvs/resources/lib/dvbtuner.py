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
import subprocess
import select
import signal
import locale
import re
import shlex
import xbmcaddon
import xbmcgui
import db
from util import DEFAULT_ENCODING, get_country, decodestring
from resources.lib import xbmcutil
from xbmcswift2 import Plugin

PLUGIN_NAME = 'TV Script'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

__rootdir__     = plugin.addon.getAddonInfo('path')

# Generic class constantc
SCAN_COMMAND = '/usr/bin/w_scan -a %d -f t -X -R 0 -O 0 -c %s'

# String messages
STR_TITLE               = 32000
STR_WAITSCAN            = 32014
STR_WARNSCAN            = 32015
STR_FOUNDSCAN           = 32016

# Regular expressions
re_frequency = re.compile('(\d.*): \(time: (\d*):(\d*)\).*')
re_service   = re.compile('service = (.*)')
re_time      = re.compile('^\(time: (\d*):(\d*)\).*')
re_freq_tuned= re.compile('^tune to: (\w*) f = (\d*)')


def dvb_tune_adapter(adapter,tvconfig):
    try:
        dialog = xbmcgui.Dialog()
        if dialog.yesno(tvconfig.adapters[adapter][0],xbmcutil.translate('tune_adapter_confirm')):
            # tune the adapter
            if not _dvb_tuning(get_country(),adapter,tvconfig.adapters[adapter][0],tvconfig.get_channelsfile(adapter),freqmax=tvconfig.adapters[adapter][4]):
                plugin.notify(xbmcutil.translate('adapter_tuning_fail'))
            else:
                plugin.log.debug('dvb ready to get channels...')
                tvconfig.retrieve_channels(adapter)
        res = True
    except:
        res = False
        plugin.log.error('>>>>> dvb_tune_adapter() error:')
        plugin.log.error(str(sys.exc_info()[0]))
        plugin.log.error(str(sys.exc_info()[1]))
        
    return res

def tvdelete_channel(adapter,channelid):
    try:
        res = False
        channel = db.read_channel_by_id(adapter,channelid)
        if channel <> None:
            dialog = xbmcgui.Dialog()
            if dialog.yesno(channel.name,xbmcutil.translate('tvdelete_channel_confirm')):
                # delete channel from db and list     
                plugin.log.info('delete channel: %s [id=%d]' % (channel.name,channelid))           
                res = db.del_channel_by_id(channelid)
    except:
        plugin.log.error('>>>>> tvdelete_channel() error:')
        plugin.log.error(str(sys.exc_info()[0]))
        plugin.log.error(str(sys.exc_info()[1]))
        
    return res
                                        
def check_pid(pid):        
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def _dvb_tuning(country,adapter,adaptername,outfile,freqmax=999999):
    f = None
    proc = None
    res = False
    startcheck = False
    isscanning = False
    progressDlg = None
    services = 0
    progressvalue = 0
    freqcounter = 0
    freqtuned = 0
    title_scan_msg = xbmcutil.translate('wait_for_scan')
    wait_scan_msg = xbmcutil.translate('warning_scan_running')
    scan_found_msg = xbmcutil.translate('scan_services_found')
    plugin.log.debug('dvb_tuning() - initialized adapter:%d' % adapter)
    try:
        try:            
            if adapter >= 0:
                plugin.log.debug('dvb_tuning() - start progress')
                progressDlg = xbmcgui.DialogProgress()
                plugin.log.debug('dvb_tuning() - progress started')
                progressDlg.create(xbmcutil.translate('tuning_title'),
                                   title_scan_msg % (adaptername),
                                   wait_scan_msg % (''))
                plugin.log.debug('dvb_tuning() - progress created adapter=%d country=%s' % (adapter,country))
                command = (SCAN_COMMAND % (adapter,country))
                f = open(outfile,'w+')
                plugin.log.debug('dvb_tuning() - outfile opened=%s' % outfile)
                plugin.log.debug('dvb_tuning() - ready to launch command=%s' % command)
                cmd = shlex.split(command)
                proc = subprocess.Popen(cmd, 
                                        shell=False,
                                        bufsize=0,
                                        stdin=None,
                                        stdout=f,
                                        stderr=subprocess.PIPE, 
                                        close_fds=True)
                plugin.log.debug('dvb_tuning() - start command: %s' % command)
                chname = ''
                te = ''
                _lastte = te
                while True and not progressDlg.iscanceled():
                    # non blocking read
                    r = select.select([proc.stderr.fileno()], [], [], 5)[0]
                    if r:
                        data = proc.stderr.readline()
                        if not data:
                            break  # EOF from process has been reached
                        else:
                            line = data.rstrip()
                            # log line from scan tool
                            plugin.log.debug(line)
                            if not check_error(line):
                                if not startcheck:
                                    currentadapter = get_dvb_frontend(line)
                                    startcheck = get_start_token(line)
                                    progressvalue = min(100,progressvalue + 1)
                                    progressDlg.update(progressvalue)
                                if startcheck:
                                    # master frequency scan
                                    (fr,te) = find_frequency(line)
                                    
                                    if fr <> '':
                                        isscanning = True
                                        freqcounter += 1
                                        # inc progressbar
                                        progressvalue = min(100,int(float(fr) / freqmax * 100))
                                        progressDlg.update(progressvalue)
                                    else:
                                        # total time elapsed check
                                        te = find_time_elapsed(line)
                                        # channels scan
                                        _chname = find_service(line)
                                        if _chname <> '':
                                            services += 1
                                            chname = ' - ' + _chname
                                        ft = find_frequency_tuned(line)
                                        if ft <> '':
                                            freqtuned += 1  
                                        
                                    if te <> '':
                                        _lastte = te
                                    if freqtuned > 0:
                                        # inc progressbar
                                        progressvalue = min(100,int(float(freqtuned) / freqcounter * 100))
                                        progressDlg.update(progressvalue) 
                                        title_scan_msg = xbmcutil.translate('warning_scan_running_2') 
                                        scan_found_msg = xbmcutil.translate('scan_channel_found')
                                        msg_counter = services
                                    else:
                                        msg_counter = freqcounter
                                                                                                                        
                                    if isscanning:
                                        progressDlg.update(progressvalue, 
                                                           title_scan_msg % (adaptername), 
                                                           wait_scan_msg % (_lastte), 
                                                           (scan_found_msg % (msg_counter)) + chname)
                            else:
                                # an error was encountered while executing w_scan
                                plugin.log.error(command)
                                plugin.log.error(line)
                                progressDlg.close()
                                if check_pid(proc.pid): os.kill(proc.pid, signal.SIGKILL)
                    
                if progressDlg.iscanceled():
                    plugin.log.debug('progress canceled')
                    if check_pid(proc.pid): os.kill(proc.pid, signal.SIGKILL)
            
            if services > 0:
                res = True
        except:
            res = False
            plugin.log.error('>>>>> _dvb_tuning() error:')
            plugin.log.error(str(sys.exc_info()[0]))
            plugin.log.error(str(sys.exc_info()[1]))

    finally:
        plugin.log.debug('dvb tuning end !')        
        if f <> None:
            f.close()
        if proc <> None:
            if check_pid(proc.pid): proc.terminate()
            if progressDlg <> None:
                progressDlg.close()
            del(progressDlg)
            
    return res

def check_error(r):
    if r <> None:
        return (re.search(' FATAL: ',r) <> None)
        
def get_start_token(r):
    if r <> None:
        return (re.match('Scanning (.*) frequencies',r) <> None)
        
def get_dvb_frontend(r):
    ret = ''
    if r <> None:
        m = re.match('frontend (?P<adapter>.*) supports',r,re.IGNORECASE)
	if m:
	    ret = m.group('adapter')
    return ret
        
def find_frequency(r):
    ret1 = ''
    ret2 = ''
    if r <> None:
        m = re_frequency.match(r)
        if m <> None:
            ret1 = m.group(1)
            ret2 = m.group(2)+':'+m.group(3)
    return (ret1,ret2)

def find_frequency_tuned(r):
    ret = ''
    if r <> None:
        m = re_freq_tuned.match(r)
        if m <> None:
            ret = m.group(2)
    return ret

def find_service(r):
    channel = ''
    if r <> None:
        m = re_service.search(r)
        if m <> None:
            channel = decodestring(m.group(1))
    return channel

def find_channel(r):
    ret = None
    if r <> None:
        if re_channel.search(r) <> None:
	    # purge bracketed channel name
	    plugin.log.debug('channel name: ' + r)
	    ret = re_channel.sub('\g<marker>:',r,1)
    return ret

def find_time_elapsed(r):
    ret = ''
    if r <> None:
        m = re_time.search(r)
        if m <> None:
            ret = m.group(1)+':'+m.group(2) 
    return ret


if __name__ == '__main__':
    outfile = '/path/to/file'
    dvb_tuning('IT',0,outfile)

