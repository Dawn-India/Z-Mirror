from pkg_resources import get_distribution

from bot.helper.ext_utils.bot_utils import (MirrorStatus,
                                            get_readable_file_size,
                                            get_readable_time)

engine_ = f"pyrogram v{get_distribution('pyrogram').version}"
class TelegramDownloadStatus:
    def __init__(self, obj, listener, gid):
        self.__obj = obj
        self.__gid = gid
        self.__listener = listener
        self.message = self.__listener.message
        self.startTime = self.__listener.startTime
        self.mode = self.__listener.mode
        self.source = self.__source()
        self.engine = engine_

    def gid(self):
        return self.__gid

    def processed_bytes(self):
        return self.__obj.downloaded_bytes

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

    def speed(self):
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def eta(self):
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
