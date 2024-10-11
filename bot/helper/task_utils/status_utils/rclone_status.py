from ...ext_utils.status_utils import MirrorStatus
from subprocess import run as rrun


class RcloneStatus:
    def __init__(
            self,
            listener,
            obj,
            gid,
            status
        ):
        self._obj = obj
        self._gid = gid
        self._status = status
        self.listener = listener
        self.engine = f"Rclone {self._eng_ver()}"

    def _eng_ver(self):
        _engine = rrun(
            [
                "rclone",
                "version"
            ],
            capture_output=True,
            text=True
        )
        return _engine.stdout.split("\n")[0].split(" ")[1]

    def gid(self):
        return self._gid

    def progress(self):
        return self._obj.percentage

    def speed(self):
        return self._obj.speed

    def name(self):
        return self.listener.name

    def size(self):
        return self._obj.size

    def eta(self):
        return self._obj.eta

    def status(self):
        if self._status == "dl":
            return MirrorStatus.STATUS_DOWNLOADING
        elif self._status == "up":
            return MirrorStatus.STATUS_UPLOADING
        else:
            return MirrorStatus.STATUS_CLONING

    def processed_bytes(self):
        return self._obj.transferred_size

    def task(self):
        return self._obj
