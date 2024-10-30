from aiofiles.os import (
    path as aiopath,
    listdir,
    makedirs,
    remove
)
from aioshutil import move
from asyncio import (
    gather,
    sleep
)
from html import escape
from requests import utils as rutils
from time import time

from bot import (
    DOWNLOAD_DIR,
    LOGGER,
    aria2,
    config_dict,
    intervals,
    non_queued_dl,
    non_queued_up,
    queued_dl,
    queued_up,
    queue_dict_lock,
    same_directory_lock,
    task_dict,
    task_dict_lock
)
from ..common import TaskConfig
from ..ext_utils.bot_utils import (
    extra_btns,
    sync_to_async
)
from ..ext_utils.db_handler import database
from ..ext_utils.files_utils import (
    clean_download,
    clean_target,
    get_path_size,
    join_files
)
from ..ext_utils.links_utils import is_gdrive_id
from ..ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time
)
from ..ext_utils.task_manager import (
    check_running_tasks,
    start_from_queued
)
from ..task_utils.gdrive_utils.upload import GoogleDriveUpload
from ..task_utils.rclone_utils.transfer import RcloneTransferHelper
from ..task_utils.status_utils.gdrive_status import GoogleDriveStatus
from ..task_utils.status_utils.queue_status import QueueStatus
from ..task_utils.status_utils.rclone_status import RcloneStatus
from ..task_utils.status_utils.telegram_status import TelegramStatus
from ..task_utils.telegram_uploader import TelegramUploader
from ..telegram_helper.button_build import ButtonMaker
from ..telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    delete_status,
    send_message,
    update_status_message,
)


class TaskListener(TaskConfig):
    def __init__(self):
        super().__init__()
        self.time = time()

    async def clean(self):
        try:
            if st := intervals["status"]:
                for intvl in list(st.values()):
                    intvl.cancel()
            intervals["status"].clear()
            await gather(
                sync_to_async(aria2.purge),
                delete_status()
            )
        except:
            pass

    async def remove_from_same_dir(self):
        async with task_dict_lock:
            if (
                self.folder_name
                and self.same_dir # type: ignore
                and self.mid in self.same_dir[self.folder_name]["tasks"] # type: ignore
            ):
                self.same_dir[self.folder_name]["tasks"].remove(self.mid) # type: ignore
                self.same_dir[self.folder_name]["total"] -= 1 # type: ignore

    async def on_download_start(self):
        if (
            config_dict["DATABASE_URL"]
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await database.add_download_url(
                self.raw_url,
                self.tag
            )
        if (
            self.is_super_chat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and config_dict["DATABASE_URL"]
        ):
            await database.add_incomplete_task(
                self.message.chat.id, # type: ignore
                self.message.link, # type: ignore
                self.tag
            )

    async def on_download_complete(self):
        await sleep(2)
        multi_links = False
        if (
            config_dict["DATABASE_URL"]
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await database.remove_download(self.raw_url)
        if (
            self.folder_name
            and self.same_dir # type: ignore
            and self.mid in self.same_dir[self.folder_name]["tasks"] # type: ignore
        ):
            async with same_directory_lock:
                while True:
                    async with task_dict_lock:
                        if self.mid not in self.same_dir[self.folder_name]["tasks"]: # type: ignore
                            return
                        if (
                            self.mid in self.same_dir[self.folder_name]["tasks"] # type: ignore
                            and (
                                self.same_dir[self.folder_name]["total"] <= 1 # type: ignore
                                or len(self.same_dir[self.folder_name]["tasks"]) > 1 # type: ignore
                            )
                        ):
                            if self.same_dir[self.folder_name]["total"] > 1: # type: ignore
                                self.same_dir[self.folder_name]["tasks"].remove(self.mid) # type: ignore
                                self.same_dir[self.folder_name]["total"] -= 1 # type: ignore
                                spath = f"{self.dir}{self.folder_name}"
                                des_id = list(self.same_dir[self.folder_name]["tasks"])[0] # type: ignore
                                des_path = f"{DOWNLOAD_DIR}{des_id}{self.folder_name}"
                                await makedirs(
                                    des_path,
                                    exist_ok=True
                                )
                                LOGGER.info(f"Moving files from {self.mid} to {des_id}")
                                for item in await listdir(spath):
                                    if item.endswith((
                                        ".aria2",
                                        ".!qB"
                                    )):
                                        continue
                                    item_path = f"{self.dir}{self.folder_name}/{item}"
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
                            break
                    await sleep(1)
        async with task_dict_lock:
            download = task_dict[self.mid]
            self.name = download.name()
            gid = download.gid()
        LOGGER.info(f"Download completed: {self.name}")

        if not (
            self.is_torrent or
            self.is_qbit
        ):
            self.seed = False

        unwanted_files = []
        unwanted_files_size = []
        files_to_delete = []

        if multi_links:
            await self.on_upload_error(f"{self.name} Downloaded!\n\nWaiting for other tasks to finish...")
            return

        if self.folder_name:
            self.name = self.folder_name.split("/")[-1]

        if not await aiopath.exists(f"{self.dir}/{self.name}"):
            try:
                files = await listdir(self.dir)
                self.name = files[-1]
                if self.name == "yt-dlp-thumb":
                    self.name = files[0]
            except Exception as e:
                await self.on_upload_error(str(e))
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

        if self.extract and not self.is_nzb:
            up_path = await self.proceed_extract(
                up_path,
                gid
            )
            if self.is_cancelled:
                return
            (
                up_dir,
                self.name
            ) = up_path.rsplit(
                "/",
                1
            )
            self.size = await get_path_size(up_dir)

        if self.name_sub:
            up_path = await self.substitute(up_path)
            if self.is_cancelled:
                return
            self.name = up_path.rsplit("/", 1)[1]

        if self.screen_shots:
            up_path = await self.generate_screenshots(up_path)
            if self.is_cancelled:
                return
            (
                up_dir,
                self.name
            ) = up_path.rsplit(
                "/",
                1
            )
            self.size = await get_path_size(up_dir)

        if self.convert_audio or self.convert_video:
            up_path = await self.convert_media(
                up_path,
                gid,
                unwanted_files,
                unwanted_files_size,
                files_to_delete
            )
            if self.is_cancelled:
                return
            (
                up_dir,
                self.name
            ) = up_path.rsplit(
                "/",
                1
            )
            self.size = await get_path_size(up_dir)

        if self.sample_video:
            up_path = await self.generate_sample_video(
                up_path,
                gid,
                unwanted_files,
                files_to_delete
            )
            if self.is_cancelled:
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
            up_path = await self.proceed_compress(
                up_path,
                gid,
                unwanted_files,
                files_to_delete
            )
            if self.is_cancelled:
                return

        (
            up_dir,
            self.name
        ) = up_path.rsplit(
            "/",
            1
        )
        self.size = await get_path_size(up_dir)

        if self.metadata:
            await self.proceedMetadata(
                up_path,
                gid
            )
            if self.is_cancelled:
                return

        if self.m_attachment:
            await self.proceedAttachment(
                up_path,
                gid
            )
            if self.is_cancelled:
                return

        if self.is_leech and not self.compress:
            await self.proceed_split(
                up_dir,
                unwanted_files_size,
                unwanted_files,
                gid
            )
            if self.is_cancelled:
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
            if self.is_cancelled:
                return
            LOGGER.info(f"Start from Queued/Upload: {self.name}")

        self.size = await get_path_size(up_dir)
        for s in unwanted_files_size:
            self.size -= s

        if self.is_leech:
            LOGGER.info(f"Leech Name: {self.name}")
            tg = TelegramUploader(
                self,
                up_dir
            )
            async with task_dict_lock:
                task_dict[self.mid] = TelegramStatus(
                    self,
                    tg,
                    gid,
                    "up"
                )
            await gather(
                update_status_message(self.message.chat.id), # type: ignore
                tg.upload(
                    unwanted_files,
                    files_to_delete
                )
            )
        elif is_gdrive_id(self.up_dest): # type: ignore
            LOGGER.info(f"Gdrive Upload Name: {self.name}")
            drive = GoogleDriveUpload(
                self,
                up_path
            )
            async with task_dict_lock:
                task_dict[self.mid] = GoogleDriveStatus(
                    self,
                    drive,
                    gid,
                    "up"
                )
            await gather(
                update_status_message(self.message.chat.id), # type: ignore
                sync_to_async(
                    drive.upload,
                    unwanted_files,
                    files_to_delete
                )
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
            config_dict["DATABASE_URL"]
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await database.remove_download(self.raw_url)
        if (
            self.is_super_chat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and config_dict["DATABASE_URL"]
        ):
            await database.rm_complete_task(self.message.link) # type: ignore
        LOGGER.info(f"Task Done: {self.name}")
        lmsg = (
            f"<b><i>{escape(self.name)}</i></b>"
            f"\n<b>cc</b>: <i>{self.tag}</i>"
        )
        gmsg = f"\n<b>Hey {self.tag}!\nYour job is done.</b>"
        msg = (
            f"\n\n<code>Size  </code>: {get_readable_file_size(self.size)}"
            f"\n<code>Past  </code>: {get_readable_time(time() - self.time)}"
            f"\n<code>Mode  </code>: {self.mode}"
        )
        _msg = (
            ""
            if rclonePath == ""
            else f"\n\n<code>Path  </code>: {rclonePath}"
        )
        msg_ = "\n\n<b><i>Link has been sent in your DM.</b></i>"
        if self.is_leech:
            msg += f"\n<code>Files </code>: {folders}\n"
            if mime_type != 0:
                msg += f"<code>Error </code>: {mime_type}\n"
            msg_ = "\n<b><i>Files has been sent in your DM.</b></i>"
            if not self.dm_message:
                if not files:
                    await send_message(
                        self.message, # type: ignore
                        lmsg + msg
                    )
                    if self.log_message:
                        await send_message(
                            self.log_message,
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
                            if self.log_message:
                                await send_message(
                                    self.log_message,
                                    lmsg + msg + fmsg
                                )
                            await send_message(
                                self.message, # type: ignore
                                lmsg + msg + fmsg
                            )
                            await sleep(1)
                            fmsg = "\n"
                    if fmsg != "\n":
                        if self.log_message:
                            await send_message(
                                self.log_message,
                                lmsg + msg + fmsg
                            )
                        await send_message(
                            self.message, # type: ignore
                            lmsg + msg + fmsg
                        )
            else:
                if not files:
                    await send_message(
                        self.message, # type: ignore
                        gmsg + msg + msg_
                    )
                    if self.log_message:
                        await send_message(
                            self.log_message,
                            lmsg + msg
                        )
                elif (
                    self.dm_message
                    and not config_dict["DUMP_CHAT_ID"]
                ):
                    await send_message(
                        self.message, # type: ignore
                        gmsg + msg + msg_
                    )
                    if self.log_message:
                        await send_message(
                            self.log_message,
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
                            if self.log_message:
                                await send_message(
                                    self.log_message,
                                    lmsg + msg + fmsg
                                )
                            await sleep(1)
                            fmsg = "\n"
                    if fmsg != "\n":
                        if self.log_message:
                            await send_message(
                                self.log_message,
                                lmsg + msg + fmsg
                            )
                        await send_message(
                            self.message, # type: ignore
                            gmsg + msg + msg_
                        )
        else:
            msg += f"\n<code>Type  </code>: {mime_type}"
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
                        buttons.url_button(
                            "ᴅʀɪᴠᴇ\nʟɪɴᴋ",
                            link,
                            "header"
                        )
                    elif not link.startswith("https://drive.google.com/"):
                        buttons.url_button(
                            "ᴄʟᴏᴜᴅ\nʟɪɴᴋ",
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
                    buttons.url_button(
                        "ʀᴄʟᴏɴᴇ\nʟɪɴᴋ",
                        share_url
                    )
                elif not rclonePath:
                    INDEX_URL = ""
                    if self.private_link:
                        INDEX_URL = self.user_dict.get(
                            "index_url",
                            ""
                        ) or ""
                    elif config_dict["INDEX_URL"]:
                        INDEX_URL = config_dict["INDEX_URL"]
                    if INDEX_URL:
                        share_url = f"{INDEX_URL}findpath?id={dir_id}"
                        if mime_type == "Folder":
                            buttons.url_button(
                                "ᴅɪʀᴇᴄᴛ\nꜰɪʟᴇ ʟɪɴᴋ",
                                share_url
                            )
                        else:
                            buttons.url_button(
                                "ᴅɪʀᴇᴄᴛ\nꜰᴏʟᴅᴇʀ ʟɪɴᴋ",
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
                                buttons.url_button(
                                    "ᴠɪᴇᴡ\nʟɪɴᴋ",
                                    share_urls
                                )
                buttons = extra_btns(buttons)
                if self.dm_message:
                    await send_message(
                        self.dm_message,
                        lmsg + msg + _msg,
                        buttons.build_menu(2)
                    )
                    await send_message(
                        self.message, # type: ignore
                        gmsg + msg + msg_
                    )
                else:
                    await send_message(
                        self.message, # type: ignore
                        lmsg + msg + _msg,
                        buttons.build_menu(2)
                    )
                if self.log_message:
                    if (
                        link.startswith("https://drive.google.com/")
                        and config_dict["DISABLE_DRIVE_LINK"]
                    ):
                        buttons.url_button(
                            "ᴅʀɪᴠᴇ\nʟɪɴᴋ",
                            link,
                            "header"
                        )
                    await send_message(
                        self.log_message,
                        lmsg + msg + _msg,
                        buttons.build_menu(2)
                    )
            else:
                if self.dm_message:
                    await send_message(
                        self.message, # type: ignore
                        gmsg + msg + msg_
                    )
                    await send_message(
                        self.dm_message,
                        lmsg + msg + _msg
                    )
                else:
                    await send_message(
                        self.message, # type: ignore
                        lmsg + msg + _msg + msg_
                    )
                if self.log_message:
                    await send_message(
                        self.log_message,
                        lmsg + msg + _msg
                    )
        if self.seed:
            if self.new_dir:
                await clean_target(self.new_dir)
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

    async def on_download_error(self, error, button=None):
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        await self.remove_from_same_dir()
        msg = f"Sorry {self.tag}!\nYour download has been stopped."
        msg += f"\n\n<code>Reason </code>: {escape(str(error))}"
        msg += f"\n<code>Past   </code>: {get_readable_time(time() - self.time)}"
        msg += f"\n<code>Mode   </code>: {self.mode}"
        tlmsg = await send_message(
            self.message, # type: ignore
            msg,
            button
        )
        await auto_delete_message(
            self.message, # type: ignore
            tlmsg
        )
        if self.log_message:
            await send_message(
                self.log_message,
                msg,
                button
            )
        if self.dm_message:
            await send_message(
                self.dm_message,
                msg,
                button
            )
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id) # type: ignore

        if (
            config_dict["DATABASE_URL"]
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await database.remove_download(self.raw_url)

        if (
            self.is_super_chat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and config_dict["DATABASE_URL"]
        ):
            await database.rm_complete_task(self.message.link) # type: ignore

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
        if self.new_dir:
            await clean_download(self.new_dir)
        if (
            self.thumb and
            await aiopath.exists(self.thumb)
        ):
            await remove(self.thumb)

    async def on_upload_error(self, error):
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        msg = f"Sorry {self.tag}!\nYour upload has been stopped."
        msg += f"\n\n<code>Reason </code>: {escape(str(error))}"
        msg += f"\n<code>Past   </code>: {get_readable_time(time() - self.time)}"
        msg += f"\n<code>Mode   </code>: {self.mode}"
        tlmsg = await send_message(
            self.message, # type: ignore
            msg
        )
        await auto_delete_message(
            self.message, # type: ignore
            tlmsg
        )
        if self.log_message:
            await send_message(
                self.log_message,
                msg
            )
        if self.dm_message:
            await send_message(
                self.dm_message,
                msg,
            )
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id) # type: ignore

        if (
            config_dict["DATABASE_URL"]
            and config_dict["STOP_DUPLICATE_TASKS"]
            and self.raw_url
        ):
            await database.remove_download(self.raw_url)

        if (
            self.is_super_chat
            and config_dict["INCOMPLETE_TASK_NOTIFIER"]
            and config_dict["DATABASE_URL"]
        ):
            await database.rm_complete_task(self.message.link) # type: ignore

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
        if self.new_dir:
            await clean_download(self.new_dir)
        if (
            self.thumb and
            await aiopath.exists(self.thumb)
        ):
            await remove(self.thumb)
