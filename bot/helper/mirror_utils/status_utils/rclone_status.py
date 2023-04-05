from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size


class RcloneStatus:
    def __init__(self, obj, message, status, extra_details):
        self.__obj = obj
        self.__status = status
        self.message = message
        self.extra_details = extra_details
        self.engine = "Rclone v1.62.2"

    def gid(self):
        return self.__obj.gid

    def progress(self):
        return self.__obj.percentage

    def speed(self):
        return self.__obj.speed

    def name(self):
        return self.__obj.name

    def size(self):
        return get_readable_file_size(self.__obj.size)

    def eta(self):
        return self.__obj.eta

    def status(self):
        if self.__status == 'dl':
            return MirrorStatus.STATUS_DOWNLOADING
        else:
            return MirrorStatus.STATUS_UPLOADING

    def processed_bytes(self):
        return self.__obj.transferred_size

    def download(self):
        return self.__obj