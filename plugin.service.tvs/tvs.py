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
import string
import threading
import subprocess
import signal
import time
import shlex

import xbmc
import db
from util import get_country, check_pid
from resources.lib import epg
from resources.lib import pvr
from resources.lib import dvb_t
from xbmcswift2 import Plugin


PLUGIN_NAME = 'TV Script Streaming Service'
PLUGIN_SERVICE_ID = 'plugin.service.tvs'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_SERVICE_ID, __file__)

__version__ = plugin.addon.getAddonInfo('version')
__rootdir__ = plugin.addon.getAddonInfo('path')
__doc__ = '''
Tvs is simple XBMC script for viewing DVB-TV (now DVB-T e then DVB-S and DVB-C).
It consists of 2 parts:
1) a main process which launch the vlc backend streaming daemon, capture the recording
rquest from the frontend and request and store EPG data from EPG data sources
2) a client frontend running from XBMC gui that display and configure the DVB channels
'''

STRINGS = {
    'no_adapters_found': 30100,
    'unable_to_create_data_dir': 30101,
    'unable_to_create_database': 30102,
    'unable_to_register_adapters': 30103
}


# Translation macro
def _translate(string):
    if string in STRINGS:
        return plugin.get_string(STRINGS[string])
    else:
        return string

# to be modified for Windows
# get the addon path
datadir = os.path.join(xbmc.translatePath('special://masterprofile'), 'addon_data', PLUGIN_ID)
databasepath = os.path.join(datadir, 'tvs.db')

RR_PERIOD = 10
THREAD_POLLING = 30
VLC_TELNET_PORT = 4212
VLC_HTTP_PORT = 9000
VLC = '/usr/bin/vlc-wrapper'
TVS_PID_FILE = os.path.join(datadir, 'tvs.pid')
DEFAULT_ENCODING = 'latin-1'


class Tvs(threading.Thread):
    vlcpid = None
    vlock = threading.Lock()

    def __init__(self, adapterslist=None):
        threading.Thread.__init__(self)
        plugin.log.debug('main service __init__')
        self.name = 'tvs service'
        self.epg = None
        self.pvr = None
        self.adapterslist = adapterslist
        self.pid = os.getpid()
        self.vlcprocs = list()
        self._stop = threading.Event()

    def run(self):
        plugin.log.info('main service is running')
        self.vlc_streamer()
        # run epg grabber
        self.epg = epg.Epg(__rootdir__)
        self.epg.start()
        # run recorder
        self.pvr = pvr.Pvr(__rootdir__)
        self.pvr.start()
        isalive = True
        plugin.log.debug('xbmc.abortRequested %s' % str(xbmc.abortRequested))
        plugin.log.debug('isalive %s' % str(isalive))
        plugin.log.debug('stopped %s' % str(self.stopped))
        while not xbmc.abortRequested and isalive and not self.stopped:
            time.sleep(RR_PERIOD)
            isalive = False
            for proc in self.vlcprocs:
                if proc.poll() is None:
                    # one vlc streaming process is alive, don't exit
                    isalive = True
            if not isalive:
                # exit from main daemon
                plugin.log.info('main service is in exit state...')
        # ...exit, so die!
        if not self.stopped: self.stop()
        # cleanup
        self.cleanup()

    def stop(self):
        self._stop.set()

    @property
    def stopped(self):
        return self._stop.isSet()

    def cleanup(self):
        # clean up vlc streaming processes
        plugin.log.info('main service cleaning-up processes.')
        if self is not None:
            for proc in self.vlcprocs:
                if check_pid(proc.pid):
                    plugin.log.info('kill vlc service pid %d' % proc.pid)
                    os.kill(proc.pid, signal.SIGKILL)
            # clean up xmltv process
            if self.epg is not None:
                if self.epg.is_alive():
                    plugin.log.info('kill epg service pid %d' % self.epg.pid)
                    os.kill(self.epg.pid, signal.SIGKILL)
            # clean up recorder process
            if self.pvr is not None:
                if self.pvr.is_alive():
                    plugin.log.info('kill pvr service pid %d' % self.pvr.pid)
                    os.kill(self.pvr.pid, signal.SIGKILL)

    def vlc_streamer(self):
        proc = None
        if not os.path.exists(VLC):
            plugin.log.error('vlc wrapper (%s) does not exists' % VLC)
            self.stop()
        try:
            try:
                if self.adapterslist is not None:
                    for adapter in self.adapterslist:
                        # --verbose 0 --quiet --daemon --file-loggin --no-ipv6 --ttl 12 --no-show-intf --no-interact --rt-priority --no-stats -I telnet
                        command = VLC
                        command = string.join([command, '--verbose 0'], ' ')
                        command = string.join([command, '--quiet'], ' ')
                        command = string.join([command, '--ttl 12'], ' ')
                        command = string.join([command, '--no-interact'], ' ')
                        command = string.join([command, '--rt-priority'], ' ')
                        command = string.join([command, '--syslog'], ' ')
                        command = string.join([command, '--intf telnet'], ' ')
                        command = string.join([command, ('--telnet-port %d' % (VLC_TELNET_PORT))], ' ')
                        plugin.log.info('vlc streaming on adapter %d start using command %s' % (adapter[1], command))
                        cmd = shlex.split(command)
                        proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                                                stdin=None,
                                                stdout=None,
                                                stderr=None, close_fds=True)
                        self.vlock.acquire()
                        self.vlcprocs.append(proc)
                        self.vlock.release()
            except:
                plugin.log.error('>>>>> vlc_streamer() error:')
                plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))

        finally:
            pass


def initialize():
    if not os.path.exists(datadir):
        plugin.log.debug(('main service make datadir %s' % datadir))
        os.mkdir(datadir)
        os.chmod(datadir, 0777)
        if not os.path.exists(datadir):
            plugin.notify(_translate('unable_to_create_data_dir') + ' ' + datadir)
            return None

    plugin.log.debug('main service discover_adapters')
    adapterslist = dvb_t.discover_dvbadapters()
    plugin.log.debug('main service out ---- discover_adapters')

    if len(adapterslist) == 0:
        plugin.notify(_translate('no_adapters_found'))

    # create db
    plugin.log.debug(('main service create_db(%s)' % databasepath))
    if db.create_db():
        plugin.log.info('TVS database: %s created' % databasepath)
        os.chmod(databasepath, 0766)
        # add new adapters    
        for a in adapterslist:
            plugin.log.info(('register adapter %s' % a[0]))
            if not db.add_adapter(a[1], a[0], a[2], a[3], a[4]):
                plugin.notify(_translate('unable_to_register_adapters') + ' ' + databasepath)
                return None

        if db.adapters_count() == 0:
            plugin.notify(_translate('no_adapters_found'))
            return None
    else:
        plugin.notify(_translate('unable_to_create_database') + ' ' + databasepath)
        return None

    adapterslist = db.read_adapters()

    return adapterslist


def do_the_job():
    try:
        tvs = None
        adapterslist = initialize()
        if adapterslist is not None:
            # create main tvs thread
            # create main tvs thread
            tvs = Tvs(adapterslist)
            plugin.log.info('main service start with pid %d' % tvs.pid)
            tvs.start()
            plugin.log.debug('>>>> After create TVS thread...')
            # wait until the end
            while tvs.is_alive() and not xbmc.abortRequested:
                tvs.join(THREAD_POLLING)
            plugin.log.debug('>>>> Before cleanup....')
            tvs.cleanup()
        else:
            plugin.log.error('main service initialization failed.')

    except SystemExit:
        plugin.log.info('System exit requested?')
    else:
        plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))

    finally:
        plugin.log.info('stop!')
        if tvs is not None:
            if not tvs.stopped:
                tvs.stop()
                tvs.cleanup()


def autostart():
    try:
        plugin.log.info('starting main service...')
        do_the_job()
        plugin.log.info('exit main service!')
    except:
        plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))


if __name__ == '__main__':
    plugin.log.info('######## TVS Service: Initializing........................')
    plugin.log.info('## Add-on ID   = %s' % str(plugin.id))
    plugin.log.info('## Add-on Name = %s' % str(plugin.name))
    autostart()
