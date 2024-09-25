from bot import (
    LOGGER,
    subprocess_lock
)
from ...ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
    MirrorStatus
)
from subprocess import run as frun
from time import time
from ...ext_utils.files_utils import get_path_size


class SplitStatus:
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
        self.engine = self._eng_ver()

    def _eng_ver(self):
        if self.listener.as_doc:
            pkg = "Split v"
            _engine = frun(
                [
                    "split",
                    "--version"
                ],
                capture_output=True,
                text=True
            )
            _engine = _engine.stdout.split("\n")[0].split(" ")[3]
            result = f"{pkg}{_engine}"
            return result
        else:
            pkg = "FFmpeg v"
            _engine = frun(
                [
                    "ffmpeg",
                    "-version"
                ],
                capture_output=True,
                text=True
            )
            _engine = _engine.stdout.split("\n")[0].split(" ")[2].split("-")[0]
            result = f"{pkg}{_engine}"
            return result

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
        return MirrorStatus.STATUS_SPLITTING

    async def processed_raw(self):
        if self.listener.new_dir:
            self._proccessed_bytes = await get_path_size(self.listener.new_dir)
        else:
            self._proccessed_bytes = await get_path_size(self.listener.dir) - self._size

    def processed_bytes(self):
        return get_readable_file_size(self._proccessed_bytes)

    def task(self):
        return self

    async def cancel_task(self):
        LOGGER.info(f"Cancelling Split: {self.listener.name}")
        self.listener.is_cancelled = True
        async with subprocess_lock:
            if (
                self.listener.suproc is not None
                and self.listener.suproc.returncode is None
            ):
                self.listener.suproc.kill()
        await self.listener.on_upload_error("splitting stopped by user!")
