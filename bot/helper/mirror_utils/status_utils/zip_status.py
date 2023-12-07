#!/usr/bin/env python3
from time import time

from bot import LOGGER, subprocess_lock
from bot.helper.ext_utils.bot_utils import (MirrorStatus, async_to_sync,
                                            get_readable_file_size,
                                            get_readable_time)
from bot.helper.ext_utils.fs_utils import get_path_size
from subprocess import run as zrun


def _eng_ver():
    _engine = zrun(['7z', '-version'], capture_output=True, text=True)
    return _engine.stdout.split('\n')[2].split(' ')[2]


class ZipStatus:
    def __init__(self, name, size, gid, listener):
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.__start_time = time()
        self.message = self.__listener.message
        self.extra_details = self.__listener.extra_details
        self.engine = f'p7zip v{_eng_ver()}'

    def gid(self):
        return self.__gid

    def speed_raw(self):
        return self.processed_raw() / (time() - self.__start_time)

    def progress_raw(self):
        try:
            return self.processed_raw() / self.__size * 100
        except:
            return 0

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def name(self):
        return self.__name

    def size(self):
        return get_readable_file_size(self.__size)

    def eta(self):
        try:
            seconds = (self.__size - self.processed_raw()) / self.speed_raw()
            return get_readable_time(seconds)
        except:
            return '-'

    def status(self):
        return MirrorStatus.STATUS_ARCHIVING

    def processed_raw(self):
        if self.__listener.newDir:
            return async_to_sync(get_path_size, self.__listener.newDir)
        else:
            return async_to_sync(get_path_size, self.__listener.dir) - self.__size

    def processed_bytes(self):
        return get_readable_file_size(self.processed_raw())

    def download(self):
        return self

    async def cancel_download(self):
        LOGGER.info(f'Cancelling Archive: {self.__name}')
        async with subprocess_lock:
            if (
                self.__listener.suproc is not None
                and self.__listener.suproc.returncode is None
            ):
                self.__listener.suproc.kill()
            else:
                self.__listener.suproc = "cancelled"
        await self.__listener.onUploadError('Archiving stopped by user!')
