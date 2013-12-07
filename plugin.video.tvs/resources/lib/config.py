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

import sys
import os
import re
import string
import xbmc
import xbmcaddon
import tvdata
import codecs
from xbmcutil import *
import db
from util import get_country, DEFAULT_ENCODING, purge_string, decodestr
from xbmcswift2 import Plugin


#__all__ = ['tvconfig']

PLUGIN_NAME = 'TV Script'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

__rootdir__     = plugin.addon.getAddonInfo('path')

band_re = re.compile('BANDWIDTH_(\d)_MHZ')
channel_re = re.compile('(.*)\(.*\)')

# default values
BW_DEFAULT = '8'
TCP_STREAMING_PORT_BASE = 9000
CHANNEL_PROTO = 'http'

# DVB-T (terrestrial television)
# fields order in channels-<adapter>.conf (DVB-T)
CH_NAME = 0
CH_FREQ = 1
CH_BAND = 3
CH_PROG = 12

# DVB-S (satellite television)
# fields order in channels-<adapter>.conf (DVB-S)

configdir = os.path.join(__rootdir__,'config')
datadir = os.path.join(xbmc.translatePath('special://masterprofile'),'addon_data',PLUGIN_ID)
databasefile = os.path.join(datadir,'tvs.db')

CHANNELSFILEPREF = 'channels-'

class DvbConfig:
    
    def __init__(self,  configfile=None):
        global __rootdir__,configdir,databasefile
        self.configfile = configfile
        self.channels = list()
        self.dvbctl = list()
        self.adapters = list()
        self.channelsdir = os.path.join(__rootdir__,'resources','media','channels')
        self.preorderedchannels = os.path.join(configdir,'preorderedchannels-'+get_country()+'.conf')

        if configfile == None:
            raise Exception('TvS Config Error')
            
        if not os.path.exists(configfile):
            # create data base configuration file
            db.create_db()
            log_error('Config file missing: '+configfile)
            return
            
    def load_adapters(self):
        try:
            # load adapters params
            self.adapters = db.read_adapters()
        finally:
            pass
        return

    def clear_vlc_controller(self):
        if len(self.dvbctl) > 0:
            del self.dvbctl[0:len(self.dvbctl[i])-1]
        self.dvbctl = list()

    def retrieve_channels(self,adapter,type=tvdata.DVBT):
        res = False
        ispreorder = False
        chlist = dict()
        f = None
        fpreord = None
        channelsfile = self.get_channelsfile(adapter)
        plugin.log.debug('dvb retireve channels...')
        # retrieve channel list from adapter config file
        try:
            try:
                if type == tvdata.DVBT:
                    plugin.log.debug('dvb channelsfile: %s' % (channelsfile))
                    if os.path.exists(channelsfile):
                        plugin.log.debug('dvb preorderedchannels: %s' % (self.preorderedchannels))
                        if os.path.exists(self.preorderedchannels.lower()):
                            # load the preodered channles list
                            ispreorder = True
                            fpreord = codecs.open(self.preorderedchannels.lower(),'r')
                            for line in fpreord:
                                a = line.strip().split(';')
                                if a and len(a) > 1:
                                    chlist[a[1]] = a[0]
                            fpreord.close()
                            fpreord = None
                        else:
                            plugin.log.info('dvb preorderchannels file not found: %s' % (self.preorderedchannels))
                        
                        # delete all channales in db for this adapter 
                        db.drop_channels(adapter)
                        plugin.log.debug('dvb channels deletd')
                        
                        f = open(channelsfile,'r')
                        plugin.log.debug('dvb channelsfile opened...')
                        order = 0
                        try:
                            for line in f:
                                plugin.log.debug('dvb channelsfile line: %s' % (line))
                                m = line.strip().split(':')
                                if m and len(m) >= 12:
                                    plugin.log.debug('dvb find chname')
                                    _chname = decodestr(m[CH_NAME])
                                    mc = channel_re.search(_chname)
                                    if mc <> None:
                                        _chname = mc.group(1).strip()
                                    plugin.log.debug('dvb chname: %s' % (_chname))
                                    if ispreorder:
                                        plugin.log.debug('dvb channels find preorder: %s' % (_chname))
                                        order = int(self.find_preorder_channel(chlist,_chname))
                                    else:
                                        order = order + 1
                                    mb = band_re.match(m[CH_BAND])
                                    if mb:
                                        bandw = mb.group(1)
                                    else:
                                        bandw = BW_DEFAULT
                                    plugin.log.debug('add channel: %s' % (_chname))
                                    db.add_channel(adapter,
                                                   ('%04d' % (order)),
                                                   m[CH_PROG],
                                                   _chname,
                                                   m[CH_FREQ],
                                                   bandw,
                                                   purge_string(_chname.upper()))
                        except:
                            plugin.log.error(">>>>> retrieve_channels(1): Unexpected error:")
                            plugin.log.error(sys.exc_info()[0])
                            plugin.log.error(sys.exc_info()[1])
                            plugin.log.error(sys.exc_info()[2])
                            raise                    
                        res = True
            except:
                plugin.log.error(">>>>> retrieve_channels(2): Unexpected error:")
                plugin.log.error(sys.exc_info()[0])
                plugin.log.error(sys.exc_info()[1])
                plugin.log.error(sys.exc_info()[2])
        finally:
            if fpreord != None:
                fpreord.close()
            if f != None:
                f.close()
        return res
    
    def find_preorder_channel(self,chlist,chname):
        res = u'9999'
        if chlist != None:
            plugin.log.debug('Search for: %s' % (chname))
            if chname in chlist:
                res = chlist[chname]
                plugin.log.debug('preorder channel orderid=%s' % (res))
                plugin.log.debug('preorder channel found=%s' % (chname))
        return(res)
        
    def adapter_has_channels(self,adapter):
        res = 0
        # retrieve the numebr of channels for the
        # selected adapter
        try:
            res = db.count_channels(adapter)
            plugin.log.debug('COUNT ADAPTER CHANNELS adapter=%s channels=%d' % (adapter,res))
        finally:
            pass
        return res
        
    def get_channelsfile(self,adapter):
        global datadir
        return(os.path.join(datadir,CHANNELSFILEPREF+str(adapter)+'.conf'))
        
tvconfig = DvbConfig(databasefile)

#if __name__ == '__main__':
#    configfile = os.path.join(os.getcwd(),'config','tvs.xml')
#    tvconfig.load()  
#    if tvconfig.channels <> None:
#        print configfile
#        print tvconfig.channels
##        for line in tvconfig.channels:
##            print line
##        tvconfig.dvbctl.append(DvbController('localhost',0, 'dvbstreamer', 'control'))
##        tvconfig.retrieve_channels(0)
          
