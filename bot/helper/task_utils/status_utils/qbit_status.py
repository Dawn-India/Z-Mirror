from asyncio import sleep, gather

from bot import (
    LOGGER,
    qbittorrent_client,
    qb_torrents,
    qb_listener_lock
)
from ...ext_utils.bot_utils import sync_to_async
from ...ext_utils.status_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)


def get_download(tag, old_info=None):
    try:
        res = qbittorrent_client.torrents_info(tag=tag)[0]
        return res or old_info
    except Exception as e:
        LOGGER.error(f"{e}: Qbittorrent, while getting torrent info. Tag: {tag}")
        return old_info


class QbittorrentStatus:
    def __init__(
            self,
            listener,
            seeding=False,
            queued=False
        ):
        self.queued = queued
        self.seeding = seeding
        self.listener = listener
        self._info = None
        self.engine = f"qBit {self._eng_ver()}"

    def _eng_ver(self):
        return qbittorrent_client.app.version

    def update(self):
        self._info = get_download(
            f"{self.listener.mid}",
            self._info
        )

    def progress(self):
        return f"{round(self._info.progress * 100, 2)}%" # type: ignore

    def processed_bytes(self):
        return get_readable_file_size(self._info.downloaded) # type: ignore

    def speed(self):
        return f"{get_readable_file_size(self._info.dlspeed)}/s" # type: ignore

    def name(self):
        if self._info.state in [ # type: ignore
            "metaDL",
            "checkingResumeData"
        ]:
            return f"[METADATA]{self.listener.name}"
        else:
            return self.listener.name

    def size(self):
        return get_readable_file_size(self._info.size) # type: ignore

    def eta(self):
        return (
            get_readable_time(eta)
            if (
                eta := self._info.get( # type: ignore
                    "eta",
                    False
                )
            )
            else "-"
        )

    def status(self):
        self.update()
        state = self._info.state # type: ignore
        if state == "queuedDL" or self.queued:
            return MirrorStatus.STATUS_QUEUEDL
        elif state == "queuedUP":
            return MirrorStatus.STATUS_QUEUEUP
        elif state in [
            "pausedDL",
            "pausedUP"
        ]:
            return MirrorStatus.STATUS_PAUSED
        elif state in [
            "checkingUP",
            "checkingDL"
        ]:
            return MirrorStatus.STATUS_CHECKING
        elif state in [
            "stalledUP",
            "uploading"
        ] and self.seeding:
            return MirrorStatus.STATUS_SEEDING
        else:
            return MirrorStatus.STATUS_DOWNLOADING

    def seeders_num(self):
        return self._info.num_seeds # type: ignore

    def leechers_num(self):
        return self._info.num_leechs # type: ignore

    def uploaded_bytes(self):
        return get_readable_file_size(self._info.uploaded) # type: ignore

    def seed_speed(self):
        return f"{get_readable_file_size(self._info.upspeed)}/s" # type: ignore

    def ratio(self):
        return f"{round(self._info.ratio, 3)}" # type: ignore

    def seeding_time(self):
        return get_readable_time(self._info.seeding_time) # type: ignore

    def task(self):
        return self

    def gid(self):
        return self.hash()[:12]

    def hash(self):
        return self._info.hash # type: ignore

    async def cancel_task(self):
        self.listener.is_cancelled = True
        await sync_to_async(self.update)
        await sync_to_async(
            qbittorrent_client.torrents_pause,
            torrent_hashes=self._info.hash # type: ignore
        )
        if not self.seeding:
            if self.queued:
                LOGGER.info(f"Cancelling QueueDL: {self.name()}")
                msg = "task have been removed from queue/download"
            else:
                LOGGER.info(f"Cancelling Download: {self._info.name}") # type: ignore
                msg = "Download stopped by user!"
            await sleep(0.3)
            await gather(
                self.listener.on_download_error(msg),
                sync_to_async(
                    qbittorrent_client.torrents_delete,
                    torrent_hashes=self._info.hash, # type: ignore
                    delete_files=True,
                ),
                sync_to_async(
                    qbittorrent_client.torrents_delete_tags,
                    tags=self._info.tags # type: ignore
                ),
            )
            async with qb_listener_lock:
                if self._info.tags in qb_torrents: # type: ignore
                    del qb_torrents[self._info.tags] # type: ignore
