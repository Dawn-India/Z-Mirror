from logging import getLogger
from os import listdir
from os import path as ospath
from random import SystemRandom
from re import search as re_search
from string import ascii_letters, digits

from yt_dlp import DownloadError, YoutubeDL

from bot import (config_dict, download_dict, download_dict_lock, non_queued_dl,
                 non_queued_up, queue_dict_lock, queued_dl)
from bot.helper.ext_utils.bot_utils import (async_to_sync,
                                            get_readable_file_size,
                                            sync_to_async)
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.yt_dlp_download_status import YtDlpDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import (delete_links, sendStatusMessage)

LOGGER = getLogger(__name__)


class MyLogger:
    def __init__(self, obj):
        self.obj = obj

    def debug(self, msg):
        # Hack to fix changing extension
        if not self.obj.is_playlist:
            if match := re_search(r'.Merger..Merging formats into..(.*?).$', msg) or \
                        re_search(r'.ExtractAudio..Destination..(.*?)$', msg):
                LOGGER.info(msg)
                newname = match.group(1)
                newname = newname.rsplit("/", 1)[-1]
                self.obj.name = newname

    @staticmethod
    def warning(msg):
        LOGGER.warning(msg)

    @staticmethod
    def error(msg):
        if msg != "ERROR: Cancelling...":
            LOGGER.error(msg)


class YoutubeDLHelper:
    def __init__(self, listener):
        self.name = ""
        self.is_playlist = False
        self._last_downloaded = 0
        self.__size = 0
        self.__progress = 0
        self.__downloaded_bytes = 0
        self.__download_speed = 0
        self.__eta = '-'
        self.__listener = listener
        self.__gid = ""
        self.__is_cancelled = False
        self.__downloading = False
        self.opts = {'progress_hooks': [self.__onDownloadProgress],
                     'logger': MyLogger(self),
                     'usenetrc': True,
                     'cookiefile': 'cookies.txt',
                     'allow_multiple_video_streams': True,
                     'allow_multiple_audio_streams': True,
                     'noprogress': True,
                     'allow_playlist_files': True,
                     'overwrites': True,
                     'nocheckcertificate': True,
                     'trim_file_name': 220}

    @property
    def download_speed(self):
        return self.__download_speed

    @property
    def downloaded_bytes(self):
        return self.__downloaded_bytes

    @property
    def size(self):
        return self.__size

    @property
    def progress(self):
        return self.__progress

    @property
    def eta(self):
        return self.__eta

    def __onDownloadProgress(self, d):
        self.__downloading = True
        if self.__is_cancelled:
            raise ValueError("Cancelling...")
        if d['status'] == "finished":
            if self.is_playlist:
                self._last_downloaded = 0
        elif d['status'] == "downloading":
            self.__download_speed = d['speed']
            if self.is_playlist:
                downloadedBytes = d['downloaded_bytes']
                chunk_size = downloadedBytes - self._last_downloaded
                self._last_downloaded = downloadedBytes
                self.__downloaded_bytes += chunk_size
            else:
                if d.get('total_bytes'):
                    self.__size = d['total_bytes']
                elif d.get('total_bytes_estimate'):
                    self.__size = d['total_bytes_estimate']
                self.__downloaded_bytes = d['downloaded_bytes']
                self.__eta = d.get('eta', '-')
            try:
                self.__progress = (self.__downloaded_bytes / self.__size) * 100
            except:
                pass

    async def __onDownloadStart(self, from_queue):
        async with download_dict_lock:
            download_dict[self.__listener.uid] = YtDlpDownloadStatus(self, self.__listener, self.__gid)
        if not from_queue:
            await self.__listener.onDownloadStart()
            await sendStatusMessage(self.__listener.message)

    def __onDownloadError(self, error):
        self.__is_cancelled = True
        async_to_sync(self.__listener.onDownloadError, error)

    def extractMetaData(self, link, name, args, get_info=False):
        if args:
            self.__set_args(args)
        if get_info:
            self.opts['playlist_items'] = '0'
        if link.startswith(('rtmp', 'mms', 'rstp', 'rtmps')):
            self.opts['external_downloader'] = 'ffmpeg'
        with YoutubeDL(self.opts) as ydl:
            try:
                result = ydl.extract_info(link, download=False)
                if get_info:
                    return result
                elif result is None:
                    raise ValueError('Info result is None')
            except Exception as e:
                if get_info:
                    raise e
                return self.__onDownloadError(str(e))
        if 'entries' in result:
            self.name = name
            for entry in result['entries']:
                if not entry:
                    continue
                elif 'filesize_approx' in entry:
                    self.__size += entry['filesize_approx']
                elif 'filesize' in entry:
                    self.__size += entry['filesize']
                if not name:
                    outtmpl_ = '%(series,playlist_title,channel)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d'
                    self.name = ydl.prepare_filename(entry, outtmpl=outtmpl_)
        else:
            outtmpl_ ='%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s'
            realName = ydl.prepare_filename(result, outtmpl=outtmpl_)
            if name == "":
                self.name = realName
            else:
                ext = realName.rsplit('.', 1)[-1]
                self.name = f"{name}.{ext}"
            if result.get('filesize'):
                self.__size = result['filesize']
            elif result.get('filesize_approx'):
                self.__size = result['filesize_approx']

    def __download(self, link, path):
        try:
            with YoutubeDL(self.opts) as ydl:
                try:
                    ydl.download([link])
                except DownloadError as e:
                    if not self.__is_cancelled:
                        self.__onDownloadError(str(e))
                    return
            if self.is_playlist and (not ospath.exists(path) or len(listdir(path)) == 0):
                self.__onDownloadError("No video available to download from this playlist. Check logs for more details")
                return
            if self.__is_cancelled:
                raise ValueError
            async_to_sync(self.__listener.onDownloadComplete)
        except ValueError:
            self.__onDownloadError("Download Stopped by User!")

    async def add_download(self, link, path, name, qual, playlist, args, from_queue=False):
        if playlist:
            self.opts['ignoreerrors'] = True
            self.is_playlist = True
        self.__gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=10))
        await self.__onDownloadStart(from_queue)
        if qual.startswith('ba/b-'):
            mp3_info = qual.split('-')
            qual = mp3_info[0]
            rate = mp3_info[1]
            self.opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': rate}]
        self.opts['format'] = qual
        await sync_to_async(self.extractMetaData, link, name, args)
        if self.__is_cancelled:
            return
        if not from_queue:
            LOGGER.info(f'Download with YT_DLP: {self.name}')
        else:
            LOGGER.info(f'Start Queued Download with YT_DLP: {self.name}')
        if self.is_playlist:
            self.opts['outtmpl'] = f"{path}/{self.name}/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s"
        elif not args:
            self.opts['outtmpl'] = f"{path}/{self.name}"
        else:
            folder_name = self.name.rsplit('.', 1)[0]
            self.opts['outtmpl'] = f"{path}/{folder_name}/{self.name}"
            self.name = folder_name
        if config_dict['STOP_DUPLICATE'] and self.name != 'NA' and not self.__listener.isLeech:
            LOGGER.info('Checking File/Folder if already in Drive...')
            sname = self.name
            if self.__listener.isZip:
                sname = f"{self.name}.zip"
            if sname:
                smsg, button = await sync_to_async(GoogleDriveHelper().drive_list, sname, True)
                if smsg:
                    await delete_links(__listener.message)
                    await self.__listener.onDownloadError('File/Folder already available in Drive.\nHere are the search results:\n', button)
                    return
        limit_exceeded = ''
        if not limit_exceeded and (YTDLP_LIMIT:= config_dict['YTDLP_LIMIT']):
            limit = YTDLP_LIMIT * 1024**3
            if self.__size > limit:
                limit_exceeded = f'Ytldp limit is {get_readable_file_size(limit)}\n'
                limit_exceeded+= f'Your {"Playlist" if self.is_playlist else "Video"} size\n'
                limit_exceeded+= f'is {get_readable_file_size(self.__size)}'
        if not limit_exceeded and (LEECH_LIMIT:= config_dict['LEECH_LIMIT']) and self.__listener.isLeech:
            limit = LEECH_LIMIT * 1024**3
            if self.__size > limit:
                limit_exceeded = f'Leech limit is {get_readable_file_size(limit)}\n'
                limit_exceeded += f'Your {"Playlist" if self.is_playlist else "Video"} size\n'
                limit_exceeded += f'is {get_readable_file_size(self.__size)}'
        if not limit_exceeded and (STORAGE_THRESHOLD:= config_dict['STORAGE_THRESHOLD']):
            limit = STORAGE_THRESHOLD * 1024**3
            acpt = await sync_to_async(check_storage_threshold, self.__size, limit, self.__listener.isZip)
            if not acpt:
                limit_exceeded = f'You must leave {get_readable_file_size(limit)} free storage.'
                limit_exceeded += f'\nYour File/Folder size is {get_readable_file_size(self.__size)}'
        if limit_exceeded:
            await delete_links(self.__listener.message)
            await self.__listener.onDownloadError(limit_exceeded)
            return
        all_limit = config_dict['QUEUE_ALL']
        dl_limit = config_dict['QUEUE_DOWNLOAD']
        if all_limit or dl_limit:
            added_to_queue = False
            async with queue_dict_lock:
                dl = len(non_queued_dl)
                up = len(non_queued_up)
                if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                    added_to_queue = True
                    queued_dl[self.__listener.uid] = ['yt', link, path, name, qual, playlist, args, self.__listener]
            if added_to_queue:
                LOGGER.info(f"Added to Queue/Download: {self.name}")
                async with download_dict_lock:
                    download_dict[self.__listener.uid] = QueueStatus(self.name, self.__size, self.__gid, self.__listener, 'Dl')
                await self.__listener.onDownloadStart()
                await sendStatusMessage(self.__listener.message)
                return
        async with queue_dict_lock:
            non_queued_dl.add(self.__listener.uid)
        await sync_to_async(self.__download, link, path)

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self.name}")
        if not self.__downloading:
            await self.__listener.onDownloadError("Download Cancelled by User!")

    def __set_args(self, args):
        args = args.split('|')
        for arg in args:
            xy = arg.split(':', 1)
            karg = xy[0].strip()
            if karg == 'format':
                continue
            varg = xy[1].strip()
            if varg.startswith('^'):
                varg = int(varg.split('^')[1])
            elif varg.lower() == 'true':
                varg = True
            elif varg.lower() == 'false':
                varg = False
            elif varg.startswith(('{', '[', '(')) and varg.endswith(('}', ']', ')')):
                varg = eval(varg)
            self.opts[karg] = varg