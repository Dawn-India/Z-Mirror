from asyncio import gather
from json import loads
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from secrets import token_urlsafe

from bot import LOGGER, task_dict, task_dict_lock, bot
from bot.helper.ext_utils.bot_utils import (
    new_task,
    sync_to_async,
    new_task,
    cmd_exec,
    arg_parser,
    COMMAND_USAGE,
)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.links_utils import (
    is_gdrive_link,
    is_share_link,
    is_rclone_path,
    is_gdrive_id,
)
from bot.helper.ext_utils.task_manager import (
    limit_checker,
    stop_duplicate_check
)
from bot.helper.listeners.task_listener import TaskListener
from bot.helper.task_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from bot.helper.task_utils.gdrive_utils.clone import gdClone
from bot.helper.task_utils.gdrive_utils.count import gdCount
from bot.helper.task_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.task_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.task_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    sendMessage,
    deleteMessage,
    sendStatusMessage,
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
        multiTag=None,
        options="",
    ):
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multiTag = multiTag
        self.options = options
        self.sameDir = {}
        self.bulk = bulk
        super().__init__()
        self.isClone = True

    @new_task
    async def newEvent(self):
        self.pmsg = await sendMessage(
            self.message,
            "Processing your request..."
        )
        text = self.message.text.split("\n")
        input_list = text[0].split(" ")

        args = {
            "link": "",
            "-m": 0,
            "-b": False,
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

        self.upDest = args["-up"]
        self.rcFlags = args["-rcf"]
        self.link = args["link"]

        isBulk = args["-b"]
        sync = args["-sync"]
        bulk_start = 0
        bulk_end = 0
        self.file_ = None

        await self.getId()

        if not isinstance(isBulk, bool):
            dargs = isBulk.split(":")
            bulk_start = dargs[0] or 0
            if len(dargs) == 2:
                bulk_end = dargs[1] or 0
            isBulk = True

        if isBulk:
            await deleteMessage(self.pmsg)
            await self.initBulk(
                input_list,
                bulk_start,
                bulk_end,
                Clone
            )
            return

        await self.getTag(text)

        if (
            not self.link
            and (reply_to := self.message.reply_to_message)
        ):
            self.link = reply_to.text.split("\n", 1)[0].strip()

        self.run_multi(
            input_list,
            "",
            Clone
        ) # type: ignore

        if len(self.link) == 0:
            hmsg = await sendMessage(
                self.message,
                COMMAND_USAGE["clone"][0],
                COMMAND_USAGE["clone"][1]
            )
            await deleteMessage(self.pmsg)
            await auto_delete_message(
                self.message,
                hmsg
            )
            return
        LOGGER.info(self.link)
        
        if await self.permissionCheck() != True:
            return
        await deleteMessage(self.pmsg)

        try:
            await self.beforeStart()
        except Exception as e:
            emsg = await sendMessage(
                self.message,
                e
            )
            await auto_delete_message(
                self.message,
                emsg
            )
            return
        await self._proceedToClone(sync)

    async def _proceedToClone(self, sync):
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
                    smsg = await sendMessage(
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
                gdCount().count,
                self.link,
                self.userId
            )
            if mime_type is None:
                smsg = await sendMessage(
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
                smsg = await sendMessage(
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
                smsg = await sendMessage(
                    self.message,
                    limit_exceeded
                )
                await auto_delete_message(
                    self.message,
                    smsg
                )
                return
            await self.onDownloadStart()
            LOGGER.info(f"Clone Started: Name: {self.name} - Source: {self.link}")
            drive = gdClone(self)
            if files <= 10:
                msg = await sendMessage(
                    self.message,
                    f"Cloning: <code>{self.link}</code>"
                )
                await delete_links(self.message)
            else:
                msg = ""
                gid = token_urlsafe(12)
                async with task_dict_lock:
                    task_dict[self.mid] = GdriveStatus(
                        self,
                        drive,
                        gid,
                        "cl"
                    )
                if self.multi <= 1:
                    await sendStatusMessage(self.message)
            (
                flink,
                mime_type,
                files,
                folders,
                dir_id
            ) = await sync_to_async(drive.clone)
            if msg:
                await deleteMessage(msg)
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
                self.upDest = self.upDest.replace(
                    "mrcc:",
                    "",
                    1
                )
                config_path = f"rclone/{self.userId}.conf"
            else:
                config_path = "rclone.conf"

            (
                remote,
                src_path
            ) = self.link.split(":", 1)
            src_path = src_path.strip("/")

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
                    smsg = await sendMessage(
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
                self.name = (
                    src_path.rsplit("/", 1)[-1]
                    if src_path
                    else remote
                )
                self.upDest += (
                    self.name
                    if self.upDest.endswith(":")
                    else f"/{self.name}"
                )

                mime_type = "Folder"
            else:
                self.name = src_path.rsplit(
                    "/",
                    1
                )[-1]
                mime_type = rstat["MimeType"]

            await self.onDownloadStart()

            RCTransfer = RcloneTransferHelper(self)
            LOGGER.info(
                f"Clone Started: Name: {self.name} - Source: {self.link} - Destination: {self.upDest}"
            )
            gid = token_urlsafe(12)
            async with task_dict_lock:
                task_dict[self.mid] = RcloneStatus(
                    self,
                    RCTransfer,
                    gid,
                    "cl"
                )
            if self.multi <= 1:
                await sendStatusMessage(self.message)
            method = (
                "sync"
                if sync
                else "copy"
            )
            flink, destination = await RCTransfer.clone(
                config_path,
                remote,
                src_path,
                mime_type,
                method,
            ) # type: ignore
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
            smsg = await sendMessage(
                self.message,
                COMMAND_USAGE["clone"][0],
                COMMAND_USAGE["clone"][1]
            )
            await auto_delete_message(
                self.message,
                smsg
            )


async def clone(client, message):
    Clone(
        client,
        message
    ).newEvent() # type: ignore


bot.add_handler( # type: ignore
    MessageHandler(
        clone,
        filters=command(
            BotCommands.CloneCommand
        ) & CustomFilters.authorized
    )
)
