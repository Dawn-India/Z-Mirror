from asyncio import gather
from json import loads
from nekozee.filters import command
from nekozee.handlers import MessageHandler
from secrets import token_urlsafe
from aiofiles.os import remove

from bot import (
    LOGGER,
    task_dict,
    task_dict_lock,
    bot,
    bot_loop
)
from ..helper.ext_utils.bot_utils import (
    sync_to_async,
    cmd_exec,
    arg_parser,
    COMMAND_USAGE
)
from ..helper.ext_utils.exceptions import DirectDownloadLinkException
from ..helper.ext_utils.links_utils import (
    is_gdrive_link,
    is_share_link,
    is_rclone_path,
    is_gdrive_id
)
from ..helper.ext_utils.task_manager import (
    limit_checker,
    stop_duplicate_check
)
from ..helper.listeners.task_listener import TaskListener
from ..helper.task_utils.download_utils.direct_link_generator import (
    direct_link_generator
)
from ..helper.task_utils.gdrive_utils.clone import GoogleDriveClone
from ..helper.task_utils.gdrive_utils.count import GoogleDriveCount
from ..helper.task_utils.rclone_utils.transfer import RcloneTransferHelper
from ..helper.task_utils.status_utils.gdrive_status import GoogleDriveStatus
from ..helper.task_utils.status_utils.rclone_status import RcloneStatus
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    send_message,
    delete_message,
    send_status_message
)


class Clone(TaskListener):
    def __init__(
        self,
        client,
        message,
        _=None,
        __=None,
        ___=None,
        ____=None,
        _____=None,
        bulk=None,
        multi_tag=None,
        options="",
    ):
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multi_tag = multi_tag
        self.options = options
        self.same_dir = {}
        self.bulk = bulk
        super().__init__()
        self.is_clone = True

    async def new_event(self):
        self.pmsg = await send_message(
            self.message,
            "Processing your request..."
        )
        text = self.message.text.split("\n")
        input_list = text[0].split(" ")

        args = {
            "link": "",
            "-m": 0,
            "-b": False,
            "-n": "",
            "-up": "",
            "-rcf": "",
            "-sync": False,
        }

        arg_parser(
            input_list[1:],
            args
        )

        try:
            self.multi = int(args["-m"])
        except:
            self.multi = 0

        self.up_dest = args["-up"]
        self.rc_flags = args["-rcf"]
        self.link = args["link"]
        self.name = args["-n"]

        is_bulk = args["-b"]
        sync = args["-sync"]
        bulk_start = 0
        bulk_end = 0
        self.file_ = None

        await self.get_id()

        if not isinstance(is_bulk, bool):
            dargs = is_bulk.split(":")
            bulk_start = dargs[0] or 0
            if len(dargs) == 2:
                bulk_end = dargs[1] or 0
            is_bulk = True

        if is_bulk:
            await delete_message(self.pmsg)
            await self.init_bulk(
                input_list,
                bulk_start,
                bulk_end,
                Clone
            )
            return

        await self.get_tag(text)

        if (
            not self.link
            and (reply_to := self.message.reply_to_message)
        ):
            try:
                self.link = reply_to.text.split(
                    "\n",
                    1
                )[0].strip()
            except:
                hmsg = await send_message(
                    self.message,
                    COMMAND_USAGE["clone"][0],
                    COMMAND_USAGE["clone"][1]
                )
                await delete_message(self.pmsg)
                await auto_delete_message(
                    self.message,
                    hmsg
                )
                return

        await self.run_multi(
            input_list,
            Clone
        )

        if len(self.link) == 0:
            hmsg = await send_message(
                self.message,
                COMMAND_USAGE["clone"][0],
                COMMAND_USAGE["clone"][1]
            )
            await delete_message(self.pmsg)
            await auto_delete_message(
                self.message,
                hmsg
            )
            return
        LOGGER.info(self.link)
        
        if await self.permission_check() != True:
            return
        await delete_message(self.pmsg)

        try:
            await self.before_start()
        except Exception as e:
            emsg = await send_message(
                self.message,
                e
            )
            await auto_delete_message(
                self.message,
                emsg
            )
            return
        await self._proceed_to_clone(sync)

    async def _proceed_to_clone(self, sync):
        if is_share_link(self.link):
            try:
                self.link = await sync_to_async(
                    direct_link_generator,
                    self.link
                )
                LOGGER.info(f"Generated link: {self.link}")
            except DirectDownloadLinkException as e:
                LOGGER.error(str(e))
                if str(e).startswith("ERROR:"):
                    smsg = await send_message(
                        self.message,
                        str(e)
                    )
                    await auto_delete_message(
                        self.message,
                        smsg
                    )
                    return
        if (
            is_gdrive_link(self.link)
            or
            is_gdrive_id(self.link)
        ):
            (
                self.name,
                mime_type,
                self.size,
                files,
                _
            ) = await sync_to_async(
                GoogleDriveCount().count,
                self.link,
                self.user_id
            )
            if mime_type is None:
                smsg = await send_message(
                    self.message,
                    self.name
                )
                await auto_delete_message(
                    self.message,
                    smsg
                )
                return
            msg, button = await stop_duplicate_check(self)
            if msg:
                smsg = await send_message(
                    self.message,
                    msg,
                    button
                )
                await auto_delete_message(
                    self.message,
                    smsg
                )
                return
            if limit_exceeded := await limit_checker(self):
                LOGGER.info(f"Clone Limit Exceeded: Name: {self.name} | Size: {self.size}")
                smsg = await send_message(
                    self.message,
                    limit_exceeded
                )
                await auto_delete_message(
                    self.message,
                    smsg
                )
                return
            await self.on_download_start()
            LOGGER.info(f"Clone Started: Name: {self.name} - Source: {self.link}")
            drive = GoogleDriveClone(self)
            if files <= 10:
                msg = await send_message(
                    self.message,
                    f"Cloning: <code>{self.link}</code>"
                )
                await delete_links(self.message)
            else:
                msg = ""
                gid = token_urlsafe(12).replace(
                    "-",
                    ""
                )
                async with task_dict_lock:
                    task_dict[self.mid] = GoogleDriveStatus(
                        self,
                        drive,
                        gid,
                        "cl"
                    )
                if self.multi <= 1:
                    await send_status_message(self.message)
            (
                flink,
                mime_type,
                files,
                folders,
                dir_id
            ) = await sync_to_async(drive.clone)
            if msg:
                await delete_message(msg)
            if not flink:
                return
            await self.onUploadComplete(
                flink,
                files,
                folders,
                mime_type,
                dir_id=dir_id
            )
            LOGGER.info(f"Cloning Done: {self.name}")
        elif is_rclone_path(self.link):
            if self.link.startswith("mrcc:"):
                self.link = self.link.replace(
                    "mrcc:",
                    "",
                    1
                )
                self.up_dest = self.up_dest.replace(
                    "mrcc:",
                    "",
                    1
                )
                config_path = f"rclone/{self.user_id}.conf"
            else:
                config_path = "rclone.conf"

            (
                remote,
                src_path
            ) = self.link.split(":", 1)
            self.link = src_path.strip("/")
            if self.link.startswith("rclone_select"):
                mime_type = "Folder"
                src_path = ""
                if not self.name:
                    self.name = self.link
            else:
                src_path = self.link
                cmd = [
                    "rclone",
                    "lsjson",
                    "--fast-list",
                    "--stat",
                    "--no-modtime",
                    "--config",
                    config_path,
                    f"{remote}:{src_path}",
                ]
                res = await cmd_exec(cmd)
                if res[2] != 0:
                    if res[2] != -9:
                        msg = f"Error: While getting rclone stat. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}"
                        smsg = await send_message(
                            self.message,
                            msg
                        )
                        await auto_delete_message(
                            self.message,
                            smsg
                        )
                    return
                rstat = loads(res[0])
                if rstat["IsDir"]:
                    if not self.name:
                        self.name = (
                            src_path.rsplit(
                                "/",
                                1
                            )[-1]
                            if src_path
                            else remote
                        )
                    self.up_dest += (
                        self.name
                        if self.up_dest.endswith(":")
                        else f"/{self.name}"
                    )

                    mime_type = "Folder"
                else:
                    if not self.name:
                        self.name = src_path.rsplit(
                            "/",
                            1
                        )[-1]
                    mime_type = rstat["MimeType"]

            await self.on_download_start()

            RCTransfer = RcloneTransferHelper(self)
            LOGGER.info(
                f"Clone Started: Name: {self.name} - Source: {self.link} - Destination: {self.up_dest}"
            )
            gid = token_urlsafe(12).replace(
                "-",
                ""
            )
            async with task_dict_lock:
                task_dict[self.mid] = RcloneStatus(
                    self,
                    RCTransfer,
                    gid,
                    "cl"
                )
            if self.multi <= 1:
                await send_status_message(self.message)
            method = (
                "sync"
                if sync
                else "copy"
            )
            (
                flink,
                destination
            ) = await RCTransfer.clone(
                config_path,
                remote,
                src_path,
                mime_type,
                method,
            ) # type: ignore
            if self.link.startswith("rclone_select"):
                await remove(self.link)
            if not destination:
                return
            LOGGER.info(f"Cloning Done: {self.name}")
            cmd1 = [
                "rclone",
                "lsf",
                "--fast-list",
                "-R",
                "--files-only",
                "--config",
                config_path,
                destination,
            ]
            cmd2 = [
                "rclone",
                "lsf",
                "--fast-list",
                "-R",
                "--dirs-only",
                "--config",
                config_path,
                destination,
            ]
            cmd3 = [
                "rclone",
                "size",
                "--fast-list",
                "--json",
                "--config",
                config_path,
                destination,
            ]
            (
                res1,
                res2,
                res3
            ) = await gather(
                cmd_exec(cmd1),
                cmd_exec(cmd2),
                cmd_exec(cmd3),
            )
            if res1[2] != res2[2] != res3[2] != 0:
                if res1[2] == -9:
                    return
                files = None
                folders = None
                self.size = 0
                LOGGER.error(
                    f"Error: While getting rclone stat. Path: {destination}. Stderr: {res1[1][:4000]}"
                )
            else:
                files = len(res1[0].split("\n"))
                folders = (
                    len(res2[0].strip().split("\n"))
                    if res2[0]
                    else 0
                )
                rsize = loads(res3[0])
                self.size = rsize["bytes"]
                await self.onUploadComplete(
                    flink,
                    files,
                    folders,
                    mime_type,
                    destination
                )
        else:
            smsg = await send_message(
                self.message,
                COMMAND_USAGE["clone"][0],
                COMMAND_USAGE["clone"][1]
            )
            await auto_delete_message(
                self.message,
                smsg
            )


async def clone(client, message):
    bot_loop.create_task(
        Clone(
            client,
            message
        ).new_event())


bot.add_handler( # type: ignore
    MessageHandler(
        clone,
        filters=command(
            BotCommands.CloneCommand,
            case_sensitive=True
        ) & CustomFilters.authorized
    )
)
