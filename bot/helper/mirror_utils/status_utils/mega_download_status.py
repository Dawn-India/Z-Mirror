from mega import MegaApi

from bot.helper.ext_utils.bot_utils import (MirrorStatus,
                                            get_readable_file_size,
                                            get_readable_time)

engine_ = f"MegaSDK v{MegaApi('test').getVersion()}"

class MegaDownloadStatus:

    def __init__(self, obj, listener):
        self.__listener = listener
        self.__obj = obj
        self.message = self.__listener.message
        self.startTime = self.__listener.startTime
        self.mode = self.__listener.mode
        self.source = self.__source()
        self.engine = engine_

    def name(self) -> str:
        return self.__obj.name

    def progress_raw(self):
        try:
            return round(self.processed_bytes() / self.__obj.size * 100,2)
        except:
            return 0.0

    def progress(self):
        """Progress of download in percentage"""
        return f"{self.progress_raw()}%"

    def status(self) -> str:
        return MirrorStatus.STATUS_DOWNLOADING

    def processed_bytes(self):
        return self.__obj.downloaded_bytes

    def eta(self):
        try:
            seconds = (self.size_raw() - self.processed_bytes()) / self.speed_raw()
            return f'{get_readable_time(seconds)}'
        except ZeroDivisionError:
            return '-'

    def size_raw(self):
        return self.__obj.size

    def size(self) -> str:
        return get_readable_file_size(self.size_raw())

    def downloaded(self) -> str:
        return get_readable_file_size(self.__obj.downloadedBytes)

    def speed_raw(self):
        return self.__obj.speed

    def listener(self):
        return self.__listener

    def speed(self) -> str:
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def gid(self) -> str:
        return self.__obj.gid

    def download(self):
        return self.__obj

    def __source(self):
        reply_to = self.message.reply_to_message
        source = reply_to.from_user.username or reply_to.from_user.id if reply_to and \
            not reply_to.from_user.is_bot else self.message.from_user.username \
                or self.message.from_user.id
        return f"<a href='{self.message.link}'>{source}</a>"
