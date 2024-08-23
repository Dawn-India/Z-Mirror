from bot import (
    DOWNLOAD_DIR,
    bot,
    config_dict,
    LOGGER,
    bot_loop
)
from bot.helper.ext_utils.bot_utils import (
    sync_to_async,
    arg_parser,
    COMMAND_USAGE,
)
from bot.helper.ext_utils.links_utils import is_url
from bot.helper.listeners.ytdlp_listener import (
    YtSelection,
    mdisk,
    extract_info
)
from bot.helper.listeners.task_listener import TaskListener
from bot.helper.task_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    deleteMessage,
    sendMessage,
)

from nekozee.filters import command
from nekozee.handlers import MessageHandler


class YtDlp(TaskListener):
    def __init__(
        self,
        client,
        message,
        _=None,
        isLeech=False,
        __=None,
        ___=None,
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
        self.isYtDlp = True
        self.isLeech = isLeech

    async def newEvent(self):
        self.pmsg = await sendMessage(
            self.message,
            "Processing your request..."
        )
        text = self.message.text.split("\n")
        input_list = text[0].split(" ")
        qual = ""

        args = {
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
        self.upDest = args["-up"]
        self.rcFlags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"]
        self.thumb = args["-t"]
        self.splitSize = args["-sp"]
        self.sampleVideo = args["-sv"]
        self.screenShots = args["-ss"]
        self.forceRun = args["-f"]
        self.forceDownload = args["-fd"]
        self.forceUpload = args["-fu"]
        self.convertAudio = args["-ca"]
        self.convertVideo = args["-cv"]
        self.nameSub = args["-ns"]
        self.mixedLeech = args["-ml"]

        isBulk = args["-b"]
        folder_name = args["-sd"]

        bulk_start = 0
        bulk_end = 0
        reply_to = None
        opt = args["-opt"]
        self.file_ = None

        await self.getId()

        if not isinstance(isBulk, bool):
            dargs = isBulk.split(":")
            bulk_start = dargs[0] or None
            if len(dargs) == 2:
                bulk_end = dargs[1] or None
            isBulk = True

        if not isBulk:
            if folder_name:
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
                YtDlp
            )
            return

        if len(self.bulk) != 0:
            del self.bulk[0]

        path = f"{DOWNLOAD_DIR}{self.mid}{folder_name}"

        await self.getTag(text)

        opt = (
            opt
            or self.userDict.get("yt_opt")
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
            hmsg = await sendMessage(
                self.message,
                COMMAND_USAGE["yt"][0],
                COMMAND_USAGE["yt"][1]
            )
            self.removeFromSameDir()
            await deleteMessage(self.pmsg)
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
                if key == "postprocessors":
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
            emsg = await sendMessage(
                self.message,
                f"{self.tag} {msg}"
            )
            self.removeFromSameDir()
            await auto_delete_message(
                self.message,
                emsg
            )
            return
        finally:
            self.run_multi(
                input_list,
                folder_name,
                YtDlp
            ) # type: ignore

        if not qual:
            qual = await YtSelection(self).get_quality(result)
            if qual is None:
                self.removeFromSameDir()
                return

        await deleteMessage(self.pmsg)

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
    ).newEvent()) # type: ignore


async def ytdlleech(client, message):
    bot_loop.create_task(YtDlp(
        client,
        message,
        isLeech=True
    ).newEvent()) # type: ignore


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
        ytdlleech,
        filters=command(
            BotCommands.YtdlLeechCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
