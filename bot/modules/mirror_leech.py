from aiofiles.os import path as aiopath
from base64 import b64encode
from re import match as re_match

from nekozee.filters import command
from nekozee.handlers import MessageHandler

from bot import (
    DOWNLOAD_DIR,
    LOGGER,
    bot,
    bot_loop,
    task_dict_lock
)
from ..helper.ext_utils.bot_utils import (
    COMMAND_USAGE,
    get_content_type,
    sync_to_async,
    arg_parser
)
from ..helper.ext_utils.exceptions import DirectDownloadLinkException
from ..helper.ext_utils.links_utils import (
    is_url,
    is_magnet,
    is_gdrive_id,
    is_mega_link,
    is_gdrive_link,
    is_rclone_path,
    is_telegram_link,
)
from ..helper.listeners.task_listener import TaskListener
from ..helper.task_utils.download_utils.aria2_download import add_aria2c_download
from ..helper.task_utils.download_utils.direct_downloader import add_direct_download
from ..helper.task_utils.download_utils.direct_link_generator import direct_link_generator
from ..helper.task_utils.download_utils.gd_download import add_gd_download
from ..helper.task_utils.download_utils.jd_download import add_jd_download
from ..helper.task_utils.download_utils.mega_download import add_mega_download
from ..helper.task_utils.download_utils.qbit_download import add_qb_torrent
from ..helper.task_utils.download_utils.nzb_downloader import add_nzb
from ..helper.task_utils.download_utils.rclone_download import add_rclone_download
from ..helper.task_utils.download_utils.telegram_download import TelegramDownloadHelper
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_message,
    get_tg_link_message,
    send_message,
    edit_message,
)


class Mirror(TaskListener):
    def __init__(
        self,
        client,
        message,
        is_qbit=False,
        is_leech=False,
        is_jd=False,
        is_nzb=False,
        same_dir=None,
        bulk=None,
        multi_tag=None,
        options="",
    ):
        if same_dir is None:
            same_dir = {}
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multi_tag = multi_tag
        self.options = options
        self.same_dir = same_dir
        self.bulk = bulk
        super().__init__()
        self.is_qbit = is_qbit
        self.is_leech = is_leech
        self.is_jd = is_jd
        self.is_nzb = is_nzb
        self.file_ = None

    async def new_event(self):
        self.pmsg = await send_message(
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
            await edit_message(
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
            "-doc": False, "-document": False,
            "-med": False, "-media": False,
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
            "-tl": "", "-thumblayout": "",
            "-ca": "", "-convertaudio": "",
            "-cv": "", "-convertvideo": "",
            "-ns": "", "-namesub": "",
            "-md": "", "-metadata": "",
            "-mda": "", "-metaattachment": ""
        }

        arg_parser(
            input_list[1:],
            args
        )

        self.select = args["-s"] or args["-select"]
        self.seed = args["-d"] or args["-seed"]
        self.name = args["-n"] or args["-rename"]
        self.up_dest = args["-up"] or args["-upload"]
        self.rc_flags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"] or args["-zip"] or args["-compress"]
        self.extract = args["-e"] or args["-extract"] or args["-uz"] or args["-unzip"]
        self.join = args["-j"] or args["-join"]
        self.thumb = args["-t"] or args["-thumb"]
        self.split_size = args["-sp"] or args["-splitsize"]
        self.sample_video = args["-sv"] or args["-samplevideo"]
        self.screen_shots = args["-ss"] or args["-screenshot"]
        self.force_run = args["-f"] or args["-forcerun"]
        self.force_download = args["-fd"] or args["-forcedownload"]
        self.force_upload = args["-fu"] or args["-forceupload"]
        self.convert_audio = args["-ca"] or args["-convertaudio"]
        self.convert_video = args["-cv"] or args["-convertvideo"]
        self.name_sub = args["-ns"] or args["-namesub"]
        self.mixed_leech = args["-ml"] or args["-mixedleech"]
        self.metadata = args["-md"] or args["-metadata"]
        self.m_attachment = args["-mda"] or args["-metaattachment"]
        self.thumbnail_layout = args["-tl"] or args["-thumblayout"]
        self.as_doc = args["-doc"] or args["-document"]
        self.as_med = args["-med"] or args["-media"]
        self.folder_name = ((
            f"/{args["-sd"]}" or
            f"/{args["-samedir"]}"
        ) if (
            len(args["-sd"]) or
            len(args["-samedir"])
        ) > 0 else "")

        headers = args["-h"] or args["-headers"]
        is_bulk = args["-b"] or args["-bulk"]

        bulk_start = 0
        bulk_end = 0
        ratio = None
        seed_time = None
        reply_to = None
        session = ""

        await self.get_id()
        await self.get_tag(text)

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

        if not isinstance(is_bulk, bool):
            dargs = is_bulk.split(":")
            bulk_start = (
                dargs[0]
                or 0
            )
            if len(dargs) == 2:
                bulk_end = (
                    dargs[1]
                    or 0
                )
            is_bulk = True

        if not is_bulk:
            if self.multi > 0:
                if self.folder_name:
                    self.seed = False
                    ratio = None
                    seed_time = None
                    async with task_dict_lock:
                        if self.folder_name in self.same_dir:
                            self.same_dir[self.folder_name]["tasks"].add(self.mid)
                            for fd_name in self.same_dir:
                                if fd_name != self.folder_name:
                                    self.same_dir[fd_name]["total"] -= 1
                        elif self.same_dir:
                            self.same_dir[self.folder_name] = {"total": self.multi, "tasks": {self.mid}}
                            for fd_name in self.same_dir:
                                if fd_name != self.folder_name:
                                    self.same_dir[fd_name]["total"] -= 1
                        else:
                            self.same_dir = {self.folder_name: {"total": self.multi, "tasks": {self.mid}}}
                elif self.same_dir:
                    async with task_dict_lock:
                        for fd_name in self.same_dir:
                            self.same_dir[fd_name]["total"] -= 1
        else:
            await delete_message(self.pmsg)
            await self.init_bulk(
                input_list,
                bulk_start,
                bulk_end,
                Mirror
            )
            return

        if len(self.bulk) != 0:
            del self.bulk[0]

        await self.run_multi(
                input_list,
                Mirror
            )

        await self.get_tag(text)

        path = f"{DOWNLOAD_DIR}{self.mid}{self.folder_name}"

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
                    tmsg = await send_message(
                        self.message,
                        f"ERROR: This is a TG invite link.\nSend media links to download.\n\ncc: {self.tag}"
                    )
                    return tmsg
                tmsg = await send_message(
                    self.message,
                    f"ERROR: {e}\n\ncc: {self.tag}"
                )
                await auto_delete_message(
                    self.message,
                    tmsg
                )
                await self.remove_from_same_dir()
                await delete_message(self.pmsg)
                return

        if isinstance(reply_to, list):
            self.bulk = reply_to
            b_msg = input_list[:1]
            self.options = " ".join(input_list[1:])
            b_msg.append(f"{self.bulk[0]} -m {len(self.bulk)} {self.options}")
            nextmsg = await send_message(
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
                self.is_qbit,
                self.is_leech,
                self.is_jd,
                self.is_nzb,
                self.same_dir,
                self.bulk,
                self.multi_tag,
                self.options,
            ).new_event()
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
            cmsg = await send_message(
                self.message,
                COMMAND_USAGE["mirror"][0],
                COMMAND_USAGE["mirror"][1]
            )
            await self.remove_from_same_dir()
            await delete_message(self.pmsg)
            await auto_delete_message(
                self.message,
                cmsg
            )
            return

        if len(self.link) > 0:
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
            await self.remove_from_same_dir()
            await delete_message(self.pmsg)
            await auto_delete_message(
                self.message,
                emsg
            )
            return

        if (
            not self.is_jd
            and not self.is_nzb
            and not self.is_qbit
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
                        dmsg = await send_message(
                            self.message,
                            e
                        )
                        await self.remove_from_same_dir()
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
        elif self.is_jd:
            await add_jd_download(
                self,
                path
            )
        elif self.is_qbit:
            await add_qb_torrent(
                self,
                path,
                ratio,
                seed_time
            )
        elif self.is_nzb:
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
    ).new_event()) # type: ignore


async def qb_mirror(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        is_qbit=True
    ).new_event()) # type: ignore


async def jd_mirror(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        is_jd=True
    ).new_event()) # type: ignore


async def nzb_mirror(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        is_nzb=True
    ).new_event()) # type: ignore


async def leech(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        is_leech=True
    ).new_event()) # type: ignore


async def qb_leech(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        is_qbit=True,
        is_leech=True
    ).new_event()) # type: ignore


async def jd_leech(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        is_leech=True,
        is_jd=True
    ).new_event()) # type: ignore


async def nzb_leech(client, message):
    bot_loop.create_task(Mirror(
        client,
        message,
        is_leech=True,
        is_nzb=True
    ).new_event()) # type: ignore


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
