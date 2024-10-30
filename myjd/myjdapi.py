from json import (
    dumps,
    loads,
    JSONDecodeError
)
from httpx import (
    AsyncClient,
    RequestError
)
from httpx import AsyncHTTPTransport
from functools import wraps

from .exception import (
    MYJDApiException,
    MYJDConnectionException,
    MYJDDecodeException
)


class System:
    def __init__(self, device):
        self.device = device
        self.url = "/system"

    async def exit_jd(self):
        return await self.device.action(f"{self.url}/exitJD")

    async def restart_jd(self):
        return await self.device.action(f"{self.url}/restartJD")

    async def hibernate_os(self):
        return await self.device.action(f"{self.url}/hibernateOS")

    async def shutdown_os(self, force):
        params = force
        return await self.device.action(f"{self.url}/shutdownOS", params)

    async def standby_os(self):
        return await self.device.action(f"{self.url}/standbyOS")

    async def get_storage_info(self):
        return await self.device.action(f"{self.url}/getStorageInfos?path")


class Jd:
    def __init__(self, device):
        self.device = device
        self.url = "/jd"

    async def get_core_revision(self):
        return await self.device.action(f"{self.url}/getCoreRevision")

    async def version(self):
        return await self.device.action(f"{self.url}/version")


class Config:

    def __init__(self, device):
        self.device = device
        self.url = "/config"

    async def list(self, params=None):
        if params is None:
            return await self.device.action(
                f"{self.url}/list",
                params
            )
        else:
            return await self.device.action(f"{self.url}/list")

    async def listEnum(self, type):
        return await self.device.action(
            f"{self.url}/listEnum",
            params=[type]
        )

    async def get(self, interface_name, storage, key):
        params = [interface_name, storage, key]
        return await self.device.action(
            f"{self.url}/get",
            params
        )

    async def getDefault(self, interfaceName, storage, key):
        params = [interfaceName, storage, key]
        return await self.device.action(
            f"{self.url}/getDefault",
            params
        )

    async def query(self, params=None):
        if params is None:
            params = [
                {
                    "configInterface": "",
                    "defaultValues": True,
                    "description": True,
                    "enumInfo": True,
                    "includeExtensions": True,
                    "pattern": "",
                    "values": True,
                }
            ]
        return await self.device.action(
            f"{self.url}/query",
            params
        )

    async def reset(self, interfaceName, storage, key):
        params = [
            interfaceName,
            storage,
            key
        ]
        return await self.device.action(
            f"{self.url}/reset",
            params
        )

    async def set(self, interface_name, storage, key, value):
        params = [
            interface_name,
            storage,
            key,
            value
        ]
        return await self.device.action(
            f"{self.url}/set",
            params
        )


class DownloadController:

    def __init__(self, device):
        self.device = device
        self.url = "/downloadcontroller"

    async def start_downloads(self):
        return await self.device.action(f"{self.url}/start")

    async def stop_downloads(self):
        return await self.device.action(f"{self.url}/stop")

    async def pause_downloads(self, value):
        params = [value]
        return await self.device.action(
            f"{self.url}/pause",
            params
        )

    async def get_speed_in_bytes(self):
        return await self.device.action(f"{self.url}/getSpeedInBps")

    async def force_download(self, link_ids, package_ids):
        params = [
            link_ids,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/force_download",
            params
        )

    async def get_current_state(self):
        return await self.device.action(f"{self.url}/getCurrentState")


class Extension:
    def __init__(self, device):
        self.device = device
        self.url = "/extensions"

    async def list(self, params=None):
        if params is None:
            params = [
                {
                    "configInterface": True,
                    "description": True,
                    "enabled": True,
                    "iconKey": True,
                    "name": True,
                    "pattern": "",
                    "installed": True,
                }
            ]
        return await self.device.action(
            f"{self.url}/list",
            params=params
        )

    async def install(self, id):
        return await self.device.action(
            f"{self.url}/install",
            params=[id]
        )

    async def isInstalled(self, id):
        return await self.device.action(
            f"{self.url}/isInstalled",
            params=[id]
        )

    async def isEnabled(self, id):
        return await self.device.action(
            f"{self.url}/isEnabled",
            params=[id]
        )

    async def setEnabled(self, id, enabled):
        return await self.device.action(
            f"{self.url}/setEnabled",
            params=[id, enabled]
        )


class Linkgrabber:

    def __init__(self, device):
        self.device = device
        self.url = "/linkgrabberv2"

    async def clear_list(self):
        return await self.device.action(f"{self.url}/clearList")

    async def move_to_downloadlist(self, link_ids=None, package_ids=None):
        if link_ids is None:
            link_ids = []
        if package_ids is None:
            package_ids = []
        params = [link_ids, package_ids]
        return await self.device.action(
            f"{self.url}/moveToDownloadlist",
            params
        )

    async def query_links(self, params=None):
        if params is None:
            params = [
                {
                    "bytesTotal": True,
                    "comment": True,
                    "status": True,
                    "enabled": True,
                    "maxResults": -1,
                    "startAt": 0,
                    "hosts": True,
                    "url": True,
                    "availability": True,
                    "variantIcon": True,
                    "variantName": True,
                    "variantID": True,
                    "variants": True,
                    "priority": True,
                }
            ]
        return await self.device.action(
            f"{self.url}/queryLinks",
            params
        )

    async def cleanup(
        self,
        action,
        mode,
        selection_type,
        link_ids=None,
        package_ids=None
    ):
        if link_ids is None:
            link_ids = []
        if package_ids is None:
            package_ids = []
        params = [
            link_ids,
            package_ids
        ]
        params += [
            action,
            mode,
            selection_type
        ]
        return await self.device.action(
            f"{self.url}/cleanup",
            params
        )

    async def add_container(self, type_, content):
        params = [
            type_,
            content
        ]
        return await self.device.action(
            f"{self.url}/addContainer",
            params
        )

    async def get_download_urls(self, link_ids, package_ids, url_display_type):
        params = [
            package_ids,
            link_ids,
            url_display_type
        ]
        return await self.device.action(
            f"{self.url}/getDownloadUrls",
            params
        )

    async def set_priority(self, priority, link_ids, package_ids):
        params = [
            priority,
            link_ids,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/setPriority",
            params
        )

    async def set_enabled(self, enable, link_ids, package_ids):
        params = [
            enable,
            link_ids,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/setEnabled",
            params
        )

    async def get_variants(self, params):
        return await self.device.action(
            f"{self.url}/getVariants",
            params
        )

    async def add_links(self, params=None):
        if params is None:
            params = [
                {
                    "autostart": False,
                    "links": None,
                    "packageName": None,
                    "extractPassword": None,
                    "priority": "DEFAULT",
                    "downloadPassword": None,
                    "destinationFolder": None,
                    "overwritePackagizerRules": False,
                }
            ]
        return await self.device.action(
            f"{self.url}/addLinks",
            params
        )

    async def is_collecting(self):
        return await self.device.action(f"{self.url}/isCollecting")

    async def set_download_directory(self, dir: str, package_ids: list):
        params = [
            dir,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/setDownloadDirectory",
            params
        )

    async def move_to_new_package(
        self,
        name: str,
        path: str,
        link_ids: list = None,
        package_ids: list = None
    ):
        if link_ids is None:
            link_ids = []
        if package_ids is None:
            package_ids = []
        params = [
            link_ids,
            package_ids,
            name,
            path
        ]
        return await self.device.action(
            f"{self.url}/movetoNewPackage",
            params
        )

    async def remove_links(self, link_ids=None, package_ids=None):
        if link_ids is None:
            link_ids = []
        if package_ids is None:
            package_ids = []
        params = [
            link_ids,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/removeLinks",
            params
        )

    async def rename_link(self, link_id, new_name):
        params = [
            link_id,
            new_name
        ]
        return await self.device.action(
            f"{self.url}/renameLink",
            params
        )

    async def get_package_count(self):
        return await self.device.action(f"{self.url}/getPackageCount")

    async def rename_package(self, package_id, new_name):
        params = [
            package_id,
            new_name
        ]
        return await self.device.action(
            f"{self.url}/renamePackage",
            params
        )

    async def query_packages(self, params=None):
        if params is None:
            params = [
                {
                    "availableOfflineCount": True,
                    "availableOnlineCount": True,
                    "availableTempUnknownCount": True,
                    "availableUnknownCount": True,
                    "bytesTotal": True,
                    "childCount": True,
                    "comment": True,
                    "enabled": True,
                    "hosts": True,
                    "maxResults": -1,
                    "packageUUIDs": [],
                    "priority": True,
                    "saveTo": True,
                    "startAt": 0,
                    "status": True,
                }
            ]
        return await self.device.action(
            f"{self.url}/queryPackages",
            params
        )


class Downloads:

    def __init__(self, device):
        self.device = device
        self.url = "/downloadsV2"

    async def query_links(self, params=None):
        if params is None:
            params = [
                {
                    "addedDate": True,
                    "bytesLoaded": True,
                    "bytesTotal": True,
                    "comment": True,
                    "enabled": True,
                    "eta": True,
                    "extractionStatus": True,
                    "finished": True,
                    "finishedDate": True,
                    "host": True,
                    "jobUUIDs": [],
                    "maxResults": -1,
                    "packageUUIDs": [],
                    "password": True,
                    "priority": True,
                    "running": True,
                    "skipped": True,
                    "speed": True,
                    "startAt": 0,
                    "status": True,
                    "url": True,
                }
            ]
        return await self.device.action(
            f"{self.url}/queryLinks",
            params
        )

    async def query_packages(self, params=None):
        if params is None:
            params = [
                {
                    "bytesLoaded": True,
                    "bytesTotal": True,
                    "childCount": True,
                    "comment": True,
                    "enabled": True,
                    "eta": True,
                    "finished": True,
                    "hosts": True,
                    "maxResults": -1,
                    "packageUUIDs": [],
                    "priority": True,
                    "running": True,
                    "saveTo": True,
                    "speed": True,
                    "startAt": 0,
                    "status": True,
                }
            ]
        return await self.device.action(
            f"{self.url}/queryPackages",
            params
        )

    async def cleanup(
        self,
        action,
        mode,
        selection_type,
        link_ids=None,
        package_ids=None
    ):
        if link_ids is None:
            link_ids = []
        if package_ids is None:
            package_ids = []
        params = [
            link_ids,
            package_ids
        ]
        params += [
            action,
            mode,
            selection_type
        ]
        return await self.device.action(
            f"{self.url}/cleanup",
            params
        )

    async def set_enabled(self, enable, link_ids, package_ids):
        params = [
            enable,
            link_ids,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/setEnabled",
            params
        )

    async def force_download(self, link_ids=None, package_ids=None):
        if link_ids is None:
            link_ids = []
        if package_ids is None:
            package_ids = []
        params = [
            link_ids,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/force_download",
            params
        )

    async def set_dl_location(self, directory, package_ids=None):
        if package_ids is None:
            package_ids = []
        params = [
            directory,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/setDownloadDirectory",
            params
        )

    async def remove_links(self, link_ids=None, package_ids=None):
        if link_ids is None:
            link_ids = []
        if package_ids is None:
            package_ids = []
        params = [
            link_ids,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/removeLinks",
            params
        )

    async def reset_links(self, link_ids, package_ids):
        params = [
            link_ids,
            package_ids
        ]
        return await self.device.action(
            f"{self.url}/resetLinks",
            params
        )

    async def move_to_new_package(
        self,
        link_ids,
        package_ids,
        new_pkg_name,
        download_path
    ):
        params = [
            link_ids,
            package_ids,
            new_pkg_name,
            download_path
        ]
        return await self.device.action(
            f"{self.url}/movetoNewPackage",
            params
        )

    async def rename_link(self, link_id: list, new_name: str):
        params = [
            link_id,
            new_name
        ]
        return await self.device.action(
            f"{self.url}/renameLink",
            params
        )


class Captcha:

    def __init__(self, device):
        self.device = device
        self.url = "/captcha"

    async def list(self):
        return await self.device.action(
            f"{self.url}/list",
            []
        )

    async def get(self, captcha_id):
        return await self.device.action(
            f"{self.url}/get",
            (captcha_id,)
        )

    async def solve(self, captcha_id, solution):
        return await self.device.action(
            f"{self.url}/solve",
            (
                captcha_id,
                solution
            )
        )


class Jddevice:

    def __init__(self, jd):

        self.myjd = jd
        self.config = Config(self)
        self.linkgrabber = Linkgrabber(self)
        self.captcha = Captcha(self)
        self.downloads = Downloads(self)
        self.downloadcontroller = DownloadController(self)
        self.extensions = Extension(self)
        self.jd = Jd(self)
        self.system = System(self)

    async def ping(self):
        return await self.action("/device/ping")

    async def action(self, path, params=()):
        response = await self.myjd.request_api(
            path,
            params
        )
        if response is None:
            raise (MYJDConnectionException("No connection established\n"))
        return response["data"]


class clientSession(AsyncClient):

    @wraps(AsyncClient.request)
    async def request(self, method: str, url: str, **kwargs):
        kwargs.setdefault(
            "timeout",
            3
        )
        kwargs.setdefault(
            "follow_redirects",
            True
        )
        return await super().request(
            method,
            url,
            **kwargs
        )


class MyJdApi:

    def __init__(self):
        self.__api_url = "http://127.0.0.1:3128"
        self._http_session = None
        self.device = Jddevice(self)

    def _session(self):
        if self._http_session is not None:
            return self._http_session

        transport = AsyncHTTPTransport(
            retries=10,
            verify=False
        )
        self._http_session = clientSession(transport=transport)
        self._http_session.verify = False
        return self._http_session

    async def request_api(self, path, params=None):
        session = self._session()
        params_request = (
            params
            if params is not None
            else []
        )
        params_request = {"params": params_request}
        data = dumps(params_request)
        data = data.replace(
            '"null"',
            "null"
        )
        data = data.replace(
            "'null'",
            "null"
        )
        request_url = self.__api_url + path
        try:
            res = await session.request(
                "POST",
                request_url,
                headers={"Content-Type": "application/json; charset=utf-8"},
                content=data,
            )
            response = res.text
        except RequestError:
            return None
        if res.status_code != 200:
            try:
                error_msg = loads(response)
            except JSONDecodeError as exc:
                raise MYJDDecodeException(
                    "Failed to decode response: {}",
                    response
                ) from exc
            msg = (
                "\n\tSOURCE: "
                + error_msg["src"]
                + "\n\tTYPE: "
                + error_msg["type"]
                + "\n------\nREQUEST_URL: "
                + self.__api_url
                + path
            )
            msg += "\n"
            if data is not None:
                msg += "DATA:\n" + data
            raise (
                MYJDApiException.get_exception(
                    error_msg["src"],
                    error_msg["type"],
                    msg
                )
            )
        return loads(response)
