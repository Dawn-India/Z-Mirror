from time import time
from bot import LOGGER
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
    MirrorStatus
)
from subprocess import run as frun
from bot.helper.ext_utils.files_utils import get_path_size


class MediaConvertStatus:
    def __init__(
            self,
            listener,
            gid
        ):
        self.listener = listener
        self._gid = gid
        self._size = self.listener.size
        self._start_time = time()
        self._proccessed_bytes = 0
        self.engine = f"FFmpeg v{self._eng_ver()}"

    def _eng_ver(self):
        _engine = frun(
            [
                "ffmpeg",
                "-version"
            ],
            capture_output=True,
            text=True
        )
        return _engine.stdout.split("\n")[0].split(" ")[2].split("-")[0]

    def gid(self):
        return self._gid

    def speed_raw(self):
        return self._proccessed_bytes / (time() - self._start_time)

    async def progress_raw(self):
        await self.processed_raw()
        try:
            return self._proccessed_bytes / self._size * 100
        except:
            return 0

    async def progress(self):
        return f"{round(await self.progress_raw(), 2)}%"

    def speed(self):
        return f"{get_readable_file_size(self.speed_raw())}/s" # type: ignore

    def name(self):
        return self.listener.name

    def size(self):
        return get_readable_file_size(self._size)

    def eta(self):
        try:
            seconds = (self._size - self._proccessed_bytes) / self.speed_raw()
            return get_readable_time(seconds)
        except:
            return "-"

    def status(self):
        return MirrorStatus.STATUS_CONVERTING

    async def processed_raw(self):
        if self.listener.newDir:
            self._proccessed_bytes = await get_path_size(self.listener.newDir)
        else:
            self._proccessed_bytes = await get_path_size(self.listener.dir) - self._size

    def processed_bytes(self):
        return get_readable_file_size(self._proccessed_bytes)

    def task(self):
        return self

    async def cancel_task(self):
        LOGGER.info(f"Cancelling Converting: {self.listener.name}")
        self.listener.isCancelled = True
        if self.listener.suproc is not None and self.listener.suproc.returncode is None:
            self.listener.suproc.kill()
        await self.listener.onUploadError("Converting stopped by user!")
