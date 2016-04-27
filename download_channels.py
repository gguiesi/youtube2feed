from youtube2feed import YdlDownloader, Feed

lst = [#'https://www.youtube.com/user/Pirulla25',
       #'https://www.youtube.com/channel/UCsMj2K36ejga547ge5cBscg',
       #'https://www.youtube.com/channel/UCfQ98EX3oOv6IHBdUNMJq8Q',
       'https://www.youtube.com/watch?v=os2uOCamqM4',
       #'http://www.youtube.com/user/chicothepa',
       ]

ydl = YdlDownloader(lst)
ydl.download(lst)
f = Feed()
f.create_feeds()
