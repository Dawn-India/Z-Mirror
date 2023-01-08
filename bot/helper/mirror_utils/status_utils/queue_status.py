from bot import LOGGER
from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size


class QueueStatus:
    def __init__(self, name, size, gid, listener, state):
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.__state = state
        self.message = listener.message
        self.source = self.__source()
        self.engine = "Queue System v1.0"

    def gid(self):
        return self.__gid

    def name(self):
        return self.__name

    def size_raw(self):
        return self.__size

    def size(self):
        return get_readable_file_size(self.__size)

    def status(self):
        if self.__state == 'Dl':
            return MirrorStatus.STATUS_QUEUEDL
        else:
            return MirrorStatus.STATUS_QUEUEUP

    def processed_bytes(self):
        return 0

    def progress(self):
        return '0%'

    def speed(self):
        return '0B/s'

    def eta(self):
        return '-'

    def download(self):
        return self

    def cancel_download(self):
        LOGGER.info(f'Cancelling Queue{self.__state}: {self.__name}')
        if self.__state == 'Dl':
            self.__listener.onDownloadError('task have been removed from queue/download')
        else:
            self.__listener.onUploadError('task have been removed from queue/upload')

    def __source(self):
        reply_to = self.message.reply_to_message
        return reply_to.from_user.username or reply_to.from_user.id if reply_to and \
            not reply_to.from_user.is_bot else self.message.from_user.username \
                or self.message.from_user.id

    def mode(self):
        return self.__listener.mode
