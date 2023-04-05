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
        self.extra_details = self.__listener.extra_details
        self.engine = engine_

    def gid(self):
        return self.__gid

    def processed_bytes(self):
        return get_readable_file_size(self.__obj.downloaded_bytes)

    def size(self):
        return get_readable_file_size(self.__obj.size)

    def status(self):
        return MirrorStatus.STATUS_DOWNLOADING

    def name(self):
        return self.__obj.name

    def progress_raw(self):
        return self.__obj.progress

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.__obj.download_speed)}/s'

    def listener(self):
        return self.__listener

    def eta(self):
        try:
            seconds = (self.__obj.size - self.__obj.downloaded_bytes) / self.__obj.download_speed
            return f'{get_readable_time(seconds)}'
        except:
            return '-'

    def download(self):
        return self.__obj