from bot import (
    LOGGER,
    subprocess_lock
)
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time,
    MirrorStatus
)
from subprocess import run as frun
from time import time
from bot.helper.ext_utils.files_utils import get_path_size


class MetaStatus:
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

    def name(self):
        return self.listener.name

    def size(self):
        return get_readable_file_size(self._size)

    def status(self):
        return MirrorStatus.STATUS_METADATA

    def task(self):
        return self

    async def cancel_task(self):
        LOGGER.info(f"Cancelling metadata editor: {self.listener.name}")
        self.listener.isCancelled = True
        async with subprocess_lock:
            if (
                self.listener.suproc is not None
                and self.listener.suproc.returncode is None
            ):
                self.listener.suproc.kill()
        await self.listener.onUploadError("Metadata editing stopped by user!")
