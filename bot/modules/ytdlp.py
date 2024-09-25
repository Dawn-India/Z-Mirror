from bot import (
    DOWNLOAD_DIR,
    LOGGER,
    bot,
    bot_loop,
    config_dict
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
            "-doc": False,
            "-med": False,
            "-s": False,
            "-b": False,
            "-z": False,
            "-sv": False,
            "-ss": False,
            "-f": False,
            "-fd": False,
            "-fu": False,
            "-ml": False,
            "-m": 0,
            "-sp": 0,
            "link": "",
            "-sd": "",
            "-opt": "",
            "-n": "",
            "-up": "",
            "-rcf": "",
            "-t": "",
            "-ca": "",
            "-cv": "",
            "-ns": "",
            "-tl": "",
        }

        arg_parser(
            input_list[1:],
            args
        )

        try:
            self.multi = int(args["-m"])
        except:
            self.multi = 0

        self.select = args["-s"]
        self.name = args["-n"]
        self.up_dest = args["-up"]
        self.rc_flags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"]
        self.thumb = args["-t"]
        self.split_size = args["-sp"]
        self.sample_video = args["-sv"]
        self.screen_shots = args["-ss"]
        self.force_run = args["-f"]
        self.force_download = args["-fd"]
        self.force_upload = args["-fu"]
        self.convert_audio = args["-ca"]
        self.convert_video = args["-cv"]
        self.name_sub = args["-ns"]
        self.mixed_leech = args["-ml"]
        self.thumbnail_layout = args["-tl"]
        self.as_doc = args["-doc"]
        self.as_med = args["-med"]

        is_bulk = args["-b"]
        folder_name = args["-sd"]

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
            if folder_name:
                folder_name = f"/{folder_name}"
                if not self.same_dir:
                    self.same_dir = {
                        "total": self.multi,
                        "tasks": set(),
                        "name": folder_name,
                    }
                self.same_dir["tasks"].add(self.mid)
            elif self.same_dir:
                self.same_dir["total"] -= 1
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

        path = f"{DOWNLOAD_DIR}{self.mid}{folder_name}"

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
            self.remove_from_same_dir()
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
            self.remove_from_same_dir()
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
            self.remove_from_same_dir()
            await auto_delete_message(
                self.message,
                emsg
            )
            return
        finally:
            await self.run_multi(
                input_list,
                folder_name,
                YtDlp
            )

        if not qual:
            qual = await YtSelection(self).get_quality(result)
            if qual is None:
                self.remove_from_same_dir()
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
