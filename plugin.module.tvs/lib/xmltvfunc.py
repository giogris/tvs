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
import xbmc
from util import DEFAULT_ENCODING, get_country, decodestr

#__all__ = ['channel_ids']


def channel_ids(channelids=''):
    doc = None
    xmltvchannels = dict()
    if os.path.exists(channelids):
        # read ids file (xml format) for channel tvs and channel xmltv link name
        try:
            try:
                doc = minidom.parse(channelids)
                channels = doc.getElementsByTagName('channel')
                for channel in channels:
                    try:
                        # take the channel id and link name
                        id = decodestr(channel.getAttribute('id'))
                        linkname = ''
                        for node in channel.childNodes:
                            if node.nodeType == channel.ELEMENT_NODE and node.hasChildNodes and linkname == '':
                                if node.nodeName == 'display-name' and node.hasChildNodes:
                                    for nc in node.childNodes:
                                        if nc.nodeType == channel.TEXT_NODE:
                                            linkname += decodestr(nc.nodeValue)
                                    # found the first display-name and so exit loop
                                    break
                        xmltvchannels[linkname] = id
                    except UnicodeError:
                        # ignore every unicode encoding/decoding errors
                        pass
            except:
                logtvs(">>>>> channel_ids() error:", xbmc.LOGERROR)
                logtvs(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]),xbmc.LOGERROR)
        finally:
            if doc <> None:
                doc.unlink()
                
    return xmltvchannels
    

if __name__ == '__main__':
    # test
    print channel_ids('/home/gio/.xbmc/scripts/tvs/config/xmltvids.xml')
    pass

