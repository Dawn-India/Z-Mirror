from time import time
from functools import partial
from asyncio import (
    Event,
    wait_for,
)

from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,
    get_readable_time
)
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    deleteMessage,
    editMessage,
    sendMessage
)

from nekozee.handlers import CallbackQueryHandler
from nekozee.filters import (
    regex,
    user
)

from httpx import AsyncClient
from yt_dlp import YoutubeDL


async def select_format(_, query, obj):
    data = query.data.split()
    message = query.message
    await query.answer()

    if data[1] == "dict":
        b_name = data[2]
        await obj.qual_subbuttons(b_name)
    elif data[1] == "mp3":
        await obj.mp3_subbuttons()
    elif data[1] == "audio":
        await obj.audio_format()
    elif data[1] == "aq":
        if data[2] == "back":
            await obj.audio_format()
        else:
            await obj.audio_quality(data[2])
    elif data[1] == "back":
        await obj.back_to_main()
    elif data[1] == "cancel":
        cmsg = await editMessage(
            message,
            "Yt-Dlp task has been cancelled."
        )
        obj.qual = None
        obj.listener.isCancelled = True
        obj.event.set()
    else:
        if data[1] == "sub":
            obj.qual = obj.formats[data[2]][data[3]][1]
        elif "|" in data[1]:
            obj.qual = obj.formats[data[1]]
        else:
            obj.qual = data[1]
        obj.event.set()
    if obj.listener.isCancelled:
        await auto_delete_message(
            message,
            cmsg
        )

class YtSelection:
    def __init__(
            self,
            listener
        ):
        self.listener = listener
        self._is_m4a = False
        self._reply_to = None
        self._time = time()
        self._timeout = 120
        self._is_playlist = False
        self._main_buttons = None
        self.event = Event()
        self.formats = {}
        self.qual = None
        self.tag = listener.tag

    async def _event_handler(self):
        pfunc = partial(
            select_format,
            obj=self
        )
        handler = self.listener.client.add_handler(
            CallbackQueryHandler(
                pfunc,
                filters=regex("^ytq")
                &
                user(self.listener.userId)
            ),
            group=-1,
        )
        try:
            await wait_for(
                self.event.wait(),
                timeout=self._timeout
            )
        except:
            await editMessage(
                self._reply_to,
                "Timed Out. Task has been cancelled!"
            )
            self.qual = None
            self.listener.isCancelled = True
            await auto_delete_message(
                self.listener.message,
                self._reply_to
            )
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)
            if self.listener.isCancelled:
                await delete_links(self.listener.message)

    async def get_quality(self, result):
        buttons = ButtonMaker()
        if "entries" in result:
            self._is_playlist = True
            for i in [
                "144",
                "240",
                "360",
                "480",
                "720",
                "1080",
                "1440",
                "2160"
            ]:
                video_format = f"bv*[height<=?{i}][ext=mp4]+ba[ext=m4a]/b[height<=?{i}]"
                b_data = f"{i}|mp4"
                self.formats[b_data] = video_format
                buttons.ibutton(
                    f"{i}-ᴍᴘ4",
                    f"ytq {b_data}"
                )
                video_format = f"bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]"
                b_data = f"{i}|webm"
                self.formats[b_data] = video_format
                buttons.ibutton(
                    f"{i}-ᴡᴇʙᴍ",
                    f"ytq {b_data}"
                )
            buttons.ibutton(
                "ᴍᴘ3",
                "ytq mp3"
            )
            buttons.ibutton(
                "ᴀᴜᴅɪᴏ\nꜰᴏʀᴍᴀᴛꜱ",
                "ytq audio"
            )
            buttons.ibutton(
                "ʙᴇꜱᴛ\nᴠɪᴅᴇᴏꜱ",
                "ytq bv*+ba/b"
            )
            buttons.ibutton(
                "ʙᴇꜱᴛ\nᴀᴜᴅɪᴏꜱ",
                "ytq ba/b"
            )
            buttons.ibutton(
                "ᴄᴀɴᴄᴇʟ",
                "ytq cancel",
                "footer"
            )
            self._main_buttons = buttons.build_menu(3)
            msg = f"Choose Playlist Videos Quality:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}\n\ncc: {self.tag}"
        else:
            format_dict = result.get("formats")
            if format_dict is not None:
                for item in format_dict:
                    if item.get("tbr"):
                        format_id = item["format_id"]

                        if item.get("filesize"):
                            size = item["filesize"]
                        elif item.get("filesize_approx"):
                            size = item["filesize_approx"]
                        else:
                            size = 0

                        if (
                            item.get("video_ext") == "none"
                            and (
                                item.get("resolution") == "audio only"
                                or item.get("acodec") != "none"
                            )
                        ):
                            if item.get("audio_ext") == "m4a":
                                self._is_m4a = True
                            b_name = (
                                f"{item.get('acodec') or format_id}-{item['ext']}"
                            )
                            v_format = format_id
                        elif item.get("height"):
                            height = item["height"]
                            ext = item["ext"]
                            fps = (
                                item["fps"]
                                if item.get("fps")
                                else ""
                            )
                            b_name = f"{height}p{fps}-{ext}"
                            ba_ext = (
                                "[ext=m4a]"
                                if self._is_m4a
                                and ext == "mp4"
                                else ""
                            )
                            v_format = f"{format_id}+ba{ba_ext}/b[height=?{height}]"
                        else:
                            continue

                        self.formats.setdefault(b_name, {})[
                            f"{item['tbr']}"
                        ] = [
                            size,
                            v_format,
                        ]

                for (
                    b_name,
                    tbr_dict
                ) in self.formats.items():
                    if len(tbr_dict) == 1:
                        (
                            tbr,
                            v_list
                        ) = next(iter(tbr_dict.items()))
                        buttonName = f"{b_name} ({get_readable_file_size(v_list[0])})"
                        buttons.ibutton(
                            buttonName,
                            f"ytq sub {b_name} {tbr}"
                        )
                    else:
                        buttons.ibutton(
                            b_name,
                            f"ytq dict {b_name}"
                        )
            buttons.ibutton(
                "ᴍᴘ3",
                "ytq mp3"
            )
            buttons.ibutton(
                "ᴀᴜᴅɪᴏ\nꜰᴏʀᴍᴀᴛꜱ",
                "ytq audio"
            )
            buttons.ibutton(
                "ʙᴇꜱᴛ\nᴠɪᴅᴇᴏ",
                "ytq bv*+ba/b"
            )
            buttons.ibutton(
                "ʙᴇꜱᴛ\nᴀᴜᴅɪᴏ",
                "ytq ba/b"
            )
            buttons.ibutton(
                "ᴄᴀɴᴄᴇʟ",
                "ytq cancel",
                "footer"
            )
            self._main_buttons = buttons.build_menu(2)
            msg = f"Choose Video Quality:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}\n\ncc: {self.tag}"
        self._reply_to = await sendMessage(
            self.listener.message,
            msg,
            self._main_buttons
        )
        await self._event_handler()
        if not self.listener.isCancelled:
            await deleteMessage(self._reply_to)
        return self.qual

    async def back_to_main(self):
        if self._is_playlist:
            msg = f"Choose Playlist Videos Quality:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}\n\ncc: {self.tag}"
        else:
            msg = f"Choose Video Quality:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}\n\ncc: {self.tag}"
        await editMessage(
            self._reply_to,
            msg,
            self._main_buttons
        )

    async def qual_subbuttons(self, b_name):
        buttons = ButtonMaker()
        tbr_dict = self.formats[b_name]
        for (
            tbr,
            d_data
        ) in tbr_dict.items():
            button_name = f"{tbr}K ({get_readable_file_size(d_data[0])})"
            buttons.ibutton(
                button_name,
                f"ytq sub {b_name} {tbr}"
            )
        buttons.ibutton(
            "ʙᴀᴄᴋ",
            "ytq back",
            "footer"
        )
        buttons.ibutton(
            "ᴄᴀɴᴄᴇʟ",
            "ytq cancel",
            "footer"
        )
        subbuttons = buttons.build_menu(2)
        msg = (
            f"Choose Bit rate for <b>{b_name}</b>:\n"
            f"Timeout: {get_readable_time(self._timeout - (time() - self._time))}\n\ncc: {self.tag}"
        )
        await editMessage(
            self._reply_to,
            msg,
            subbuttons
        )

    async def mp3_subbuttons(self):
        i = "s" if self._is_playlist else ""
        buttons = ButtonMaker()
        audio_qualities = [
            64,
            128,
            320
        ]
        for q in audio_qualities:
            audio_format = f"ba/b-mp3-{q}"
            buttons.ibutton(
                f"{q}ᴋ-ᴍᴘ3",
                f"ytq {audio_format}"
            )
        buttons.ibutton(
            "ʙᴀᴄᴋ",
            "ytq back"
        )
        buttons.ibutton(
            "ᴄᴀɴᴄᴇʟ",
            "ytq cancel"
        )
        subbuttons = buttons.build_menu(3)
        msg = f"Choose mp3 Audio{i} Bitrate:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}\n\ncc: {self.tag}"
        await editMessage(
            self._reply_to,
            msg,
            subbuttons
        )

    async def audio_format(self):
        i = "s" if self._is_playlist else ""
        buttons = ButtonMaker()
        for frmt in [
            "aac",
            "alac",
            "flac",
            "m4a",
            "opus",
            "vorbis",
            "wav"
        ]:
            audio_format = f"ba/b-{frmt}-"
            buttons.ibutton(
                frmt,
                f"ytq aq {audio_format}"
            )
        buttons.ibutton(
            "ʙᴀᴄᴋ",
            "ytq back",
            "footer"
        )
        buttons.ibutton(
            "ᴄᴀɴᴄᴇʟ",
            "ytq cancel",
            "footer"
        )
        subbuttons = buttons.build_menu(3)
        msg = f"Choose Audio{i} Format:\nTimeout: {get_readable_time(self._timeout - (time() - self._time))}\n\ncc: {self.tag}"
        await editMessage(
            self._reply_to,
            msg,
            subbuttons
        )

    async def audio_quality(self, format):
        i = (
            "s"
            if self._is_playlist
            else ""
        )
        buttons = ButtonMaker()
        for qual in range(11):
            audio_format = f"{format}{qual}"
            buttons.ibutton(
                qual,
                f"ytq {audio_format}"
            )
        buttons.ibutton(
            "ʙᴀᴄᴋ",
            "ytq aq back"
        )
        buttons.ibutton(
            "ᴄᴀɴᴄᴇʟ",
            "ytq aq cancel"
        )
        subbuttons = buttons.build_menu(5)
        msg = (
            f"Choose Audio{i} Qaulity:\n0 is best and 10 is worst\n"
            f"Timeout: {get_readable_time(self._timeout - (time() - self._time))}\n\ncc: {self.tag}"
        )
        await editMessage(
            self._reply_to,
            msg,
            subbuttons
        )


def extract_info(link, options):
    with YoutubeDL(options) as ydl:
        result = ydl.extract_info(
            link,
            download=False
        )
        if result is None:
            raise ValueError("Info result is None")
        return result


async def mdisk(link, name):
    key = link.split("/")[-1]
    async with AsyncClient(verify=False) as client:
        resp = await client.get(
            f"https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={key}"
        )
    if resp.status_code == 200:
        resp_json = resp.json()
        link = resp_json["source"]
        if not name:
            name = resp_json["filename"]
    return (
        name,
        link
    )
