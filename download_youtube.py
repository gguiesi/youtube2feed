from __future__ import unicode_literals
from datetime import datetime
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
                    `url`   TEXT NOT NULL UNIQUE,
                    `channel_id`    INTEGER NOT NULL,
                    `flg_feed`  NUMERIC NOT NULL DEFAULT 0,
                    FOREIGN KEY(`channel_id`) REFERENCES `channel`(`id`) ON DELETE CASCADE
                )'''
        sql_channel = '''CREATE TABLE IF NOT EXISTS "channel" (
                    `id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                    `name`  TEXT NOT NULL UNIQUE,
                    `url`   TEXT NOT NULL UNIQUE,
                    `image_url` TEXT NOT NULL
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
        sql = '''insert into channel (name, url, image_url)
        values (?, ?, ?)'''
        print sql, content[u'uploader'], content[u'uploader_url'],
        content[u'thumbnail']
        self.cur.execute(sql, (content[u'uploader'], content[u'uploader_url'],
                               content[u'thumbnail'],))
        self.conn.commit()

    def get_episodes_by_channel_id(self, channel_id):
        sql = '''select * from episode where channel_id = ? order by
        pub_date desc'''
        return self.cur.execute(sql, (channel_id,)).fetchall()

    def insert_episode(self, content):
        sql = '''insert into episode (title, pub_date, url, channel_id)
        values (?, ?, ?, ?)'''
        title = content[u'title'].replace(':', ' -')
        host_ip = str(socket.gethostbyname(socket.getfqdn()))
        uploader = content[u'uploader']
        upload_date = content[u'upload_date']
        id = content[u'id']
        ext = YdlDownloader.ydl_opts[u'postprocessors'][0][u'preferredcodec']
        url = 'http://%s:8000/youtube/%s/%s-%s.%s' % (host_ip, uploader,
                                                      upload_date, id, ext)
        pub_date = datetime.strptime(upload_date, '%Y%m%d')
        print sql, title, pub_date, url, content[u'channel_id']
        self.cur.execute(sql, (title, pub_date, url, content[u'channel_id']))
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
        content[u'channel_id'] = channel[0]
        try:
            self.db.insert_episode(content)
        except sqlite3.IntegrityError as e:
            print 'ERROR ON SAVE EPISODE: ', e.message

    def download(self, lst):
        with youtube_dl.YoutubeDL(YdlDownloader.ydl_opts) as ydl:
            for i in self.urls:
                t = ydl.extract_info(i, download=False)
                # episode download
                if u'uploader' in t:
                    print '\ngrava ep fora do entries:', t
                    self.save_episode_data(t)
                # channel download
                elif len(t[u'entries']) > 0:
                    for e in t[u'entries']:
                        print '\ngrava ep', e
                        self.save_episode_data(e)
