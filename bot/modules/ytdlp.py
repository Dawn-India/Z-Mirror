from bot import (
    DOWNLOAD_DIR,
    LOGGER,
    bot,
    bot_loop,
    config_dict,
    task_dict_lock
)
from bot.helper.ext_utils.bot_utils import (
    COMMAND_USAGE,
    arg_parser,
    sync_to_async
)
from bot.helper.ext_utils.links_utils import is_url
from bot.helper.listeners.ytdlp_listener import (
    extract_info,
    mdisk,
    YtSelection
)
from bot.helper.listeners.task_listener import TaskListener
from bot.helper.task_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_message,
    send_message,
)

from nekozee.filters import command
from nekozee.handlers import MessageHandler


class YtDlp(TaskListener):
    def __init__(
        self,
        client,
        message,
        _=None,
        is_leech=False,
        __=None,
        ___=None,
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
        self.is_ytdlp = True
        self.is_leech = is_leech

    async def new_event(self):
        self.pmsg = await send_message(
            self.message,
            "Processing your request..."
        )
        text = self.message.text.split("\n")
        input_list = text[0].split(" ")
        qual = ""

        args = {
            "-doc": False, "-document": False,
            "-med": False, "-media": False,
            "-s": False, "-select": False,
            "-b": False, "-bulk": False,
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
            "-sd": "", "-samedir": "",
            "-opt": "",
            "-n": "", "-rename": "",
            "-up": "", "-upload": "",
            "-rcf": "",
            "-t": "", "-thumb": "",
            "-tl": "", "-thumblayout": "",
            "-ca": "", "-convertaudio": "",
            "-cv": "", "-convertvideo": "",
            "-ns": "", "-namesub": ""
        }

        arg_parser(
            input_list[1:],
            args
        )

        try:
            self.multi = int(args["-m"])
        except:
            self.multi = 0

        self.select = args["-s"] or args["-select"]
        self.name = args["-n"] or args["-rename"]
        self.up_dest = args["-up"] or args["-upload"]
        self.rc_flags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"] or args["-zip"] or args["-compress"]
        self.thumb = args["-t"] or args["-thumb"]
        self.thumbnail_layout = args["-tl"] or args["-thumblayout"]
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
        self.as_doc = args["-doc"] or args["-document"]
        self.as_med = args["-med"] or args["-media"]
        self.folder_name = ((
            f"/{args["-sd"]}" or
            f"/{args["-samedir"]}"
        ) if (
            len(args["-sd"]) or
            len(args["-samedir"])
        ) > 0 else "")

        is_bulk = args["-b"]

        bulk_start = 0
        bulk_end = 0
        reply_to = None
        opt = args["-opt"]
        self.file_ = None

        await self.get_id()

        if not isinstance(is_bulk, bool):
            dargs = is_bulk.split(":")
            bulk_start = dargs[0] or None
            if len(dargs) == 2:
                bulk_end = dargs[1] or None
            is_bulk = True

        if not is_bulk:
            if self.multi > 0:
                if self.folder_name:
                    async with task_dict_lock:
                        if self.folder_name in self.same_dir:
                            self.same_dir[self.folder_name]["tasks"].add(self.mid)
                            for fd_name in self.same_dir:
                                if fd_name != self.folder_name:
                                    self.same_dir[fd_name]["total"] -= 1
                        elif self.same_dir:
                            self.same_dir[self.folder_name] = {
                                "total": self.multi,
                                "tasks": {self.mid},
                            }
                            for fd_name in self.same_dir:
                                if fd_name != self.folder_name:
                                    self.same_dir[fd_name]["total"] -= 1
                        else:
                            self.same_dir = {
                                self.folder_name: {
                                    "total": self.multi,
                                    "tasks": {self.mid},
                                }
                            }
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
                YtDlp
            )
            return

        if len(self.bulk) != 0:
            del self.bulk[0]

        path = f"{DOWNLOAD_DIR}{self.mid}{self.folder_name}"

        await self.get_tag(text)

        opt = (
            opt
            or self.user_dict.get("yt_opt")
            or config_dict["YT_DLP_OPTIONS"]
        )

        if (
            not self.link
            and (reply_to := self.message.reply_to_message)
        ):
            self.link = reply_to.text.split(
                "\n",
                1
            )[0].strip()

        if not is_url(self.link):
            hmsg = await send_message(
                self.message,
                COMMAND_USAGE["yt"][0],
                COMMAND_USAGE["yt"][1]
            )
            await self.remove_from_same_dir()
            await delete_message(self.pmsg)
            await auto_delete_message(
                self.message,
                hmsg
            )
            return

        if "mdisk.me" in self.link:
            (
                self.name,
                self.link
            ) = await mdisk(
                self.link,
                self.name
            )

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
            await auto_delete_message(
                self.message,
                emsg
            )
            return

        options = {
            "usenetrc": True,
            "cookiefile": "cookies.txt"
        }
        if opt:
            yt_opts = opt.split("|")
            for ytopt in yt_opts:
                (
                    key,
                    value
                ) = map(
                    str.strip,
                    ytopt.split(
                        ":",
                        1
                    )
                )
                if key in [
                    "postprocessors",
                    "download_ranges"
                ]:
                    continue
                if key == "format" and not self.select:
                    if value.startswith("ba/b-"):
                        qual = value
                        continue
                    else:
                        qual = value
                if value.startswith("^"):
                    if (
                        "." in value
                        or value == "^inf"
                    ):
                        value = float(value.split("^")[1])
                    else:
                        value = int(value.split("^")[1])
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif (
                    value.startswith(
                        (
                            "{",
                            "[",
                            "("
                        )
                    )
                    and
                    value.endswith(
                        (
                            "}",
                            "]",
                            ")"
                        )
                    )
                ):
                    value = eval(value)
                options[key] = value
        options["playlist_items"] = "0"

        try:
            result = await sync_to_async(
                extract_info,
                self.link,
                options
            )
        except Exception as e:
            msg = str(e).replace(
                "<",
                " "
            ).replace(
                ">",
                " "
            )
            emsg = await send_message(
                self.message,
                f"{self.tag} {msg}"
            )
            await self.remove_from_same_dir()
            await auto_delete_message(
                self.message,
                emsg
            )
            return
        finally:
            await self.run_multi(
                input_list,
                YtDlp
            )

        if not qual:
            qual = await YtSelection(self).get_quality(result)
            if qual is None:
                await self.remove_from_same_dir()
                return

        await delete_message(self.pmsg)

        LOGGER.info(f"Downloading with YT-DLP: {self.link}")
        playlist = "entries" in result
        ydl = YoutubeDLHelper(self)
        await ydl.add_download(
            path,
            qual,
            playlist,
            opt
        )


async def ytdl(client, message):
    bot_loop.create_task(YtDlp(
        client,
        message
    ).new_event()) # type: ignore


async def ytdl_leech(client, message):
    bot_loop.create_task(YtDlp(
        client,
        message,
        is_leech=True
    ).new_event()) # type: ignore


bot.add_handler( # type: ignore
    MessageHandler(
        ytdl,
        filters=command(
            BotCommands.YtdlCommand,
            case_sensitive=True
        ) & CustomFilters.authorized
    )
)

bot.add_handler( # type: ignore
    MessageHandler(
        ytdl_leech,
        filters=command(
            BotCommands.YtdlLeechCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
