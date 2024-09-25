from time import time

from bot import aria2, LOGGER
from ...ext_utils.bot_utils import sync_to_async
from ...ext_utils.status_utils import (
    MirrorStatus,
    get_readable_time
)


def get_download(gid, old_info=None):
    try:
        res = aria2.get_download(gid)
        return (
            res or
            old_info
        )
    except Exception as e:
        LOGGER.error(f"{e}: Aria2c, Error while getting torrent info")
        return old_info


class Aria2Status:

    def __init__(
            self,
            listener,
            gid,
            seeding=False,
            queued=False
        ):
        self._gid = gid
        self._download = None
        self.listener = listener
        self.queued = queued
        self.start_time = 0
        self.seeding = seeding
        self.engine = f"Aria2c v{self._eng_ver()}"

    def _eng_ver(self):
        return aria2.client.get_version()["version"]

    def update(self):
        if self._download is None:
            self._download = get_download(
                self._gid,
                self._download
            )
        else:
            self._download = self._download.live
        if self._download.followed_by_ids: # type: ignore
            self._gid = self._download.followed_by_ids[0] # type: ignore
            self._download = get_download(self._gid)

    def progress(self):
        return self._download.progress_string() # type: ignore

    def processed_bytes(self):
        return self._download.completed_length_string() # type: ignore

    def speed(self):
        return self._download.download_speed_string() # type: ignore

    def name(self):
        return self._download.name # type: ignore

    def size(self):
        return self._download.total_length_string() # type: ignore

    def eta(self):
        try:
            return self._download.eta_string() # type: ignore
        except:
            return "-"

    def status(self):
        self.update()
        if self._download.is_waiting or self.queued: # type: ignore
            if self.seeding:
                return MirrorStatus.STATUS_QUEUEUP
            else:
                return MirrorStatus.STATUS_QUEUEDL
        elif self._download.is_paused: # type: ignore
            return MirrorStatus.STATUS_PAUSED
        elif self._download.seeder and self.seeding: # type: ignore
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        return self._download.num_seeders # type: ignore

    def leechers_num(self):
        return self._download.connections # type: ignore

    def uploaded_bytes(self):
        return self._download.upload_length_string() # type: ignore

    def seed_speed(self):
        return self._download.upload_speed_string() # type: ignore

    def ratio(self):
        return f"{round(self._download.upload_length / self._download.completed_length, 3)}" # type: ignore

    def seeding_time(self):
        return get_readable_time(
            time() - self.start_time # type: ignore
        )

    def task(self):
        return self

    def gid(self):
        return self._gid

    async def cancel_task(self):
        self.listener.is_cancelled = True
        await sync_to_async(self.update)
        if self._download.seeder and self.seeding: # type: ignore
            LOGGER.info(f"Cancelling Seed: {self.name()}")
            await self.listener.on_upload_error(
                f"Seeding stopped with Ratio: {self.ratio()} and Time: {self.seeding_time()}"
            )
            await sync_to_async(
                aria2.remove,
                [self._download],
                force=True,
                files=True
            )
        elif downloads := self._download.followed_by: # type: ignore
            LOGGER.info(f"Cancelling Download: {self.name()}")
            await self.listener.on_download_error("Download cancelled by user!")
            downloads.append(self._download)
            await sync_to_async(
                aria2.remove,
                downloads,
                force=True,
                files=True
            )
        else:
            if self.queued:
                LOGGER.info(f"Cancelling QueueDl: {self.name()}")
                msg = "task have been removed from queue/download"
            else:
                LOGGER.info(f"Cancelling Download: {self.name()}")
                msg = "Download stopped by user!"
            await self.listener.on_download_error(msg)
            await sync_to_async(
                aria2.remove,
                [self._download],
                force=True,
                files=True
            )
