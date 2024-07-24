from aiofiles.os import (
    path as aiopath,
    listdir,
    makedirs,
    remove
)
from aioshutil import move
from asyncio import (
    sleep,
    gather
)
from html import escape
from requests import utils as rutils
from time import time

from bot import (
    Intervals,
    aria2,
    DOWNLOAD_DIR,
    task_dict,
    task_dict_lock,
    LOGGER,
    DATABASE_URL,
    config_dict,
    non_queued_up,
    non_queued_dl,
    queued_up,
    queued_dl,
    queue_dict_lock,
)
from bot.helper.common import TaskConfig
from bot.helper.ext_utils.bot_utils import (
    extra_btns,
    sync_to_async
)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.files_utils import (
    get_path_size,
    clean_download,
    clean_target,
    join_files,
)
from bot.helper.ext_utils.links_utils import is_gdrive_id
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time
)
from bot.helper.ext_utils.task_manager import (
    start_from_queued,
    check_running_tasks
)
from bot.helper.task_utils.gdrive_utils.upload import gdUpload
from bot.helper.task_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.task_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.task_utils.status_utils.queue_status import QueueStatus
from bot.helper.task_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.task_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.task_utils.telegram_uploader import TgUploader
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    sendMessage,
    delete_status,
    update_status_message,
)


class TaskListener(TaskConfig):
    def __init__(self):
        super().__init__()
        self.time = time()

    async def clean(self):
        try:
            if st := Intervals["status"]:
                for intvl in list(st.values()):
                    intvl.cancel()
            Intervals["status"].clear()
            await gather(
                sync_to_async(aria2.purge),
                delete_status()
            )
        except:
            pass

    def removeFromSameDir(self):
        if (
            self.sameDir # type: ignore
            and self.mid
            in self.sameDir["tasks"] # type: ignore
        ):
            self.sameDir["tasks"].remove(self.mid) # type: ignore
            self.sameDir["total"] -= 1 # type: ignore

    async def onDownloadStart(self):
        if (
            DATABASE_URL
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await DbManager().add_download_url(
                self.raw_url,
                self.tag
            )
        if (
            self.isSuperChat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and DATABASE_URL
        ):
            await DbManager().add_incomplete_task(
                self.message.chat.id, # type: ignore
                self.message.link, # type: ignore
                self.tag
            )

    async def onDownloadComplete(self):
        multi_links = False
        if (
            DATABASE_URL
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await DbManager().remove_download(self.raw_url)
        if (
            self.sameDir # type: ignore
            and self.mid
            in self.sameDir["tasks"] # type: ignore
        ):
            while not (
                self.sameDir["total"] in [1, 0] # type: ignore
                or self.sameDir["total"] > 1 # type: ignore
                and len(self.sameDir["tasks"]) > 1 # type: ignore
            ):
                await sleep(0.5)

        async with task_dict_lock:
            if (
                self.sameDir # type: ignore
                and self.sameDir["total"] > 1 # type: ignore
                and self.mid
                in self.sameDir["tasks"] # type: ignore
            ):
                self.sameDir["tasks"].remove(self.mid) # type: ignore
                self.sameDir["total"] -= 1 # type: ignore
                folder_name = self.sameDir["name"] # type: ignore
                spath = f"{self.dir}{folder_name}"
                des_path = (
                    f"{DOWNLOAD_DIR}{list(self.sameDir["tasks"])[0]}{folder_name}" # type: ignore
                )
                await makedirs(
                    des_path,
                    exist_ok=True
                )
                for item in await listdir(spath):
                    if item.endswith((
                        ".aria2",
                        ".!qB"
                    )):
                        continue
                    item_path = f"{self.dir}{folder_name}/{item}"
                    if item in await listdir(des_path):
                        await move(
                            item_path,
                            f"{des_path}/{self.mid}-{item}"
                        )
                    else:
                        await move(
                            item_path,
                            f"{des_path}/{item}"
                        )
                multi_links = True
            download = task_dict[self.mid]
            self.name = download.name()
            gid = download.gid()
        LOGGER.info(f"Download completed: {self.name}")

        if not (
            self.isTorrent or
            self.isQbit
        ):
            self.seed = False

        unwanted_files = []
        unwanted_files_size = []
        files_to_delete = []

        if multi_links:
            await self.onUploadError("Downloaded! Waiting for other tasks...")
            return

        if not await aiopath.exists(f"{self.dir}/{self.name}"):
            try:
                files = await listdir(self.dir)
                self.name = files[-1]
                if self.name == "yt-dlp-thumb":
                    self.name = files[0]
            except Exception as e:
                await self.onUploadError(str(e))
                return

        up_path = f"{self.dir}/{self.name}"
        self.size = await get_path_size(up_path)
        if not config_dict["QUEUE_ALL"]:
            async with queue_dict_lock:
                if self.mid in non_queued_dl:
                    non_queued_dl.remove(self.mid)
            await start_from_queued()

        if self.join and await aiopath.isdir(up_path):
            await join_files(up_path)

        if self.extract and not self.isNzb:
            up_path = await self.proceedExtract(
                up_path,
                gid
            )
            if self.isCancelled:
                return
            (
                up_dir,
                self.name
            ) = up_path.rsplit(
                "/",
                1
            )
            self.size = await get_path_size(up_dir)

        if self.nameSub:
            up_path = await self.substitute(up_path)
            if self.isCancelled:
                return
            self.name = up_path.rsplit("/", 1)[1]

        if self.screenShots:
            up_path = await self.generateScreenshots(up_path)
            if self.isCancelled:
                return
            (
                up_dir,
                self.name
            ) = up_path.rsplit(
                "/",
                1
            )
            self.size = await get_path_size(up_dir)

        if self.convertAudio or self.convertVideo:
            up_path = await self.convertMedia(
                up_path,
                gid,
                unwanted_files,
                unwanted_files_size,
                files_to_delete
            )
            if self.isCancelled:
                return
            (
                up_dir,
                self.name
            ) = up_path.rsplit(
                "/",
                1
            )
            self.size = await get_path_size(up_dir)

        if self.sampleVideo:
            up_path = await self.generateSampleVideo(
                up_path,
                gid,
                unwanted_files,
                files_to_delete
            )
            if self.isCancelled:
                return
            (
                up_dir,
                self.name
            ) = up_path.rsplit(
                "/",
                1
            )
            self.size = await get_path_size(up_dir)

        if self.compress:
            up_path = await self.proceedCompress(
                up_path,
                gid,
                unwanted_files,
                files_to_delete
            )
            if self.isCancelled:
                return

        (
            up_dir,
            self.name
        ) = up_path.rsplit(
            "/",
            1
        )
        self.size = await get_path_size(up_dir)

        if self.isLeech and not self.compress:
            await self.proceedSplit(
                up_dir,
                unwanted_files_size,
                unwanted_files,
                gid
            )
            if self.isCancelled:
                return

        (
            add_to_queue,
            event
        ) = await check_running_tasks(
            self,
            "up"
        )
        await start_from_queued()
        if add_to_queue:
            LOGGER.info(f"Added to Queue/Upload: {self.name}")
            async with task_dict_lock:
                task_dict[self.mid] = QueueStatus(
                    self,
                    gid,
                    "Up"
                )
            await event.wait() # type: ignore
            if self.isCancelled:
                return
            async with queue_dict_lock:
                non_queued_up.add(self.mid)
            LOGGER.info(f"Start from Queued/Upload: {self.name}")

        self.size = await get_path_size(up_dir)
        for s in unwanted_files_size:
            self.size -= s

        if self.isLeech:
            LOGGER.info(f"Leech Name: {self.name}")
            tg = TgUploader(
                self,
                up_dir
            )
            async with task_dict_lock:
                task_dict[self.mid] = TelegramStatus(
                    self,
                    tg,
                    gid,
                    "up",
                )
            await gather(
                update_status_message(self.message.chat.id), # type: ignore
                tg.upload(
                    unwanted_files,
                    files_to_delete
                ),
            )
        elif is_gdrive_id(self.upDest): # type: ignore
            LOGGER.info(f"Gdrive Upload Name: {self.name}")
            drive = gdUpload(
                self,
                up_path
            )
            async with task_dict_lock:
                task_dict[self.mid] = GdriveStatus(
                    self,
                    drive,
                    gid,
                    "up",
                )
            await gather(
                update_status_message(self.message.chat.id), # type: ignore
                sync_to_async(
                    drive.upload,
                    unwanted_files,
                    files_to_delete
                ),
            )
        else:
            LOGGER.info(f"Rclone Upload Name: {self.name}")
            RCTransfer = RcloneTransferHelper(self)
            async with task_dict_lock:
                task_dict[self.mid] = RcloneStatus(
                    self,
                    RCTransfer,
                    gid,
                    "up",
                )
            await gather(
                update_status_message(self.message.chat.id), # type: ignore
                RCTransfer.upload(
                    up_path,
                    unwanted_files,
                    files_to_delete
                ),
            )

    async def onUploadComplete(
        self,
        link,
        files,
        folders,
        mime_type,
        rclonePath="",
        dir_id=""
    ):
        if (
            DATABASE_URL
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await DbManager().remove_download(self.raw_url)
        if (
            self.isSuperChat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and DATABASE_URL
        ):
            await DbManager().rm_complete_task(self.message.link) # type: ignore
        LOGGER.info(f"Task Done: {self.name}")
        lmsg = (
            f"<b><i>{escape(self.name)}</i></b>"
            f"\n<b>cc</b>: <i>{self.tag}</i>"
        )
        gmsg = f"\n<b>Hey {self.tag}!\nYour job is done.</b>"
        msg = (
            f"\n\n<blockquote><code>Size  </code>: {get_readable_file_size(self.size)}"
            f"\n<code>Past  </code>: {get_readable_time(time() - self.time)}"
            f"\n<code>Mode  </code>: {self.mode}"
        )
        _msg = (
            ""
            if rclonePath == ""
            else f"\n\n<code>Path  </code>: {rclonePath}"
        )
        msg_ = "\n\n<b><i>Link has been sent in your DM.</b></i>"
        if self.isLeech:
            msg += f"\n<code>Files </code>: {folders}</blockquote>\n"
            if mime_type != 0:
                msg += f"<code>Error </code>: {mime_type}\n"
            msg_ = "\n<b><i>Files has been sent in your DM.</b></i>"
            if not self.dmMessage:
                if not files:
                    await sendMessage(
                        self.message, # type: ignore
                        lmsg + msg
                    )
                    if self.logMessage:
                        await sendMessage(
                            self.logMessage,
                            lmsg + msg
                        )
                else:
                    fmsg = "\n"
                    for index, (
                        link,
                        self.name
                    ) in enumerate(
                        files.items(),
                        start=1
                    ):
                        fmsg += f"{index}. <a href='{link}'>{self.name}</a>\n"
                        if len(fmsg.encode() + msg.encode()) > 4000:
                            if self.logMessage:
                                await sendMessage(
                                    self.logMessage,
                                    lmsg + msg + fmsg
                                )
                            await sendMessage(
                                self.message, # type: ignore
                                lmsg + msg + fmsg
                            )
                            await sleep(1)
                            fmsg = "\n"
                    if fmsg != "\n":
                        if self.logMessage:
                            await sendMessage(
                                self.logMessage,
                                lmsg + msg + fmsg
                            )
                        await sendMessage(
                            self.message, # type: ignore
                            lmsg + msg + fmsg
                        )
            else:
                if not files:
                    await sendMessage(
                        self.message, # type: ignore
                        gmsg + msg + msg_
                    )
                    if self.logMessage:
                        await sendMessage(
                            self.logMessage,
                            lmsg + msg
                        )
                elif (
                    self.dmMessage
                    and not config_dict["DUMP_CHAT_ID"]
                ):
                    await sendMessage(
                        self.message, # type: ignore
                        gmsg + msg + msg_
                    )
                    if self.logMessage:
                        await sendMessage(
                            self.logMessage,
                            lmsg + msg
                        )
                else:
                    fmsg = "\n"
                    for index, (
                        link,
                        self.name
                    ) in enumerate(
                        files.items(),
                        start=1
                    ):
                        fmsg += f"{index}. <a href='{link}'>{self.name}</a>\n"
                        if len(fmsg.encode() + msg.encode()) > 4000:
                            if self.logMessage:
                                await sendMessage(
                                    self.logMessage,
                                    lmsg + msg + fmsg
                                )
                            await sleep(1)
                            fmsg = "\n"
                    if fmsg != "\n":
                        if self.logMessage:
                            await sendMessage(
                                self.logMessage,
                                lmsg + msg + fmsg
                            )
                        await sendMessage(
                            self.message, # type: ignore
                            gmsg + msg + msg_
                        )
        else:
            msg += f"\n<code>Type  </code>: {mime_type}</blockquote>"
            if mime_type == "Folder":
                msg += f"\n<code>Files </code>: {files}"
                msg += f"\n<code>Folder</code>: {folders}"
            if (
                link
                or rclonePath
                and config_dict["RCLONE_SERVE_URL"]
            ):
                buttons = ButtonMaker()
                if link:
                    if (
                        link.startswith("https://drive.google.com/")
                        and not config_dict["DISABLE_DRIVE_LINK"]
                    ):
                        buttons.ubutton(
                            "♻️ Drive Link",
                            link,
                            "header"
                        )
                    elif not link.startswith("https://drive.google.com/"):
                        buttons.ubutton(
                            "☁️ Cloud Link",
                            link,
                            "header"
                        )
                if (
                    rclonePath
                    and (
                        RCLONE_SERVE_URL := config_dict["RCLONE_SERVE_URL"]
                    )
                ):
                    remote, path = rclonePath.split(
                        ":",
                        1
                    )
                    url_path = rutils.quote(f"{path}") # type: ignore
                    share_url = f"{RCLONE_SERVE_URL}/{remote}/{url_path}"
                    if mime_type == "Folder":
                        share_url += "/"
                    buttons.ubutton(
                        "🔗 Rclone Link",
                        share_url
                    )
                elif not rclonePath:
                    INDEX_URL = ""
                    if self.privateLink:
                        INDEX_URL = self.userDict.get(
                            "index_url",
                            ""
                        ) or ""
                    elif config_dict["INDEX_URL"]:
                        INDEX_URL = config_dict["INDEX_URL"]
                    if INDEX_URL:
                        share_url = f"{INDEX_URL}findpath?id={dir_id}"
                        if mime_type == "Folder":
                            buttons.ubutton(
                                "📁 Direct Link",
                                share_url
                            )
                        else:
                            buttons.ubutton(
                                "🔗 Direct Link",
                                share_url
                            )
                            if mime_type.startswith(
                                (
                                    "image",
                                    "video",
                                    "audio"
                                )
                            ):
                                share_urls = f"{INDEX_URL}findpath?id={dir_id}&view=true"
                                buttons.ubutton(
                                    "🌐 View Link",
                                    share_urls
                                )
                buttons = extra_btns(buttons)
                if self.dmMessage:
                    await sendMessage(
                        self.dmMessage,
                        lmsg + msg + _msg,
                        buttons.build_menu(2)
                    )
                    await sendMessage(
                        self.message, # type: ignore
                        gmsg + msg + msg_
                    )
                else:
                    await sendMessage(
                        self.message, # type: ignore
                        lmsg + msg + _msg,
                        buttons.build_menu(2)
                    )
                if self.logMessage:
                    if (
                        link.startswith("https://drive.google.com/")
                        and config_dict["DISABLE_DRIVE_LINK"]
                    ):
                        buttons.ubutton(
                            "♻️ Drive Link",
                            link,
                            "header"
                        )
                    await sendMessage(
                        self.logMessage,
                        lmsg + msg + _msg,
                        buttons.build_menu(2)
                    )
            else:
                if self.dmMessage:
                    await sendMessage(
                        self.message, # type: ignore
                        gmsg + msg + msg_
                    )
                    await sendMessage(
                        self.dmMessage,
                        lmsg + msg + _msg
                    )
                else:
                    await sendMessage(
                        self.message, # type: ignore
                        lmsg + msg + _msg + msg_
                    )
                if self.logMessage:
                    await sendMessage(
                        self.logMessage,
                        lmsg + msg + _msg
                    )
        if self.seed:
            if self.newDir:
                await clean_target(self.newDir)
            async with queue_dict_lock:
                if (
                    self.mid
                    in non_queued_up
                ):
                    non_queued_up.remove(self.mid)
            await start_from_queued()
            return
        await clean_download(self.dir)
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id) # type: ignore

        async with queue_dict_lock:
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()

    async def onDownloadError(self, error, button=None):
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
            self.removeFromSameDir()
        msg = f"Sorry {self.tag}!\nYour download has been stopped."
        msg += f"\n\n<code>Reason </code>: {escape(str(error))}"
        msg += f"\n<code>Past   </code>: {get_readable_time(time() - self.time)}"
        msg += f"\n<code>Mode   </code>: {self.mode}"
        tlmsg = await sendMessage(
            self.message, # type: ignore
            msg,
            button
        )
        await auto_delete_message(
            self.message, # type: ignore
            tlmsg
        )
        if self.logMessage:
            await sendMessage(
                self.logMessage,
                msg,
                button
            )
        if self.dmMessage:
            await sendMessage(
                self.dmMessage,
                msg,
                button
            )
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id) # type: ignore

        if (
            DATABASE_URL
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await DbManager().remove_download(self.raw_url)

        if (
            self.isSuperChat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and DATABASE_URL
        ):
            await DbManager().rm_complete_task(self.message.link) # type: ignore

        async with queue_dict_lock:
            if self.mid in queued_dl:
                queued_dl[self.mid].set()
                del queued_dl[self.mid]
            if self.mid in queued_up:
                queued_up[self.mid].set()
                del queued_up[self.mid]
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()
        await delete_links(self.message) # type: ignore
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)
        if (
            self.thumb and
            await aiopath.exists(self.thumb)
        ):
            await remove(self.thumb)

    async def onUploadError(self, error):
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        msg = f"Sorry {self.tag}!\nYour upload has been stopped."
        msg += f"\n\n<code>Reason </code>: {escape(str(error))}"
        msg += f"\n<code>Past   </code>: {get_readable_time(time() - self.time)}"
        msg += f"\n<code>Mode   </code>: {self.mode}"
        tlmsg = await sendMessage(
            self.message, # type: ignore
            msg
        )
        await auto_delete_message(
            self.message, # type: ignore
            tlmsg
        )
        if self.logMessage:
            await sendMessage(
                self.logMessage,
                msg
            )
        if self.dmMessage:
            await sendMessage(
                self.dmMessage,
                msg,
            )
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id) # type: ignore

        if (
            DATABASE_URL
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await DbManager().remove_download(self.raw_url)

        if (
            self.isSuperChat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and DATABASE_URL
        ):
            await DbManager().rm_complete_task(self.message.link) # type: ignore

        async with queue_dict_lock:
            if self.mid in queued_dl:
                queued_dl[self.mid].set()
                del queued_dl[self.mid]
            if self.mid in queued_up:
                queued_up[self.mid].set()
                del queued_up[self.mid]
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()
        await delete_links(self.message) # type: ignore
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)
        if (
            self.thumb and
            await aiopath.exists(self.thumb)
        ):
            await remove(self.thumb)
