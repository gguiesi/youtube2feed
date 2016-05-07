from __future__ import unicode_literals
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom
from xml.etree import ElementTree
import youtube_dl
import socket
import sqlite3


class MyLogger(object):
    def debug(self, msg):
        print(msg)

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


class Cursor:
    def __init__(self):
        self.conn = sqlite3.connect('youtube2feed.db')
        self.cur = self.conn.cursor()
        # enable foreign keys
        self.cur.execute('''PRAGMA foreign_keys = ON''')
        self.__create_db()

    def __create_db(self):
        sql_episode = '''CREATE TABLE IF NOT EXISTS "episode" (
                    `id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                    `title` TEXT NOT NULL,
                    `pub_date`  TEXT NOT NULL,
                    `webpage_url` TEXT NOT NULL UNIQUE,
                    `url`   TEXT NOT NULL UNIQUE,
                    `channel_id`    INTEGER NOT NULL,
                    `flg_feed`  NUMERIC NOT NULL DEFAULT 0,
                    `last_update` TEXT NOT NULL,
                    FOREIGN KEY(`channel_id`) REFERENCES `channel`(`id`)
                    ON DELETE CASCADE
                )'''
        sql_channel = '''CREATE TABLE IF NOT EXISTS "channel" (
                    `id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                    `name`  TEXT NOT NULL UNIQUE,
                    `url`   TEXT NOT NULL UNIQUE,
                    `image_url` TEXT NOT NULL,
                    `last_update` TEXT NOT NULL
                )'''
        self.cur.execute(sql_channel)
        self.cur.execute(sql_episode)
        self.conn.commit()

    def get_channels(self):
        sql = '''select * from channel'''
        return self.cur.execute(sql).fetchall()

    def get_channel_by_name(self, name):
        sql = '''select * from channel where name = ?'''
        self.cur.execute(sql, (name,))
        return self.cur.fetchone()

    def insert_channel(self, content):
        sql = '''insert into channel (name, url, image_url, last_update)
        values (?, ?, ?, datetime('now', 'localtime'))'''
        print '\ninsert_channel:\n', sql, content[u'uploader'], content[u'uploader_url'],
        content[u'thumbnail']
        self.cur.execute(sql, (content[u'uploader'], content[u'uploader_url'],
                               content[u'thumbnail'],))
        self.conn.commit()

    def update_channel(self, content):
        sql = '''update channel set image_url = ? where id = ?'''
        print '\nupdate_channel:\n', sql, content[u'id'], content[u'thumbnail']
        self.cur.execute(sql, (content[u'id'], content[u'thumbnail']))
        self.conn.commit()

    def get_episodes_by_channel_id(self, channel_id):
        sql = '''select * from episode where channel_id = ? order by
        pub_date desc'''
        return self.cur.execute(sql, (channel_id,)).fetchall()

    def insert_episode(self, content):
        sql = '''insert into episode (title, pub_date, webpage_url, url,
        channel_id, last_update) values (?, ?, ?, ?, ?,
        datetime('now', 'localtime'))'''
        # print '\ncontent:\n', content
        title = content[u'title'].replace(':', ' -')
        host_ip = str(socket.gethostbyname(socket.getfqdn()))
        uploader = content[u'uploader']
        webpage_url = content[u'webpage_url']
        upload_date = content[u'upload_date']
        id = content[u'id']
        ext = YdlDownloader.ydl_opts[u'postprocessors'][0][u'preferredcodec']
        url = 'http://%s:8000/youtube/%s/%s-%s.%s' % (host_ip, uploader,
                                                      upload_date, id, ext)
        pub_date = datetime.strptime(upload_date, '%Y%m%d')
        print sql, title, pub_date, webpage_url, url, content[u'channel_id']
        self.cur.execute(sql, (title, pub_date, webpage_url, url,
                               content[u'channel_id']))
        self.conn.commit()


class YdlDownloader:
    def my_hook(d):
        if d['status'] == 'finished':
            print 'Done downloading, now converting ...'

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'outtmpl': 'youtube/%(uploader)s/%(upload_date)s-%(id)s.%(ext)s',
        'download_archive': 'download_archive',
        'logger': MyLogger(),
        'progress_hooks': [my_hook],
    }

    def __init__(self, urls):
        self.urls = urls
        self.db = Cursor()

    def save_episode_data(self, content):
        # print '\nsave_episode_data:\n %s\n' % content
        channel = self.db.get_channel_by_name(content[u'uploader'])
        if channel is None:
            self.db.insert_channel(content)
            channel = self.db.get_channel_by_name(content[u'uploader'])
            # print 'channel:', channel
        else:
            c = {}
            # print '\ncontent:\n', content
            c[u'id'] = channel[0]
            c[u'thumbnail'] = content[u'thumbnail']
            self.db.update_channel(c)
        content[u'channel_id'] = channel[0]
        try:
            self.db.insert_episode(content)
        except sqlite3.IntegrityError as e:
            print 'ERROR ON SAVE EPISODE: ', e.message

    def download(self, lst):
        with youtube_dl.YoutubeDL(YdlDownloader.ydl_opts) as ydl:
            for i in self.urls:
                t = ydl.extract_info(i, download=True)
                # episode download
                if u'uploader' in t:
                    print '\ngrava ep fora do entries:', t
                    self.save_episode_data(t)
                # channel download
                elif len(t[u'entries']) > 0:
                    for e in t[u'entries']:
                        print '\ngrava ep', e
                        self.save_episode_data(e)


class Feed:
    def __init__(self):
        self.cursor = Cursor()
        # self.create_feeds()

    def __prettify(self, elem):
        """
        Return a pretty-printed XML string for the Element
        """
        rough_string = ElementTree.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='    ').encode('utf-8')

    def create_feeds(self):
        channels = self.cursor.get_channels()
        for channel in channels:
            xml = self.__get_channel(channel)
            file = open('%s.xml' % channel[1], 'w')
            file.write(self.__prettify(xml))

    def __get_channel(self, channel):
        channel_id = channel[0]
        channel_name = channel[1]
        channel_link = channel[2]
        channel_url_img = channel[3]

        rss = Element('rss')
        rss.set('version', '2.0')
        channel = SubElement(rss, 'channel')
        title = SubElement(channel, 'title')
        title.text = channel_name
        link = SubElement(channel, 'link')
        link.text = channel_link
        last_build_date = SubElement(channel, 'lastBuildDate')
        last_build_date.text = datetime.now().strftime('%a, %d %b %Y ' +
                                                       '%H:%M:%S %z')
        image = SubElement(channel, 'image')
        img_link = SubElement(image, 'link')
        img_link.text = channel_link
        img_url = SubElement(image, 'url')
        img_url.text = channel_url_img
        img_title = SubElement(image, 'title')
        img_title.text = channel_name
        self.__get_items(channel,
                         self.cursor.get_episodes_by_channel_id(channel_id))

        return rss

    def __get_items(self, root_element, items):
        for i in items:
            t = i[1]
            pd = datetime.strptime(i[2], '%Y-%m-%d %H:%M:%S').\
                strftime('%a, %d %b %Y %H:%M:%S %z')
            webpage_url = i[3]
            url = i[4]

            item = SubElement(root_element, 'item')
            title = SubElement(item, 'title')
            title.text = t
            pub_date = SubElement(item, 'pubDate')
            pub_date.text = pd
            link = SubElement(item, 'link')
            link.text = webpage_url
            e = {}
            e['url'] = url
            e['length'] = '0'
            e['type'] = 'audio/mpeg'
            SubElement(item, 'enclosure', e)
