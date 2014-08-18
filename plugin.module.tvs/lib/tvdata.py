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

#__all__ = ['TVChannel','DVBT','DVBS','DEFAULT_CODING']

# glabl constants and default values
DVBT       = 'DVB-T'
DVBS       = 'DVB-S'

DATEFMT = '%d.%m.%Y'

class TVChannel(object):
    """
    TV Channel data object
    """
    def __init__(self,adapter=0,type=DVBT,channelid=0):
        self.adapter        = adapter
        self.type           = type
        self.name           = ''
        self.order          = ''
        self.channelid      = channelid
        self.channelhash    = ''
        self.programid      = ''
        self.frequency      = ''
        self.bandwidth      = ''
        self.v_image        = ''
        self.v_nowtitle     = ''
        self.v_nowdescription=''
        self.v_nowstarttime = ''
        self.v_nowstarttimeandtitle=''
        self.v_nowduration  = ''
        self.v_nowyear      = ''
        self.v_nowsubtitle  = ''
        self.v_nowactors    = []
        self.v_nowfanart    = ''
        self.v_nowposter    = ''
        self.v_nowdate      = ''
        self.v_nowgenre     = ''
        self.v_nexttitle    = ''
        self.v_nextescription=''
        self.v_nextstarttime= ''
        self.v_nextstarttimeandtitle=''
        self.v_nextduration  = ''
        self.v_nextyear      = ''
        self.v_nextsubtitle  = ''
        self.v_nextactors    = ''
        self.v_nextfanart    = ''
        self.v_nextposter    = ''
        self.v_nextdate      = ''
        self.v_nextgenre     = ''

    def getimagefile(self,imagedir=''):
        iconfile = db.read_channel_icon(self.channelid)
        if iconfile == None or iconfile == u'':
            image = self.name.encode(DEFAULT_ENCODING)
            iconfile = os.path.join(imagedir,image+'.png')
            if not os.path.exists(iconfile):
                iconfile = os.path.join(imagedir,image+'.jpg')
                if not os.path.exists(iconfile):
                    iconfile = os.path.join(imagedir,image+'.gif')
                    if not os.path.exists(iconfile):
                        iconfile = os.path.join(imagedir,'dummychannel.png')
        #iconfile = os.path.join(tvconfig.channelsdir,'dummychannel.png')
        return iconfile.encode('ascii')

    def nowtitle(self):
        self.v_nowtitle = db.read_epg_nowtitle(self.channelhash)
        return(self.v_nowtitle)

    def nexttitle(self):
        self.v_nexttitle = db.read_epg_nexttitle(self.channelhash)
        return(self.v_nexttitle)

    def nextstarttime(self):
        self.v_nextstarttime = db.read_epg_nextstarttime(self.channelhash)
        return(self.v_nextstarttime)
    
    def nowstarttimeandtitle(self):
        start = self.v_nowstarttime
        if start <> '':
            self.v_nowstarttimeandtitle = start + ' - ' + self.v_nowtitle
        else:
            self.v_nowstarttimeandtitle = self.v_nowtitle
        return self.v_nowstarttimeandtitle

    def nextstarttimeandtitle(self):
        start = self.v_nextstarttime
        if start <> '':
            self.v_nextstarttimeandtitle = start + ' - ' + self.v_nexttitle
        else:
            self.v_nextstarttimeandtitle = self.v_nexttitle
        return self.v_nextstarttimeandtitle

    def nowdescription(self):
        return(db.read_epg_nowdescription(self.channelhash))
    
    def nowstarttime(self):
        return(db.read_epg_nowstarttime(self.channelhash))

    def nowduration(self):
        self.v_nowduration = db.read_epg_nowduration(self.channelhash)
        return(self.v_nowduration)
    
    def nowyear(self):
        self.v_nowyear = db.read_epg_nowyear(self.channelhash)
        return(self.v_nowyear)
    
    def nowsubtitle(self):
        self.v_nowsubtitle = db.read_epg_nowsubtitle(self.channelhash)
        return(self.v_nowsubtitle)
    
    def nowactors(self):
        self.v_nowactors = db.read_epg_nowactors(self.channelhash)
        return(self.v_nowactors)
    
    def nowfanart(self):
        self.v_nowfanart = db.read_epg_nowfanart(self.channelhash)
        return(self.v_nowfanart)
    
    def nowposter(self):
        self.v_nowposter = db.read_epg_nowposter(self.channelhash)
        return(self.v_nowposter)
    
    def nowdate(self):
        self.v_nowdate = datetime.now().strftime(DATEFMT)
        return(self.v_nowdate)

    def nowgenre(self):
        self.v_nowgenre = db.read_epg_nowgenre(self.channelhash)
        return(self.v_nowgenre)

#if __name__ == '__main__':   
#    c = TVChannel() 
#    print c
#    del(c)
    
