from bot.helper.ext_utils.files_utils import get_path_size
from bot.helper.ext_utils.status_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)
from pkg_resources import get_distribution


class YtDlpDownloadStatus:
    def __init__(self, listener, obj, gid):
        self._obj = obj
        self._gid = gid
        self.listener = listener
        self._proccessed_bytes = 0
        self.engine = f"Yt-Dlp v{self._eng_ver()}"
        self._isPlayList = self._obj.is_playlist

    def _eng_ver(self):
        return get_distribution("yt-dlp").version

    def playList(self):
        if self._isPlayList:
            return f"{self._obj.playlist_index} / {self._obj.playlist_count}"
        else:
            return None

    def gid(self):
        return self._gid

    def processed_bytes(self):
        return get_readable_file_size(self._proccessed_bytes)

    async def processed_raw(self):
        if self._obj.downloaded_bytes != 0:
            self._proccessed_bytes = self._obj.downloaded_bytes
        else:
            self._proccessed_bytes = await get_path_size(self.listener.dir)

    def size(self):
        return get_readable_file_size(self._obj.size)

    def status(self):
        return MirrorStatus.STATUS_DOWNLOADING

    def name(self):
        return self.listener.name

    async def progress(self):
        await self.processed_raw()
        return f"{round(self._obj.progress, 2)}%"

    def speed(self):
        return f"{get_readable_file_size(self._obj.download_speed)}/s"

    def eta(self):
        if self._obj.eta != "-":
            return get_readable_time(self._obj.eta)
        try:
            seconds = (
                self._obj.size - self._proccessed_bytes
            ) / self._obj.download_speed
            return get_readable_time(seconds)
        except:
            return "-"

    def task(self):
        return self._obj
