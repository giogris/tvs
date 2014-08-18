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
import time
from __builtin__ import unicode

from xbmcswift2 import Plugin, ListItem, SortMethod

import xbmc
import xbmcaddon
import db
from util import try_parse_int
from resources.lib import config
from resources.lib import xbmcutil
from resources.lib.dvbtuner import dvb_tune_adapter, tvdelete_channel
from resources.lib.xbmcutil import TVSError
from resources.lib.vlctelnet import VlcController


PLUGIN_NAME = 'TV Script'
PLUGIN_ID = 'plugin.video.tvs'
plugin = Plugin(PLUGIN_NAME, PLUGIN_ID, __file__)

__version__ = plugin.addon.getAddonInfo('version')
__rootdir__ = plugin.addon.getAddonInfo('path')

imagedir = os.path.join(__rootdir__, 'images')


@plugin.route('/')
def show_root():
    plugin.log.info('loading adapters...')
    items = []
    config.tvconfig.load_adapters()
    if len(config.tvconfig.adapters) == 0:
        raise TVSError(xbmcutil.translate('no_adapters_found'))
    else:
        for i in range(len(config.tvconfig.adapters)):
            adapter = int(config.tvconfig.adapters[i][1])
            plugin.log.info('loading vlc controllers adapter %d...' % adapter)
            item = {'label': config.tvconfig.adapters[i][0],
                    'path': plugin.url_for(str('show_adapter'), adapter=str(i)),
                    'icon': xbmcutil.get_imagepath('ico_adapter.png'), 'is_playable': False}
            items.append(item)

    return plugin.finish(items)


@plugin.route('/<adapter>')
def show_adapter(adapter):
    items = []
    item = {'label': xbmcutil.translate('channels'), 'path': plugin.url_for(str('show_channels'), adapter=adapter),
            'icon': xbmcutil.get_imagepath('ico_channels.png'), 'is_playable': False}
    items.append(item)
    item = {
        'label': xbmcutil.translate('epg'),
        'path': plugin.url_for(str('show_epg'), adapter=adapter),
        'icon': xbmcutil.get_imagepath('ico_epg.png'),
        'is_playable': False
    }
    items.append(item)
    item = {
        'label': xbmcutil.translate('records'),
        'path': plugin.url_for(str('show_records'), adapter=adapter),
        'icon': xbmcutil.get_imagepath('ico_records.png'),
        'is_playable': False
    }
    items.append(item)
    item = {
        'label': xbmcutil.translate('tuning'),
        'path': plugin.url_for(str('show_tuning'), adapter=adapter),
        'icon': xbmcutil.get_imagepath('ico_tuning.png'),
        'is_playable': False
    }
    items.append(item)
    item = {
        'label': xbmcutil.translate('settings'),
        'path': plugin.url_for(str('show_settings'), adapter=adapter),
        'icon': xbmcutil.get_imagepath('ico_settings.png'),
        'is_playable': False
    }
    items.append(item)
    return plugin.finish(items)


@plugin.route('/<adapter>/channels')
def show_channels(adapter):
    items = []
    channels = db.read_channels(adapter)
    for channel in channels:
        item = tvitem(adapter, channel)
        items.append(item)
    plugin.add_sort_method(SortMethod.NONE, '%B')
    plugin.log.info('show channels finish with %d channels' % (len(items)))
    return plugin.finish(items, update_listing=True)


@plugin.route('/<adapter>/channels/<channelid>')
def play_channel(adapter, channelid):
    # tune program on vlc controller
    def tune_and_play(adapter, channelid):
        streaming_protocol = plugin.get_setting('streaming_protocol')
        streaming_ip = plugin.get_setting('streaming_ip')
        streaming_port = plugin.get_setting('streaming_port')
        command_ip = plugin.get_setting('command_ip')
        command_pass = plugin.get_setting('command_pass')
        iadapter = int(adapter)
        ichannel = int(channelid)
        channel = db.read_channel_by_id(iadapter, ichannel)
        player = VlcController(command_ip, None, command_pass)
        channelplay = player.which_channel_isplaying()
        plugin.log.debug(
            'selected for play %s://%s:%s/%d' % (streaming_protocol, streaming_ip, streaming_port, ichannel))
        if channelplay != '':
            ichannelplay = int(channelplay.split('-')[1])
            if ichannelplay != ichannel:
                player.del_channel(ichannelplay)
        if not player.channel_isplaying(ichannel):
            player.play_channel(streaming_protocol, streaming_ip, streaming_port, channel)
            time.sleep(1)
        return unicode(str('%s://%s:%s/%d' % (streaming_protocol, streaming_ip, streaming_port, ichannel)))
        # ...and now play the tv stream...
    iadapter = int(adapter)
    ichannel = int(channelid)
    plugin.log.debug('TVItem call...')
    item = tvitem(adapter, db.read_channel_by_id(iadapter, ichannel))
    plugin.log.debug('tune and play call...')
    item.path = tune_and_play(adapter, channelid)
    plugin.log.debug('url ready: ' + item.path)
    return plugin.set_resolved_url(item)


@plugin.route('/<adapter>/records')
def show_records(adapter):
    return plugin.end_of_directory(succeeded=False, update_listing=False, cache_to_disc=False)


@plugin.route('/<adapter>/epg')
def show_epg(adapter):
    return plugin.end_of_directory(succeeded=False, update_listing=False, cache_to_disc=False)


@plugin.route('/<adapter>/tuning')
def show_tuning(adapter):
    command_ip = plugin.get_setting('command_ip')
    command_pass = plugin.get_setting('command_pass')
    player = VlcController(command_ip, None, command_pass)
    # remove all possible channel tuned on the adapter
    # no matter about others adapter... sorry.
    player.del_all_channels()
    config.tvconfig.load_adapters()
    if len(config.tvconfig.adapters) == 0:
        raise TVSError(xbmcutil.translate('no_adapters_found'))
    else:
        dvb_tune_adapter(int(adapter), config.tvconfig)
    return plugin.end_of_directory(succeeded=False, update_listing=False, cache_to_disc=False)


@plugin.route('/<adapter>/settings')
def show_settings(adapter):
    plugin.open_settings()
    return plugin.end_of_directory(succeeded=False, update_listing=False, cache_to_disc=False)


@plugin.route('/<adapter>/epg/<channelid>')
def epg_channel(adapter, channelid):
    return plugin.end_of_directory(succeeded=Fale, update_listing=False, cache_to_disc=False)


@plugin.route('/<adapter>/rec/<channelid>')
def rec_channel(adapter, channelid):
    return plugin.end_of_directory(succeeded=False, update_listing=False, cache_to_disc=False)


@plugin.route('/<adapter>/del/<channelid>')
def del_channel(adapter, channelid):
    if tvdelete_channel(int(adapter), int(channelid)):
        return xbmc.executebuiltin('XBMC.Container.Refresh(''plugin://plugin.video.tvs/%s/channels'')' % (adapter))
    else:
        return plugin.end_of_directory(succeeded=False, update_listing=False, cache_to_disc=False)


def create_context_menu(name, adapter, id):
    context_menu = [
        (xbmcutil.translate('mnu_epg_guide') % name,
         'RunPlugin(%s)' % (plugin.url_for('epg_channel', adapter=adapter, channelid=str(id)))),
        (xbmcutil.translate('mnu_record_start') % name,
         'RunPlugin(%s)' % (plugin.url_for('rec_channel', adapter=adapter, channelid=str(id)))),
        (xbmcutil.translate('mnu_delete') % name,
         'RunPlugin(%s)' % (plugin.url_for('del_channel', adapter=adapter, channelid=str(id))))
    ]
    return context_menu


def tvitem(adapter, channel):
    titleandtime = channel.nowstarttimeandtitle()

    item = ListItem(label=channel.name,
                    label2=titleandtime,
                    icon=channel.getimagefile(config.tvconfig.channelsdir),
                    thumbnail=channel.getimagefile(config.tvconfig.channelsdir),
                    path=plugin.url_for(str('play_channel'), adapter=adapter, channelid=str(channel.channelid)))

    item.set_is_playable(True)
    item.set_info('video',
                  {
                      'title': channel.name[:15],
                      'tvshowtitle': titleandtime,
                      'duration': channel.v_nowduration,
                      'plot': channel.v_nowdescription,
                      'plotoutline': channel.v_nowdescription,
                      'tagline': channel.nowstarttimeandtitle(),
                      'playcount': 0,
                      #'cast': channel.v_nowactors,
                      'fanart': channel.v_nowfanart,
                      'extrafanart': channel.v_nowposter,
                      'originaltitle': channel.v_nowtitle,
                      'year': channel.v_nowyear,
                      'album': titleandtime,  # I used album 'cause I haven't found another field to display label2
                      'genre': channel.v_nowgenre
                  })
    item.add_context_menu_items(create_context_menu(channel.name, adapter, channel.channelid), replace_items=True)
    item.add_stream_info('video',
                         {'duration': try_parse_int(channel.v_nowduration) * 60, 'plot': channel.v_nowdescription})
    return item


if __name__ == '__main__':
    try:
        plugin.run()
    except TVSError:
        plugin.notify(msg=TVSError.message)
    except:
        plugin.log.error(str(sys.exc_info()[0].__name__) + ': ' + str(sys.exc_info()[1]))

sys.modules.clear()