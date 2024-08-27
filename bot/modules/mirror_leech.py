from aiofiles.os import (
    path as aiopath,
    remove
)
from base64 import b64encode
from nekozee.filters import command
from nekozee.handlers import MessageHandler
from re import match as re_match

from bot import (
    bot,
    DOWNLOAD_DIR,
    LOGGER,
    bot_loop
)
from bot.helper.ext_utils.bot_utils import (
    get_content_type,
    sync_to_async,
    arg_parser,
    COMMAND_USAGE,
)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.links_utils import (
    is_url,
    is_magnet,
    is_gdrive_id,
    is_mega_link,
    is_gdrive_link,
    is_rclone_path,
    is_telegram_link,
)
from bot.helper.listeners.task_listener import TaskListener
from bot.helper.task_utils.download_utils.aria2_download import (
    add_aria2c_download,
)
from bot.helper.task_utils.download_utils.direct_downloader import (
    add_direct_download,
)
from bot.helper.task_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from bot.helper.task_utils.download_utils.gd_download import add_gd_download
from bot.helper.task_utils.download_utils.jd_download import add_jd_download
from bot.helper.task_utils.download_utils.mega_download import add_mega_download
from bot.helper.task_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.task_utils.download_utils.nzb_downloader import add_nzb
from bot.helper.task_utils.download_utils.rclone_download import (
    add_rclone_download,
)
from bot.helper.task_utils.download_utils.telegram_download import (
    TelegramDownloadHelper,
)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    deleteMessage,
    get_tg_link_message,
    sendMessage,
    editMessage,
)
from myjd.exception import MYJDException


class Mirror(TaskListener):
    def __init__(
        self,
        client,
        message,
        isQbit=False,
        isLeech=False,
        isJd=False,
        isNzb=False,
        sameDir=None,
        bulk=None,
        multiTag=None,
        options="",
    ):
        if sameDir is None:
            sameDir = {}
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multiTag = multiTag
        self.options = options
        self.sameDir = sameDir
        self.bulk = bulk
        super().__init__()
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.isJd = isJd
        self.isNzb = isNzb
        self.file_ = None

    async def newEvent(self):
        self.pmsg = await sendMessage(
            self.message,
            "Processing your request..."
        )
        try:
            text = (
                self.message.caption.split("\n")
                if self.message.document
                else self.message.text.split("\n")
            )
        except Exception as e:
            LOGGER.error(e)
            await editMessage(
                self.pmsg,
                f"ERROR: {e}"
            )
            return
        input_list = text[0].split(" ")

        args = {
            "-d": False, "-seed": False,
            "-j": False, "-join": False,
            "-s": False, "-select": False,
            "-b": False, "-bulk": False,
            "-e": False, "-extract": False, "-uz": False, "-unzip": False,
            "-z": False, "-zip": False, "-compress": False,
            "-sv": False, "-samplevideo": False,
            "-ss": False, "-screenshot": False,
            "-f": False, "-forcerun": False,
            "-fd": False, "-forcedownload": False,
            "-fu": False, "-forceupload": False,
            "-ml": False, "-mixedleech": False,
            "-m": 0,
            "-sp": 0, "-splitsize": 0,
            "link": "",
            "-n": "", "-rename": "",
            "-sd": "", "-samedir": "",
            "-up": "", "-upload": "",
            "-rcf": "",
            "-au": "", "-authuser": "",
            "-ap": "", "-authpass": "",
            "-h": "", "-headers": "",
            "-t": "", "-thumb": "",
            "-ca": "", "-convertaudio": "",
            "-cv": "", "-convertvideo": "",
            "-ns": "", "-namesub": "",
            "-md": "", "-metadata": "",
            "-mda": "", "-metaattachment": "",
        }

        arg_parser(
            input_list[1:],
            args
        )

        self.select = args["-s"] or args["-select"]
        self.seed = args["-d"] or args["-seed"]
        self.name = args["-n"] or args["-rename"]
        self.upDest = args["-up"] or args["-upload"]
        self.rcFlags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"] or args["-zip"] or args["-compress"]
        self.extract = args["-e"] or args["-extract"] or args["-uz"] or args["-unzip"]
        self.join = args["-j"] or args["-join"]
        self.thumb = args["-t"] or args["-thumb"]
        self.splitSize = args["-sp"] or args["-splitsize"]
        self.sampleVideo = args["-sv"] or args["-samplevideo"]
        self.screenShots = args["-ss"] or args["-screenshot"]
        self.forceRun = args["-f"] or args["-forcerun"]
        self.forceDownload = args["-fd"] or args["-forcedownload"]
        self.forceUpload = args["-fu"] or args["-forceupload"]
        self.convertAudio = args["-ca"] or args["-convertaudio"]
        self.convertVideo = args["-cv"] or args["-convertvideo"]
        self.nameSub = args["-ns"] or args["-namesub"]
        self.mixedLeech = args["-ml"] or args["-mixedleech"]
        self.metaData = args["-md"] or args["-metadata"]
        self.metaAttachment = args["-mda"] or args["-metaattachment"]

        headers = args["-h"] or args["-headers"]
        isBulk = args["-b"] or args["-bulk"]
        folder_name = args["-sd"] or args["-samedir"]

        bulk_start = 0
        bulk_end = 0
        ratio = None
        seed_time = None
        reply_to = None
        session = ""

        await self.getId()

        await self.getTag(text)

        try:
            self.multi = int(args["-m"])
        except:
            self.multi = 0

        if not isinstance(self.seed, bool):
            dargs = self.seed.split(":")
            ratio = (
                dargs[0]
                or None
            )
            if len(dargs) == 2:
                seed_time = (
                    dargs[1]
                    or None
                )
            self.seed = True

        if not isinstance(isBulk, bool):
            dargs = isBulk.split(":")
            bulk_start = (
                dargs[0]
                or 0
            )
            if len(dargs) == 2:
                bulk_end = (
                    dargs[1]
                    or 0
                )
            isBulk = True

        if not isBulk:
            if folder_name:
                self.seed = False
                ratio = None
                seed_time = None
                folder_name = f"/{folder_name}"
                if not self.sameDir:
                    self.sameDir = {
                        "total": self.multi,
                        "tasks": set(),
                        "name": folder_name,
                    }
                self.sameDir["tasks"].add(self.mid)
            elif self.sameDir:
                self.sameDir["total"] -= 1

        else:
            await deleteMessage(self.pmsg)
            await self.initBulk(
                input_list,
                bulk_start,
                bulk_end,
                Mirror
            )
            return

        if len(self.bulk) != 0:
            del self.bulk[0]

        self.run_multi(
            input_list,
            folder_name,
            Mirror
        ) # type: ignore

        path = f"{DOWNLOAD_DIR}{self.mid}{folder_name}"

        if (
            not self.link
            and (reply_to := self.message.reply_to_message)
        ):
            if reply_to.text:
                self.link = reply_to.text.split(
                    "\n",
                    1
                )[0].strip()
        if is_telegram_link(self.link):
            try:
                result = await get_tg_link_message(self.link)
                if result is not None:
                    reply_to, session = result
            except Exception as e:
                e = str(e)
                if "group" in e:
                    tmsg = await sendMessage(
                        self.message,
                        f"ERROR: This is a TG invite link.\nSend media links to download.\n\ncc: {self.tag}"
                    )
                    return tmsg
                tmsg = await sendMessage(
                    self.message,
                    f"ERROR: {e}\n\ncc: {self.tag}"
                )
                await auto_delete_message(
                    self.message,
                    tmsg
                )
                self.removeFromSameDir()
                await deleteMessage(self.pmsg)
                return

        if isinstance(reply_to, list):
            self.bulk = reply_to
            self.sameDir = {}
            b_msg = input_list[:1]
            self.options = " ".join(input_list[1:])
            b_msg.append(
                f"{self.bulk[0]} -m {len(self.bulk)} {self.options}"
            )
            nextmsg = await sendMessage(
                self.message,
                " ".join(b_msg)
            )
            nextmsg = await self.client.get_messages(
                chat_id=self.message.chat.id,
                message_ids=nextmsg.id # type: ignore
            )
            if self.message.from_user:
                nextmsg.from_user = self.user
            else:
                nextmsg.sender_chat = self.user
            await Mirror(
                self.client,
                nextmsg,
                self.isQbit,
                self.isLeech,
                self.isJd,
                self.isNzb,
                self.sameDir,
                self.bulk,
                self.multiTag,
                self.options,
            ).newEvent()
            return

        if reply_to:
            self.file_ = (
                reply_to.document
                or reply_to.photo
                or reply_to.video
                or reply_to.audio
                or reply_to.voice
                or reply_to.video_note
                or reply_to.sticker
                or reply_to.animation
                or None
            )

            if self.file_ is None:
                if reply_text := reply_to.text:
                    self.link = reply_text.split(
                        "\n",
                        1
                    )[0].strip()
                else:
                    reply_to = None
            elif reply_to.document and (
                self.file_.mime_type == "application/x-bittorrent"
                or self.file_.file_name.endswith((
                    ".torrent",
                    ".dlc",
                    ".nzb"
                ))
            ):
                self.link = await reply_to.download()
                self.file_ = None

        if (
            not self.link
            and self.file_ is None
            or is_telegram_link(self.link)
            and reply_to is None
            or self.file_ is None
            and not is_url(self.link)
            and not is_magnet(self.link)
            and not await aiopath.exists(self.link)
            and not is_rclone_path(self.link)
            and not is_gdrive_id(self.link)
            and not is_gdrive_link(self.link)
            and not is_mega_link(self.link)
        ):
            cmsg = await sendMessage(
                self.message,
                COMMAND_USAGE["mirror"][0],
                COMMAND_USAGE["mirror"][1]
            )
            self.removeFromSameDir()
            await deleteMessage(self.pmsg)
            await auto_delete_message(
                self.message,
                cmsg
            )
            return

        if self.link:
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
            self.removeFromSameDir()
            await deleteMessage(self.pmsg)
            await auto_delete_message(
                self.message,
                emsg
            )
            return

        if (
            not self.isJd
            and not self.isNzb
            and not self.isQbit
            and not is_magnet(self.link)
            and not is_rclone_path(self.link)
            and not is_gdrive_link(self.link)
            and not is_mega_link(self.link)
            and not self.link.endswith(".torrent")
            and self.file_ is None
            and not is_gdrive_id(self.link)
        ):
            content_type = await get_content_type(self.link)
            if content_type is None or re_match(
                r"text/html|text/plain",
                content_type
            ):
                try:
                    self.link = await sync_to_async(
                        direct_link_generator,
                        self.link
                    )
                    if isinstance(
                        self.link,
                        tuple
                    ):
                        self.link, headers = self.link
                    elif isinstance(
                        self.link,
                        str
                    ):
                        LOGGER.info(f"Generated link: {self.link}")
                except DirectDownloadLinkException as e:
                    e = str(e)
                    if "This link requires a password!" not in e:
                        LOGGER.info(e)
                    if e.startswith("ERROR:"):
                        dmsg = await sendMessage(
                            self.message,
                            e
                        )
                        self.removeFromSameDir()
                        await auto_delete_message(
                            self.message,
                            dmsg
                        )
                        return

        if self.file_ is not None:
            await TelegramDownloadHelper(self).add_download(
                reply_to,
                f"{path}/",
                session
            )
        elif isinstance(
            self.link,
            dict
        ):
            await add_direct_download(
                self,
                path
            )
        elif self.isJd:
            try:
                await add_jd_download(
                    self,
                    path
                )
            except (
                Exception,
                MYJDException
            ) as e:
                jmsg = await sendMessage(
                    self.message,
                    f"{e}".strip()
                )
                self.removeFromSameDir()
                await auto_delete_message(
                    self.message,
                    jmsg
                )
                return
            finally:
                if await aiopath.exists(str(self.link)):
                    await remove(str(self.link))
        elif self.isQbit:
            await add_qb_torrent(
                self,
                path,
                ratio,
                seed_time
            )
        elif self.isNzb:
            await add_nzb(
                self,
                path
            )
        elif is_rclone_path(str(self.link)):
            await add_rclone_download(
                self,
                f"{path}/"
            )
        elif (
            is_gdrive_link(str(self.link)) or
            is_gdrive_id(str(self.link))
        ):
            await add_gd_download(
                self,
                path
            )
        elif is_mega_link(self.link):
            await add_mega_download(
                self,
                f"{path}/"
            )
        else:
            ussr = args["-au"]
            pssw = args["-ap"]
            if ussr or pssw:
                auth = f"{ussr}:{pssw}"
                headers += (
                    f" authorization: Basic {b64encode(auth.encode()).decode("ascii")}"
                )
            await add_aria2c_download(
                self,
                path,
                headers,
                ratio,
                seed_time
            )


async def mirror(client, message):
    bot_loop.create_task(Mirror(
        client,
        message
    ).newEvent()) # type: ignore


async def qb_mirror(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        isQbit=True
    ).newEvent()) # type: ignore


async def jd_mirror(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        isJd=True
    ).newEvent()) # type: ignore


async def nzb_mirror(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        isNzb=True
    ).newEvent()) # type: ignore


async def leech(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        isLeech=True
    ).newEvent()) # type: ignore


async def qb_leech(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        isQbit=True,
        isLeech=True
    ).newEvent()) # type: ignore


async def jd_leech(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        isLeech=True,
        isJd=True
    ).newEvent()) # type: ignore


async def nzb_leech(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        isLeech=True,
        isNzb=True
    ).newEvent()) # type: ignore


bot.add_handler( # type: ignore
    MessageHandler(
        mirror,
        filters=command(
            BotCommands.MirrorCommand,
            case_sensitive=True
        ) & CustomFilters.authorized
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        qb_mirror,
        filters=command(
            BotCommands.QbMirrorCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        jd_mirror,
        filters=command(
            BotCommands.JdMirrorCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        nzb_mirror,
        filters=command(
            BotCommands.NzbMirrorCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        leech,
        filters=command(
            BotCommands.LeechCommand,
            case_sensitive=True
        ) & CustomFilters.authorized
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        qb_leech,
        filters=command(
            BotCommands.QbLeechCommand,
            case_sensitive=True
        ) & CustomFilters.authorized
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        jd_leech,
        filters=command(
            BotCommands.JdLeechCommand,
            case_sensitive=True
        ) & CustomFilters.authorized
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        nzb_leech,
        filters=command(
            BotCommands.NzbLeechCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
