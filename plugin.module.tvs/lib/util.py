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
import syslog
import locale
import urllib2
import unicodedata

#__all__ = ['get_country','check_pid']

DEFAULT_ENCODING = locale.getpreferredencoding()


def decodestring(s):
    try:
        u_s = unicode(s)
        ret = unicodedata.normalize('NFKD', u_s).encode('ascii', 'ignore')
    except UnicodeError:
        ret = u''
    else:
        pass
    finally:
        pass

    return ret


def try_parse_int(strinp, res=0):
    try:
        return int(strinp)
    except Exception:
        return res


def download(url='', filepath=''):
    outf = None
    try:
        res = False
        try:
            # Get the channel icon file from Internet
            if url != '':
                rfile = urllib2.urlopen(url)
                outf = open(filepath, 'wb')
                outf.write(rfile.read())
                res = True
        except:
            Exception('Download fail: ' + url)
            raise
    finally:
        if outf is not None:
            outf.close()


def get_country():
    ret = ''
    try:
        # get country language code
        ret = locale.getdefaultlocale()[0].split('_')[1]
    except:
        pass
    return ret


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def purge_string(str):
    strout = str.replace(' ', '').replace('-', '').replace('&', '').replace('.', '').replace("'", '').replace('@', '')
    return strout.replace('#', '').replace(':', '').replace(',', '').replace('!', '')
