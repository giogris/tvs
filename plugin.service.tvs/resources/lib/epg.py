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
import shlex
from datetime import *
import xbmc
import db
import xmltvfunc
from util import *  #purge_string, DEFAULT_ENCODING, get_country, download, decodestring
from xml.dom import minidom
from xbmcswift2 import Plugin

PLUGIN_NAME = 'TV Script Streaming Service'
PLUGIN_SERVICE_ID = 'plugin.service.tvs'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_SERVICE_ID, __file__)
pluginsettings = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

__version__ = plugin.addon.getAddonInfo('version')
__rootdir__ = plugin.addon.getAddonInfo('path')

xmltvdir = os.path.expanduser('~/.xmltv')
datadir = os.path.join(xbmc.translatePath('special://masterprofile'), 'addon_data', PLUGIN_ID)
icondir = os.path.join(xbmc.translatePath('special://masterprofile'), 'addon_data', PLUGIN_ID, 'images')
if not os.path.exists(icondir):
    os.makedirs(icondir, 0777)
databasepath = os.path.join(datadir, 'tvs.db')

XMLTV_COMMAND = '/usr/bin/tv_grab_' + get_country().lower()  # localized xmltv grabber
XMLTV_PERIOD = 24  # Every 24h
XMLTV_WAIT_TIME = 60
XMLTV_DAYS = 5


class EpgException(Exception):
    def __init__(self, msg):
        self.msg = msg


class Epg(threading.Thread):
    xmltvproc = None
    vlock = threading.Lock()

    def __init__(self, scriptdir=''):
        threading.Thread.__init__(self)
        self.daemon = True
        self.pid = os.getpid()
        self.xmltvchannels = dict()
        self.scriptdir = scriptdir
        self.configdir = datadir
        self.xmltvfile = os.path.join(self.configdir, 'xmltv.xml')
        self.xmltvids = os.path.join(self.configdir, 'xmltvids.xml')
        self.xmltvlog = os.path.join(self.configdir, 'xmltv.log')

    def run(self):
        plugin.log.info('epg daemon is running')
        if os.path.exists(self.xmltvfile):
            last_modified = datetime.fromtimestamp(os.path.getmtime(self.xmltvfile))
        else:
            last_modified = (datetime.now() - timedelta(days=2))
        plugin.log.info('epg xmltv last run time %s' % str(last_modified))
        # grab and update channels list
        self.xmltv_grabber_channels()
        # link channels to correct epg reference
        self.xmltv_link_channel_epg()
        # main grabber loop
        while True and not xbmc.abortRequested:
            # if time elapsed is more than XMLTV_PERIOD than we get the xmltv file
            if (((datetime.now() - last_modified) >= timedelta(hours=XMLTV_PERIOD)) \
                        or not os.path.exists(self.xmltvfile)) \
                    and db.count_epg_links() > 0:
                # start the epg grabber (xmltv process)
                plugin.log.info('epg launch xmltv grabber...')
                self.xmltv_grabber()
                # wait for xmltv process end
                if self.xmltvproc <> None:
                    # wait until tv_grab terminate
                    plugin.log.info('epg wait for data...')
                    self.xmltvproc.wait()
                    plugin.log.info('epg load data...')
                    # process the xmltv.xml file and load EPG data into db
                    self.load_epg_data()
                    # purge expired epg data
                    db.purge_expired_epg()
            # chek last valid epg time
            if os.path.exists(self.xmltvfile):
                last_modified = datetime.fromtimestamp(os.path.getmtime(self.xmltvfile))
            else:
                last_modified = (datetime.now() - timedelta(days=2))
            # xmltv grabber runs every XMLTV_PERIOD seconds (default 24h)
            sleep(XMLTV_WAIT_TIME)

    def load_epg_data(self):
        doc = None
        if os.path.exists(self.xmltvfile):
            try:
                try:
                    doc = minidom.parse(self.xmltvfile)
                    programs = doc.getElementsByTagName('programme')
                    for program in programs:
                        # check if attribute is present to prevent errors by corrupted xmltv files
                        if program.hasAttribute('channel'):
                            channel = decodestring(program.getAttribute('channel'))
                            if channel <> None:
                                title = None
                                subtitle = ''
                                category = ''
                                description = ''
                                year = ''
                                for node in program.childNodes:
                                    if node.nodeType == program.ELEMENT_NODE:
                                        # TODO language filter (attribute lang="it")
                                        if node.nodeName == 'title' and node.hasChildNodes:
                                            title = ''
                                            for nc in node.childNodes:
                                                if nc.nodeType == program.TEXT_NODE:
                                                    title += decodestring(nc.nodeValue)
                                                plugin.log.info('epg->[' + channel + '] ' + program.getAttribute(
                                                    'start') + ' ' + title)
                                        elif node.nodeName == 'sub-title' and node.hasChildNodes:
                                            subtitle = ''
                                            for nc in node.childNodes:
                                                if nc.nodeType == program.TEXT_NODE:
                                                    subtitle += decodestring(nc.nodeValue)
                                        elif node.nodeName == 'desc' and node.hasChildNodes:
                                            description = ''
                                            for nc in node.childNodes:
                                                if nc.nodeType == program.TEXT_NODE:
                                                    description += decodestring(nc.nodeValue)
                                        elif node.nodeName == 'category' and node.hasChildNodes:
                                            category = ''
                                            for nc in node.childNodes:
                                                if nc.nodeType == program.TEXT_NODE:
                                                    category += decodestring(nc.nodeValue)
                                        elif node.nodeName == 'date':
                                            year = ''
                                            for nc in node.childNodes:
                                                if nc.nodeType == program.TEXT_NODE:
                                                    year += nc.nodeValue
                                if title <> None:
                                    db.add_epg_data(channel,
                                                    program.getAttribute('start'),
                                                    program.getAttribute('stop'),
                                                    category,
                                                    title,
                                                    subtitle,
                                                    description,
                                                    year)
                except:
                    plugin.log.error('>>>>> load_epg_data() error:')
                    plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            finally:
                if doc <> None:
                    doc.unlink()

    def xmltv_grabber(self):
        self.xmltvproc = None
        xmltvperiod = int(pluginsettings.get_setting('epg_days_period'))
        if not os.path.exists(XMLTV_COMMAND):
            plugin.log.error('xmltv_grabber (%s) does not exists' % XMLTV_COMMAND)
        else:
            try:
                try:
                    # start xmltv grab command (i.e.: tv_grab_it --days 1 --verbose --cache)
                    command = XMLTV_COMMAND
                    command = string.join([command, '--verbose'], ' ')
                    command = string.join([command, '--days %d' % (xmltvperiod)], ' ')
                    command = string.join([command, '--cache'], ' ')
                    plugin.log.info('xmltv grabber started using command %s' % (command))
                    f = open(self.xmltvfile, 'w+')
                    l = open(self.xmltvlog, 'w+')
                    self.xmltvproc = subprocess.Popen(command,
                                                      shell=True,
                                                      bufsize=0,
                                                      stdin=None,
                                                      stdout=f,
                                                      stderr=l,
                                                      close_fds=True)
                except:
                    plugin.log.error('>>>>> xmltv_grabber() error:')
                    plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))

            finally:
                pass

    def xmltv_grabber_channels(self):
        proc = None
        if not os.path.exists(XMLTV_COMMAND):
            plugin.log.error('xmltv_grabber_channels (%s) does not exists' % XMLTV_COMMAND)
        else:
            try:
                try:
                    # start xmltv grab channels list command (i.e.: tv_grab_it --list-channels)
                    command = XMLTV_COMMAND
                    command = string.join([command, '--list-channels'], ' ')
                    plugin.log.info('xmltv grabber channles started using command %s' % (command))
                    f = open(self.xmltvids, 'w+')
                    l = open(self.xmltvlog, 'w+')
                    proc = subprocess.Popen(command,
                                            shell=True,
                                            bufsize=0,
                                            stdin=None,
                                            stdout=f,
                                            stderr=l,
                                            close_fds=True)

                    if proc <> None:
                        plugin.log.info('xmltv wait grabber channles...')
                        proc.wait()
                        f.close()
                        l.close()

                except:
                    plugin.log.error('>>>>> xmltv_grabber_channels() error:')
                    plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))

            finally:
                pass

    def xmltv_get_channels_info(self):
        items = []
        if os.path.exists(self.xmltvids):
            doc = None
            try:
                try:
                    doc = minidom.parse(self.xmltvids)
                    channels = doc.getElementsByTagName('channel')
                    for channel in channels:
                        item = {'id': '0', 'name': '', 'iconurl': ''}
                        if channel.hasAttribute('id'):
                            item['id'] = decodestring(channel.getAttribute('id'))
                        names = channel.getElementsByTagName('display-name')
                        if len(names) > 0:
                            item['name'] = purge_string(decodestring(names[0].childNodes[0].data).upper())
                        icons = channel.getElementsByTagName('icon')
                        if len(icons) > 0:
                            if icons[0].hasAttribute('src'):
                                item['iconurl'] = icons[0].getAttribute('src')
                        items.append(item)
                except:
                    plugin.log.error('>>>>> xmltv_get_channels_info() error:')
                    plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            finally:
                if doc <> None:
                    doc.unlink()
        else:
            plugin.log.info(self.xmltvids + ' file not found!')

        return items

    def xmltv_epg_set_info(self, item):
        fname = ''
        try:
            # Get the channel icon file from Internet
            url = item['iconurl']
            if url <> '':
                fname = os.path.join(icondir, os.path.basename(url))
                if not os.path.exists(fname):
                    if download(url, fname):
                        plugin.log.info('channel icon downloaded: ' + url)
        except:
            plugin.log.error('>>>>> xmltv_epg_set_info() error:')
            plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))

        if db.add_epg_link(item['id'], item['name'], fname):
            plugin.log.info('epg link added: ' + item['id'])

    def xmltv_link_channel_epg(self):
        items = self.xmltv_get_channels_info()
        for item in items:
            self.xmltv_epg_set_info(item)


if __name__ == '__main__':
    """ Test egp """
    pass
