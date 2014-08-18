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
import telnetlib
from util import get_country, DEFAULT_ENCODING, purge_string, decodestring
from xbmcswift2 import Plugin

#__all__ = ['VlcController']
PLUGIN_NAME = 'TV Script'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

__rootdir__     = plugin.addon.getAddonInfo('path')

VLC_PORT = 4212
MEDIANAME = 'tvschannel'

class VlcController:
    """
    High level connection to a Vlc telnet daemon, uses a transitory connection
    to process commands/requests.
    """
    def __init__(self, host, username=None, password=None):
        self.host = host
        self.username = username
        self.password = password
        self.tn = None
        self.my_ip = None

    def close(self):
        """
        Close the connection to the Vlc daemon.
        """
        if self.tn:
            self.logout()
            self.tn.close()
            self.tn = None

    def exec_command(self, commandlist):
        """
        Send a command to the Vlc instance to execute
        """
        if self.tn is None:
            self.tn = telnetlib.Telnet()

        try:
            result = False
            try:
                linesout = list()
                self.tn.open(self.host, VLC_PORT)
                self.tn.read_until("Password: ")
                self.tn.write(self.password+'\n')
                self.tn.read_until('> ')
                for command in commandlist:
                    self.tn.write(command.encode('ascii')+'\n')
                    linesout.append(self.tn.read_until('> ').replace('\r',' '))
                    plugin.log.debug('command sent: ' + command)
                result = linesout
            except:
                plugin.log.error('>>>>> VlcController: exec_command() error:')
                plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
                result = None
        finally:
            self.tn.close()

        return result


    def play_channel(self, streaming_protocol='http', streaming_ip='127.0.0.1', streaming_port='9000', channel=None):
        """
        Play a channel by sending commands to vlc telnet interface
        """
        if channel <> None:
            cmdlist = list()
            cmdlist.append('del %s-%d' % (MEDIANAME,channel.channelid))
            cmdlist.append('new %s-%d broadcast input dvb:// enabled' % (MEDIANAME,channel.channelid))
            cmdlist.append('setup %s-%d output #standard{access=%s,mux=ts,dst=%s:%s/%d}' % (MEDIANAME,channel.channelid,streaming_protocol,streaming_ip,streaming_port,channel.channelid))
            #cmdlist.append('setup %s output #rtp{mux=ps,sdp=rtsp://127.0.0.1:%d/%s_%s)}' % (MEDIANAME,channelid,VLC_STREAMING_PORT,channel.adapter,channel.programid))
            cmdlist.append('setup %s-%d option dvb-adapter=%d' % (MEDIANAME,channel.channelid,channel.adapter))
            cmdlist.append('setup %s-%d option dvb-frequency=%s' % (MEDIANAME,channel.channelid,channel.frequency))
            cmdlist.append('setup %s-%d option dvb-bandwidth=%s' % (MEDIANAME,channel.channelid,channel.bandwidth))
            cmdlist.append('setup %s-%d option program=%s' % (MEDIANAME,channel.channelid,channel.programid))
            #cmdlist.append('setup %s-%d option ts-es-id-pid' % (MEDIANAME,channel.channelid))
            cmdlist.append('control %s-%d play' % (MEDIANAME,channel.channelid))
            plugin.log.debug(cmdlist)  # debug
            self.exec_command(cmdlist)
        
    def rec_channel(self, recname, channel=None, fileout='/dev/null'):
        """
        Record a channel by sending commands to vlc telnet interface
        """
        if channel <> None:
            cmdlist = list()
            cmdlist.append('del %s' % (recname))
            cmdlist.append('new %s schedule input dvb:// enabled' % (recname))
            cmdlist.append('setup %s output #standard{access=file,mux=ps,dst=%s)}' % (recname,fileout))
            cmdlist.append('setup %s option dvb-adapter=%d' % (recname,channel.adapter))
            cmdlist.append('setup %s option dvb-frequency=%s' % (recname,channel.frequency))
            cmdlist.append('setup %s option dvb-bandwidth=%s' % (recname,channel.bandwidth))
            cmdlist.append('setup %s option program=%s' % (recname,channel.programid))
            cmdlist.append('control %s enabled' % (recname))
            plugin.log.debug(cmdlist)   # debug
            self.exec_command(cmdlist)
        
    def stop_channel(self,channelid):
        """
        Stop a channel by sending commands to vlc telnet interface
        """
        cmdlist = list()
        cmdlist.append('control %s-%d stop' % (MEDIANAME,channelid))
        self.exec_command(cmdlist)
        
    def del_channel(self,channelid):
        """
        Delete a channel by sending commands to vlc telnet interface
        """
        cmdlist = list()
        cmdlist.append('del %s-%d' % (MEDIANAME,channelid))
        self.exec_command(cmdlist)
        
    def del_all_channels(self):
        """
        Delete all tuned channels by sending commands to vlc telnet interface
        """
        cmdlist = list()
        cmdlist.append('del all')
        self.exec_command(cmdlist)
 
    def channel_isplaying(self,channelid):
        """
        Test if a channel is playing
        """
        isplaying = False
        cmdlist = list()
        cmdlist.append('show %s-%d' % (MEDIANAME,channelid))
        linesout = self.exec_command(cmdlist)
        if linesout <> None:
            pattern = re.compile('.*state : playing')
            for line in linesout:
                plugin.log.debug('>>>>> ' + line)
                if pattern.search(line):
                    isplaying = True
                    break
        return isplaying
        
    def which_channel_isplaying(self):
        """
        Test channel is playing
        """
        channelplay = ''
        isplaying = False
        cmdlist = list()
        cmdlist.append('show')
        linesout = self.exec_command(cmdlist)
        if linesout <> None:
            patternstate = re.compile('.*state : playing')
            patternchannel = re.compile('.*%s-\d+' % (MEDIANAME))
            for lines in linesout:
                mylines = lines.split('\n')
                for line in mylines:
                    plugin.log.debug('>>>>> ' + line)
                    if patternchannel.search(line):
                        channelplay = line.strip()
                    if patternstate.search(line):
                        isplaying = True
                        break
                if isplaying:
                    break
        return channelplay
        
    
    def logout(self):
        """
        Logout the telnet session
        """
        cmdlist = list()
        cmdlist.append('logout')
        self.exec_command(cmdlist)
        

if __name__ == '__main__':
    
    ctrl = VlcController('localhost',0, '', 'admin')
    
    #ctrl.play_channel(0,'546000000','8','3401')
    ctrl.stop_channel(0)
    print 'exit command'
    ctrl.close()
    del ctrl
