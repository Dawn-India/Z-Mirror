from pkg_resources import get_distribution

from bot import DOWNLOAD_DIR
from bot.helper.ext_utils.bot_utils import (MirrorStatus,
                                            get_readable_file_size,
                                            get_readable_time)
from bot.helper.ext_utils.fs_utils import get_path_size

engine_ = f"yt-dlp v{get_distribution('yt-dlp').version}"

class YtDlpDownloadStatus:
    def __init__(self, obj, listener, gid):
        self.__obj = obj
        self.__uid = listener.uid
        self.__gid = gid
        self.__listener = listener
        self.message = self.__listener.message
        self.__isPlayList = self.__obj.is_playlist
        self.startTime = self.__listener.startTime
        self.mode = self.__listener.mode
        self.source = self.__source()
        self.engine = engine_

    def playList(self):
        if self.__isPlayList:
            return f"{self.__obj.playlist_index} of {self.__obj.playlist_count}"
        else:
            return None

    def gid(self):
        return self.__gid

    def processed_bytes(self):
        if self.__obj.downloaded_bytes != 0:
          return self.__obj.downloaded_bytes
        else:
          return get_path_size(f"{DOWNLOAD_DIR}{self.__uid}")

    def size_raw(self):
        return self.__obj.size

    def size(self):
        return get_readable_file_size(self.size_raw())

    def status(self):
        return MirrorStatus.STATUS_DOWNLOADING

    def name(self):
        return self.__obj.name

    def progress_raw(self):
        return self.__obj.progress

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed_raw(self):
        """
        :return: Download speed in Bytes/Seconds
        """
        return self.__obj.download_speed

    def listener(self):
        return self.__listener

    def speed(self):
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def eta(self):
        if self.__obj.eta != '-':
            return f'{get_readable_time(self.__obj.eta)}'
        try:
            seconds = (self.size_raw() - self.processed_bytes()) / self.speed_raw()
            return f'{get_readable_time(seconds)}'
        except:
            return '-'

    def download(self):
        return self.__obj

    def __source(self):
        reply_to = self.message.reply_to_message
        source = reply_to.from_user.username or reply_to.from_user.id if reply_to and \
            not reply_to.from_user.is_bot else self.message.from_user.username \
                or self.message.from_user.id
        return f"<a href='{self.message.link}'>{source}</a>"
