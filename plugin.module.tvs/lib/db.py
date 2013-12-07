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
from time import *
from datetime import *
import hashlib
import tvdata
import xbmc
import xbmcaddon
from sqlite3 import dbapi2 as sqlite


#__all__ = ['create_db','read_adapters','add_adapter','read_channels','add_channel',
#            'count_channels','escape_string','del_channel','add_epg_data','add_epg_link','count_epg_links']

PLUGIN_ID = 'plugin.video.tvs'

datadir = os.path.join(xbmc.translatePath('special://masterprofile'),'addon_data',PLUGIN_ID)
databasefile = os.path.join(datadir,'tvs.db')

EPGTIMESTAMPFMT = '%Y%m%d%H%M%S +0100'
EPGEXPIREDAYS   = 5

def _log(msg):
    print('%s: %s' % ('db', msg))
    
def _db_try_readonly(cursor):
    cursor.execute('PRAGMA journal_mode = OFF')
    cursor.execute('PRAGMA synchronous = OFF')
    cursor.execute('PRAGMA read_uncommitted = True')
    
def create_db():
    """
        DataBase creation
    """
    global databasefile
    connection = None
    try:
        try:
            if not os.path.exists(datadir):
                os.mkdir(datadir)
            if not os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                # database parameters
                cursor.execute('PRAGMA encoding = %s' % escape_string('UTF-8'))
                cursor.execute('PRAGMA foreign_keys = ON')
                # TABLE CHANNELS
                cursor.execute('CREATE TABLE IF NOT EXISTS tblchannels \
                                (channelid INTEGER PRIMARY KEY AUTOINCREMENT,\
                                channelhash TEXT, \
                                adapter INTEGER, \
                                orderid TEXT, \
                                programid TEXT, \
                                channelname TEXT, \
                                frequency TEXT, \
                                bandwidth TEXT)')
                # CHANNELS Indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxChannelsOrd \
                                ON tblChannels \
                                (adapter,orderid)')
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxChannelsRef \
                                ON tblChannels \
                                (adapter,programid)')
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxChannelsName \
                                ON tblChannels \
                                (channelname)')
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxChannelsHash \
                                ON tblChannels \
                                (channelhash)')
                # TABLE EPG
                cursor.execute('CREATE TABLE IF NOT EXISTS tblepg \
                                (epgid INTEGER PRIMARY KEY AUTOINCREMENT,\
                                channelhash TEXT, \
                                datetimestart TEXT, \
                                datetimeend TEXT, \
                                category TEXT, \
                                title TEXT, \
                                description TEXT)')
                # EPG Indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxEpgXmltv \
                                ON tblEpg \
                                (channelhash)')
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxEpgDate \
                                ON tblEpg \
                                (datetimestart)')
                # TABLE EPGLINK
                cursor.execute('CREATE TABLE IF NOT EXISTS tblepglink \
                                (epglinkid INTEGER PRIMARY KEY AUTOINCREMENT,\
                                channelhash TEXT, \
                                epgkey TEXT)')
                # EPGLINK Indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxEpgLink \
                                ON tblEpgLink \
                                (channelhash)')
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxEpgLinkKey \
                                ON tblEpgLink \
                                (epgkey)')
                # TABLE RECORDING
                cursor.execute('CREATE TABLE IF NOT EXISTS tblrecording \
                                (recid INTEGER PRIMARY KEY AUTOINCREMENT,\
                                channelid INTEGER REFERENCES tblchannels (channelid) ON DELETE CASCADE, \
                                title TEXT, \
                                file TEXT, \
                                datetime TEXT, \
                                starttime TEXT, \
                                duration TEXT, \
                                status TEXT)')
                # RECORDING Indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxRecordingDate \
                                ON tblRecording \
                                (datetime)')
                # TABLE ADAPTERS
                cursor.execute('CREATE TABLE IF NOT EXISTS tbladapters \
                                (adapterid INTEGER PRIMARY KEY AUTOINCREMENT,\
                                adapterindex INTEGER,\
                                adaptername TEXT,\
                                adaptertype TEXT,\
                                freqmin REAL DEFAULT 0,\
                                freqmax REAL DEFAULT 0)')
                # ADAPTERS Indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxAdaptersName \
                                ON tbladapters \
                                (adaptername)')
                # TABLE PARAMETERS
                cursor.execute('CREATE TABLE IF NOT EXISTS tblparams \
                                (paramid INTEGER PRIMARY KEY AUTOINCREMENT,\
                                paramname TEXT,\
                                paramvalue TEXT,\
                                paramtitle TEXT)')
                cursor.close()
                connection.commit()
            res = db_update()
        except:
            _log(">>>>> create_db() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            res = False
    finally:
        if connection <> None:
            connection.close()
            
    return res

def db_update():
    """ Update database function. Check to see for any needed change in tables. """
    global databasefile
    connection = None
    version = 0
    res = True
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                cursor.execute("SELECT paramvalue FROM tblparams WHERE paramname='DBVERSION'")
                row = cursor.fetchone()
                if row <> None:
                    version = int(row[0])
                else:
                    cursor.execute("INSERT INTO tblParams (paramname,paramvalue,paramtitle) VALUES ('DBVERSION','0','Data Base Version')")
                cursor.close()
                connection.commit()
                
            if version == 0:
                # update to db version 1
                res = db_update_version_1(1)
                
            if version == 1:
                # update to db version 2
                res = db_update_version_2(2)
                
            res = res and True
            
        except:
            if connection <> None:
                connection.rollback()
            _log(">>>>> db_update() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            res = False
    finally:
        if connection <> None:
            connection.close() 
    return res   

def db_update_version_1(dbversion):
    """ Update database to version 1. """
    global databasefile
    connection = None
    res = False
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                # ALTER TABLE CHANNELS
                cursor.execute('ALTER TABLE tblchannels ADD COLUMN shortname TEXT')
                cursor.execute('CREATE INDEX IF NOT EXISTS IdxChannelsShortName \
                                ON tblChannels \
                                (shortname)')
                # ALTER TABLE EPG
                cursor.execute('ALTER TABLE tblepg ADD COLUMN subtitle TEXT')
                cursor.execute('ALTER TABLE tblepg ADD COLUMN year TEXT')
                cursor.execute('ALTER TABLE tblepg ADD COLUMN overview TEXT')         
                cursor.execute('ALTER TABLE tblepg ADD COLUMN actors TEXT')         
                cursor.execute('ALTER TABLE tblepg ADD COLUMN fanarturl TEXT')         
                cursor.execute('ALTER TABLE tblepg ADD COLUMN posterurl TEXT')
                cursor.execute("UPDATE tblparams SET paramvalue='"+str(dbversion)+"' WHERE paramname='DBVERSION'")        
                cursor.close()
                connection.commit()
                
            res = True
            
        except:
            _log(">>>>> db_update_version_1() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close() 
    return res   

def db_update_version_2(dbversion):
    """ Update database to version 1. """
    global databasefile
    connection = None
    res = False
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                # ALTER TABLE CHANNELS
                cursor.execute('ALTER TABLE tblchannels ADD COLUMN icon TEXT')
                cursor.execute("UPDATE tblparams SET paramvalue='"+str(dbversion)+"' WHERE paramname='DBVERSION'")        
                cursor.close()
                connection.commit()
                
            res = True
            
        except:
            _log(">>>>> db_update_version_2() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close() 
    return res  

def escape_string(s):
    """meta escaping, returns quoted string for use in sql statements""" 
    return "'%s'" % str(s).replace("\\","\\\\").replace("'","''") 
    
    
def read_adapters():
    global databasefile
    connection = None
    try:
        try:
            adapters = list()
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                _db_try_readonly(cursor)
                cursor.execute('SELECT adapterindex,adaptername,adaptertype,freqmin,freqmax FROM tbladapters \
                                ORDER BY adapterindex')
                for row in cursor:
                    adapters.append((row[1],row[0],row[2],row[3],row[4]))
                cursor.close()
        except:
            _log(">>>>> read_adapters() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            adapters = list()
    finally:
        if connection <> None:
            connection.close()
        
    return adapters
    
def adapters_count():
    global databasefile
    connection = None
    res = 0
    try:
        try:
            adapters = list()
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                _db_try_readonly(cursor)
                cursor.execute('SELECT COUNT(*) FROM tbladapters')
                row = cursor.fetchone()
                if row <> None:
                    res = int(row[0])
                cursor.close()
        except:
            _log(">>>>> adapters_count() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res
    
def add_adapter(index,name,type,freqmin,freqmax):
    global databasefile
    connection = None
    try:
        try:
            res = False
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                v = (name,index,type)
                cursor.execute('SELECT * FROM tbladapters WHERE adaptername=? AND adapterindex=? AND adaptertype=?',v)
                row = cursor.fetchone()
                # Add adapter only if it doesn't exists
                if row == None:
                    v = (index,name,type,freqmin,freqmax)
                    cursor.execute('INSERT INTO tbladapters \
                                    (adapterindex,adaptername,adaptertype,freqmin,freqmax) \
                                    VALUES (?,?,?,?,?)', v)                
                cursor.close()
                connection.commit()
                res = True
        except:
            _log(">>>>> add_adapters() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res
    
def drop_channels(adapter):
	"""
	Clear channels table
	"""
	global databasefile
	connection = None
	res = False
	try:
		try:
			if os.path.exists(databasefile):
				connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
				cursor = connection.cursor()
				v = (adapter,)
				cursor.execute('DELETE FROM tblChannels WHERE adapter=?',v)
				cursor.close()
				connection.commit()
			res = True
		except:
			_log(">>>>> drop_channels() error:")
			_log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
			res = False
	finally:
		if connection <> None:
			connection.close()
		    
	return res

def read_channels(adapter):
    global databasefile
    connection = None
    channels = None
    try:
    	try:
    	    channels = list()
    	    if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                _db_try_readonly(cursor)
                v = (adapter,)
                cursor.execute('SELECT channelid,orderid,programid,channelname,frequency,bandwidth,channelhash \
                            FROM tblchannels \
                            WHERE adapter=? \
                            ORDER BY orderid,channelname',v)
    	        for row in cursor:
    	            dataobj = tvdata.TVChannel()
    	            dataobj.adapter     = adapter
    	            dataobj.channelid   = row[0]
    	            dataobj.orderid     = row[1]                   
    	            dataobj.programid   = row[2]
    	            dataobj.name        = row[3]
    	            dataobj.frequency   = row[4]
    	            dataobj.bandwidth   = row[5]
    	            dataobj.channelhash = row[6]
                    # read now epg from db
                    _epg = read_epg_now(dataobj.channelhash)
                    if len(_epg) > 0:
                        dataobj.v_nowtitle = _epg['title']
                        dataobj.v_nowdescription = _epg['description']
                        dataobj.v_nowduration = _epg['duration']
                        dataobj.v_nowyear = _epg['year']
                        dataobj.v_nowsubtitle = _epg['subtitle']
                        dataobj.v_nowfanart = _epg['fanart']
                        dataobj.v_nowposter = _epg['poster']
                        dataobj.v_nowgenre = _epg['genre']
                        dataobj.v_nowactors = _epg['actors']
                        dataobj.v_nowstarttime = _epg['datetimestart']
                    # append channel to channel list
                    channels.append(dataobj)    
                cursor.close()
        except:
            _log(">>>>> read_channels() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            channels = list()
    finally:
    	if connection <> None:
    	    connection.close()
    	
    return channels

def read_channel_by_id(adapter,channelid):
    global databasefile
    connection = None
    channel = None
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                _db_try_readonly(cursor)
                v = (channelid,)
                cursor.execute('SELECT channelid,orderid,programid,channelname,frequency,bandwidth,channelhash \
                                FROM tblchannels \
                                WHERE channelid=?',v)
                row = cursor.fetchone()
                if row <> None:
                    channel = tvdata.TVChannel()
                    channel.adapter     = adapter
                    channel.channelid   = row[0]
                    channel.orderid     = row[1]                   
                    channel.programid   = row[2]
                    channel.name        = row[3]
                    channel.frequency   = row[4]
                    channel.bandwidth   = row[5]
                    channel.channelhash = row[6]
                    # read now epg from db
                    _epg = read_epg_now(channel.channelhash)
                    if len(_epg) > 0:
                        channel.v_nowtitle = _epg['title']
                        channel.v_nowdescription = _epg['description']
                        channel.v_nowduration = _epg['duration']
                        channel.v_nowyear = _epg['year']
                        channel.v_nowsubtitle = _epg['subtitle']
                        channel.v_nowfanart = _epg['fanart']
                        channel.v_nowposter = _epg['poster']
                        channel.v_nowgenre = _epg['genre']
                        channel.v_nowactors = _epg['actors']
                        channel.v_nowstarttime = _epg['datetimestart']                
                    # read next epg from db
                    _epg = read_epg_next(channel.channelhash)
                    if len(_epg) > 0:
                        channel.v_nexttitle = _epg['title']
                        channel.v_nextescription = _epg['description']
                        channel.v_nextduration = _epg['duration']
                        channel.v_nextyear = _epg['year']
                        channel.v_nextsubtitle = _epg['subtitle']
                        channel.v_nextfanart = _epg['fanart']
                        channel.v_nextposter = _epg['poster']
                        channel.v_nextgenre = _epg['genre']
                        channel.v_nextactors = _epg['actors']
                        channel.v_nextstarttime = _epg['datetimestart']
                
                cursor.close()
        except:
            _log(">>>>> read_channel_by_id() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return channel

def read_epg_now(channelhash):
    global databasefile
    connection = None
    res = {}
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    connection.row_factory = sqlite.Row
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT title, \
                                    description, \
                                    datetimeend, \
                                    year, \
                                    subtitle, \
                                    fanarturl, \
                                    posterurl, \
                                    category, \
                                    actors, \
                                    datetimestart \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?''',v)
                    row = cursor.fetchone()
                    if row <> None:
                        # get the time portion from 20100214155505
                        dt1 = row['datetimestart'][:14]
                        dt2 = row['datetimeend'][:14]                        
                        delta = datetime(int(dt2[0:4]),int(dt2[4:6]),int(dt2[6:8]),int(dt2[8:10]),int(dt2[10:12]),int(dt2[12:14])) - datetime(int(dt1[0:4]),int(dt1[4:6]),int(dt1[6:8]),int(dt1[8:10]),int(dt1[10:12]),int(dt1[12:14]))
                        duration = str(int(delta.seconds / 60))
                        res = {
                               'title':row['title'],                               
                               'description':row['description'],                               
                               'duration':duration,                               
                               'year':row['year'],                               
                               'subtitle':row['subtitle'],                               
                               'fanart':row['fanarturl'],                               
                               'poster':row['posterurl'],                               
                               'genre':row['category'],                               
                               'actors':row['actors'],                               
                               'datetimestart':str(datetime(int(dt1[0:4]),int(dt1[4:6]),int(dt1[6:8]),int(dt1[8:10]),int(dt1[10:12]),int(dt1[12:14])))[11:-3]
                               }
                    cursor.close()
        except:
            _log(">>>>> read_epg_now() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_next(channelhash):
    global databasefile
    connection = None
    res = {}
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    connection.row_factory = sqlite.Row
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,)
                    cursor.execute('SELECT title, \
                                    description, \
                                    datetimeend, \
                                    year, \
                                    subtitle, \
                                    fanarturl, \
                                    posterurl, \
                                    category, \
                                    actors, \
                                    datetimestart \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart>=''?'' \
                                    ORDER BY datetimestart',v)
                    row = cursor.fetchone()
                    if row <> None:
                        # get the time portion from 20100214155505
                        dt1 = row['datetimestart'][:14]
                        dt2 = row['datetimeend'][:14]                      
                        delta = datetime(int(dt2[0:4]),int(dt2[4:6]),int(dt2[6:8]),int(dt2[8:10]),int(dt2[10:12]),int(dt2[12:14])) - datetime(int(dt1[0:4]),int(dt1[4:6]),int(dt1[6:8]),int(dt1[8:10]),int(dt1[10:12]),int(dt1[12:14]))
                        duration = str(int(delta.seconds / 60))
                        res = {
                               'title':row['title'],                               
                               'description':row['description'],                               
                               'duration':duration,                               
                               'year':row['year'],                               
                               'subtitle':row['subtitle'],                               
                               'fanart':row['fanarturl'],                               
                               'poster':row['posterurl'],                               
                               'genre':row['category'],                               
                               'actors':row['actors'],                               
                               'datetimestart':str(datetime(int(dt1[0:4]),int(dt1[4:6]),int(dt1[6:8]),int(dt1[8:10]),int(dt1[10:12]),int(dt1[12:14])))[11:-3]
                               }
                    cursor.close()
        except:
            _log(">>>>> read_epg_next() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nowtitle(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT title \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?'' \
                                    ORDER BY datetimestart DESC',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowtitle() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nexttitle(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = (datetime.now()).strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,)
                    cursor.execute('SELECT title \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart>=''?'' \
                                    ORDER BY datetimestart',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nexttitle() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nextstarttime(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = (datetime.now()).strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,)
                    cursor.execute('SELECT datetimestart \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart>=''?'' \
                                    ORDER BY datetimestart',v)
                    row = cursor.fetchone()
                    if row <> None:
                        # get the time portion from 20100214155505
                        dt = row[0][:14]
                        res = str(datetime(int(dt[0:4]),int(dt[4:6]),int(dt[6:8]),int(dt[8:10]),int(dt[10:12]),int(dt[12:14])))[11:-3]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nextstarttime() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nowdescription(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT description \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?'' \
                                    ORDER BY datetimestart DESC',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowdescription() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return str(res)

def read_epg_nowstarttime(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT datetimestart \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?''',v)
                    row = cursor.fetchone()
                    if row <> None:
                        # get the time portion from 20100214155505
                        dt = row[0][:14]
                        res = str(datetime(int(dt[0:4]),int(dt[4:6]),int(dt[6:8]),int(dt[8:10]),int(dt[10:12]),int(dt[12:14])))[11:-3]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowstarttime() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nowduration(channelhash):
    global databasefile
    connection = None
    try:
        try:
            res = ''
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT datetimestart,datetimeend \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?''',v)
                    row = cursor.fetchone()
                    if row <> None:
                        dt1 = row[0][:14]
                        dt2 = row[1][:14]                        
                        delta = datetime(int(dt2[0:4]),int(dt2[4:6]),int(dt2[6:8]),int(dt2[8:10]),int(dt2[10:12]),int(dt2[12:14])) - datetime(int(dt1[0:4]),int(dt1[4:6]),int(dt1[6:8]),int(dt1[8:10]),int(dt1[10:12]),int(dt1[12:14]))
                        res = str(int(delta.seconds / 60))
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowduration() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()

    return res

def read_epg_nowyear(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT year \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?'' \
                                    ORDER BY datetimestart DESC',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowyear() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nowsubtitle(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT subtitle \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?'' \
                                    ORDER BY datetimestart DESC',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowsubtitle() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res


def read_epg_nowfanart(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT fanarturl \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?'' \
                                    ORDER BY datetimestart DESC',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowfanart() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nowposter(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT posterurl \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?'' \
                                    ORDER BY datetimestart DESC',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowposter() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nowgenre(channelhash):
    global databasefile
    connection = None
    res = ''
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT category \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?'' \
                                    ORDER BY datetimestart DESC',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowgenre() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_epg_nowactors(channelhash):
    global databasefile
    connection = None
    res = []
    try:
        try:
            if channelhash <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,dt,dt,)
                    cursor.execute('SELECT actors \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart<=''?'' \
                                    AND datetimeend>=''?'' \
                                    ORDER BY datetimestart DESC',v)
                    row = cursor.fetchone()
                    if row <> None:
                        if row[0] <> None:
                            res = row[0].split('|')
                    cursor.close()
        except:
            _log(">>>>> read_epg_nowactors() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def last_epg_datestarttime():
    global databasefile
    connection = None
    res = datetime.now()-timedelta(days=2)
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                _db_try_readonly(cursor)
                cursor.execute('SELECT MAX(datetimestart) FROM tblepg')
                row = cursor.fetchone()
                if row[0] <> None:
                    # get the datetime portion from 20100214155505
                    dt = row[0][:14]
                    res = datetime(int(dt[0:4]),int(dt[4:6]),int(dt[6:8]),int(dt[8:10]),int(dt[10:12]),int(dt[12:14]))
                cursor.close()
        except:
            _log(">>>>> last_epg_datestarttime() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def read_channel_icon(channelid):
    global databasefile
    connection = None
    res = u''
    try:
        try:
            if channelid <> None:
                if os.path.exists(databasefile):
                    connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                    cursor = connection.cursor()
                    _db_try_readonly(cursor)
                    dt = datetime.now().strftime(EPGTIMESTAMPFMT)
                    v = (channelid,)
                    cursor.execute('SELECT icon \
                                    FROM tblchannels \
                                    WHERE channelid=?',v)
                    row = cursor.fetchone()
                    if row <> None:
                        res = row[0]
                    cursor.close()
        except:
            _log(">>>>> read_epg_icon() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()

    return res


def count_channels(adapter):
    global databasefile
    connection = None
    res = 0
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                _db_try_readonly(cursor)
                v = (adapter,)
                cursor.execute('SELECT COUNT(*) \
                                FROM tblchannels \
                                WHERE adapter=?',v)
                row = cursor.fetchone()
                if row[0] <> None:
                    res = int(row[0])
                cursor.close()
        except:
            _log(">>>>> count_channels() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
            
    return res


def add_channel(adapter,order,programid,channelname,frequency,bandwidth,shortname):
    global databasefile
    connection = None
    res = False
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                v = (adapter,order,programid,channelname,frequency,bandwidth,hashlib.md5(channelname).hexdigest(),shortname)
                cursor.execute('INSERT INTO tblchannels \
                                (adapter,orderid,programid,channelname,frequency,bandwidth,channelhash,shortname) \
                                VALUES (?,?,?,?,?,?,?,?)', v)
                cursor.close()
                connection.commit()
                res = True
        except:
            _log(">>>>> add_channel() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            pass
    finally:
        if connection <> None:
            connection.close()
        
    return res

def del_channel(adapter,programid):
    global databasefile
    connection = None
    res = False
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                v = (adapter,programid,)
                cursor.execute('DELETE FROM tblchannels \
                                WHERE adapter=? and programid=?', v)
                cursor.close()
                connection.commit()
                res = True
        except:
            _log(">>>>> del_channel() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def del_channel_by_id(channelid):
    global databasefile
    connection = None
    res = False
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                v = (channelid,)
                cursor.execute('DELETE FROM tblchannels \
                                WHERE channelid=?', v)
                cursor.close()
                connection.commit()
                res = True
        except:
            _log(">>>>> del_channel_by_id() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def purge_expired_epg():
    global databasefile
    connection = None
    res = False
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                dt = (datetime.now()-timedelta(days=EPGEXPIREDAYS)).strftime(EPGTIMESTAMPFMT) 
                v = (dt,)
                cursor.execute('DELETE FROM tblepg \
                                WHERE datetimestart<=?', v)
                cursor.close()
                connection.commit()
                res = True
        except:
            _log(">>>>> purge_expired_epg() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

def add_epg_data(channelname,datetimestart,datetimeend='',category='',title='',subtitle='',description='',year=''):
    global databasefile
    connection = None
    res = False
    try:
        try:
            update_epg = False
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                v = (channelname,)
                cursor.execute('SELECT channelhash \
                                FROM tblepglink \
                                WHERE epgkey=''?''',v)
                row = cursor.fetchone()
                if row <> None:
                    channelhash = str(row[0])
                    if datetimeend == None or datetimeend == '':
                        dt = datetimestart
                        datetimeend = (datetime(int(dt[0:4]),int(dt[4:6]),int(dt[6:8]),int(dt[8:10]),int(dt[10:12]),int(dt[12:14]))+timedelta(hours=1)).strftime(EPGTIMESTAMPFMT)
                    v = (channelhash,datetimestart)
                    cursor.execute('SELECT channelhash \
                                    FROM tblepg \
                                    WHERE channelhash=? \
                                    AND datetimestart=''?''',v)
                    row = cursor.fetchone()
                    if row <> None:
                        update_epg = True

                    if update_epg:
                        v = (datetimestart,datetimeend,category,title,description,subtitle,year,channelhash,datetimestart,)
                        cursor.execute('UPDATE tblepg \
                                        SET datetimestart=?,datetimeend=?,category=?,title=?,description=?, \
                                        subtitle=?, year=? \
                                        WHERE channelhash=? AND datetimestart=?', v)
                    else:
                        v = (channelhash,datetimestart,datetimeend,category,title,description,subtitle,year,)
                        cursor.execute('INSERT INTO tblepg \
                                        (channelhash,datetimestart,datetimeend,category,title,description,subtitle,year) \
                                        VALUES (?,?,?,?,?,?,?,?)', v)
                cursor.close()
                connection.commit()
                res = True
        except:
            _log(">>>>> add_epg_data() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            pass
    finally:
        if connection <> None:
            connection.close()
        
    return res

def add_epg_link(epgkey='',channelprefix='',fname=''):
    global databasefile
    connection = None
    res = False
    try:
        try:
            update = False
            if os.path.exists(databasefile) and len(channelprefix)>2:
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                channelprefix += '%'
                v = (channelprefix,)
                cursor.execute('SELECT channelhash,LENGTH(shortname) FROM tblchannels WHERE shortname LIKE ? ORDER BY LENGTH(shortname)',v)
                row = cursor.fetchone()
                if row <> None:
                    channelhash = row[0]
                    v = (channelhash,)
                    cursor.execute('SELECT channelhash,epgkey FROM tblepglink WHERE channelhash=?',v)
                    row = cursor.fetchone()
                    if row <> None:
                        update = True
    
                    if update:
                        v = (epgkey,channelhash,)
                        cursor.execute('UPDATE tblepglink SET epgkey=''?'' WHERE channelhash=?', v)
                    else:
                        v = (epgkey,channelhash,)
                        cursor.execute('INSERT INTO tblepglink (epgkey,channelhash) VALUES (?,?)', v)

                    if fname <> '':
                        # update channel icon
                        v = (fname,channelhash,)
                        cursor.execute('UPDATE tblchannels SET icon=''?'' WHERE channelhash=?', v)
                        
                    res = True
                    
                    
                cursor.close()
                connection.commit()
        except:
            _log(">>>>> add_epg_link() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
            
    finally:
        if connection <> None:
            connection.close()
        
    return res

def count_epg_links():
    global databasefile
    connection = None
    res = 0
    try:
        try:
            if os.path.exists(databasefile):
                connection = sqlite.connect(databasefile, isolation_level='IMMEDIATE')
                cursor = connection.cursor()
                _db_try_readonly(cursor)
                cursor.execute('SELECT COUNT(*) \
                                FROM tblepglink')
                row = cursor.fetchone()
                if row[0] <> None:
                    res = int(row[0])
                cursor.close()
        except:
            _log(">>>>> count_epg_links() error:")
            _log(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))
    finally:
        if connection <> None:
            connection.close()
        
    return res

if __name__ == '__main__':
    databasefile = os.path.join('/var/lib/tvs/tvs.db')
    #create_db()
    #print read_adapters()
    #print read_channels(0)
    #print count_channels(0)
 
