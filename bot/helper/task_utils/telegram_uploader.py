from PIL import Image
from html import escape
from aiofiles.os import (
    remove,
    path as aiopath,
    rename,
    makedirs,
)
from aioshutil import (
    copy,
    rmtree
)
from asyncio import sleep
from logging import getLogger
from natsort import natsorted
from os import (
    walk,
    path as ospath
)
from pyrogram.errors import (
    FloodWait,
    RPCError
)
from pyrogram.types import (
    InputMediaVideo,
    InputMediaDocument,
    InputMediaPhoto
)
from re import (
    match as re_match,
    sub as re_sub
)
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    RetryError,
)
from time import time

from bot import bot, config_dict, user, IS_PREMIUM_USER
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.files_utils import (
    clean_unwanted,
    is_archive,
    get_base_name
)
from bot.helper.ext_utils.media_utils import (
    get_media_info,
    get_document_type,
    create_thumbnail,
    get_audio_thumb,
)
from bot.helper.telegram_helper.message_utils import deleteMessage

LOGGER = getLogger(__name__)


class TgUploader:
    def __init__(self, listener, path):
        self._last_uploaded = 0
        self._processed_bytes = 0
        self._listener = listener
        self._path = path
        self._start_time = time()
        self._total_files = 0
        self._thumb = self._listener.thumb or f"Thumbnails/{listener.userId}.jpg"
        self._msgs_dict = {}
        self._corrupted = 0
        self._is_corrupted = False
        self._media_dict = {"videos": {}, "documents": {}}
        self._last_msg_in_group = False
        self._up_path = ""
        self._lprefix = ""
        self._lsuffix = ""
        self._lcapfont = ""
        self._media_group = False
        self._is_private = False
        self._sent_msg = None
        self._sent_DMmsg = None
        self._user_session = self._listener.userTransmission

    async def _upload_progress(self, current, _):
        if self._listener.isCancelled:
            if self._user_session:
                user.stop_transmission() # type: ignore
            else:
                self._listener.client.stop_transmission()
        chunk_size = current - self._last_uploaded
        self._last_uploaded = current
        self._processed_bytes += chunk_size

    async def _user_settings(self):
        self._media_group = self._listener.userDict.get("media_group") or (
            config_dict["MEDIA_GROUP"]
            if "media_group" not in self._listener.userDict
            else False
        )
        self._lprefix = self._listener.userDict.get("lprefix") or (
            config_dict["LEECH_FILENAME_PREFIX"]
            if "lprefix" not in self._listener.userDict
            else ""
        )
        self._lsuffix = self._listener.userDict.get("lsuffix") or (
            config_dict["LEECH_FILENAME_SUFFIX"]
            if "lsuffix" not in self._listener.userDict
            else ""
        )
        self._lcapfont = self._listener.userDict.get("lcapfont") or (
            config_dict["LEECH_CAPTION_FONT"]
            if "lcapfont" not in self._listener.userDict
            else ""
        )
        if not await aiopath.exists(self._thumb): # type: ignore
            self._thumb = None

    async def _msg_to_reply(self):
        if DUMP_CHAT_ID := config_dict["DUMP_CHAT_ID"]:
            if self._listener.logMessage:
                self._sent_msg = await self._listener.logMessage.copy(DUMP_CHAT_ID)
            else:
                msg = f"<b>File Name</b>: <code>{escape(self._listener.name)}</code>\n\n"
                msg += f"<b>#Leech_Started!</b>\n"
                msg += f"<b>Req By</b>: {self._listener.tag}\n"
                msg += f"<b>User ID</b>: <code>{self._listener.message.from_user.id}</code>"
                self._sent_msg = await bot.send_message( # type: ignore
                    DUMP_CHAT_ID,
                    msg,
                    disable_web_page_preview=True
                )
            if self._listener.dmMessage:
                self._sent_DMmsg = self._listener.dmMessage
            if IS_PREMIUM_USER:
                try:
                    self._sent_msg = await user.get_messages( # type: ignore
                        chat_id=self._sent_msg.chat.id,
                        message_ids=self._sent_msg.id
                    )
                except RPCError as e:
                    await self._listener.onUploadError(
                        f"{e.NAME} [{e.CODE}]: {e.MESSAGE}"
                    )
                except Exception as e:
                    await self._listener.onUploadError(e)
        elif IS_PREMIUM_USER:
            if not self._listener.isSuperChat:
                await self._listener.onUploadError(
                    "Use SuperGroup to leech with User!"
                )
                return False
            self._sent_msg = self._listener.message
            try:
                self._sent_msg = await user.get_messages( # type: ignore
                    chat_id=self._sent_msg.chat.id,
                    message_ids=self._sent_msg.id
                )
            except RPCError as e:
                await self._listener.onUploadError(
                    f"{e.NAME} [{e.CODE}]: {e.MESSAGE}"
                )
            except Exception as e:
                await self._listener.onUploadError(e)
            if self._listener.dmMessage:
                self._sent_DMmsg = self._listener.dmMessage
        elif self._listener.dmMessage:
            self._sent_msg = self._listener.dmMessage
        else:
            self._sent_msg = self._listener.message
        if self._sent_msg is None:
            await self._listener.onUploadError(
                "Cannot find the message to reply"
            )
            return False
        return True

    async def _prepare_file(self, file_, dirpath, delete_file):
        if self._lprefix or self._lsuffix:
            if self._lprefix:
                cap_mono = f"{self._lprefix} {file_}"
                self._lprefix = re_sub(
                    "<.*?>",
                    "",
                    self._lprefix
                )
            else:
                cap_mono = f"{file_}"

            if self._lsuffix:
                cap_mono = f"{cap_mono} {self._lsuffix}"
                self._lsuffix = re_sub(
                    "<.*?>",
                    "",
                    self._lsuffix
                )
            if (
                self._listener.seed
                and not self._listener.newDir
                and not dirpath.endswith("/splited_files_zee")
                and not delete_file
            ):
                dirpath = f"{dirpath}/copied_zee"
                await makedirs(
                    dirpath,
                    exist_ok=True
                )
                new_path = ospath.join(
                    dirpath,
                    f"{self._lprefix} {file_} {self._lsuffix}"
                )
                self._up_path = await copy(
                    self._up_path,
                    new_path
                )
            else:
                new_path = ospath.join(
                    dirpath,
                    f"{self._lprefix} {file_} {self._lsuffix}"
                )
                await rename(
                    self._up_path,
                    new_path
                )
                self._up_path = new_path
        else:
            cap_mono = f"{file_}"

        if len(file_) > 60:
            if is_archive(file_):
                name = get_base_name(file_)
                ext = file_.split(
                    name,
                    1
                )[1]
            elif match := re_match(
                r".+(?=\..+\.0*\d+$)|.+(?=\.part\d+\..+$)",
                file_
            ):
                name = match.group(0)
                ext = file_.split(
                    name,
                    1
                )[1]
            elif len(fsplit := ospath.splitext(file_)) > 1:
                name = fsplit[0]
                ext = fsplit[1]
            else:
                name = file_
                ext = ""
            extn = len(ext)
            remain = 60 - extn
            name = name[:remain]
            if (
                self._listener.seed
                and not self._listener.newDir
                and not dirpath.endswith("/splited_files_zee")
                and not delete_file
            ):
                dirpath = f"{dirpath}/copied_zee"
                await makedirs(
                    dirpath,
                    exist_ok=True
                )
                new_path = ospath.join(
                    dirpath,
                    f"{name}{ext}"
                )
                self._up_path = await copy(
                    self._up_path,
                    new_path
                )
            else:
                new_path = ospath.join(
                    dirpath,
                    f"{name}{ext}"
                )
                await rename(
                    self._up_path,
                    new_path
                )
                self._up_path = new_path
        return cap_mono

    async def _prepare_caption_font(self, cap_mono):
        font_styles = {
            "monospace": "code",
            "mono": "code",
            "m": "code",
            "bold": "b",
            "b": "b",
            "italic": "i",
            "i": "i",
            "underline": "u",
            "u": "u",
            "bi": "bi",
            "bu": "bu",
            "iu": "iu",
            "biu": "biu"
        }

        style = self._lcapfont.lower()
        if style in font_styles:
            tags = font_styles[style]
            if tags in [
                "bi",
                "bu",
                "iu",
                "biu"
            ]:
                cap_mono = f"<{tags[0]}><{tags[1]}>{cap_mono}</{tags[1]}></{tags[0]}>"
            else:
                cap_mono = f"<{tags}>{cap_mono}</{tags}>"
        return cap_mono

    def _get_input_media(self, subkey, key, msg_list=None):
        rlist = []
        msgs = []
        if msg_list:
            for msg in msg_list:
                media_msg = bot.get_messages( # type: ignore
                    msg.chat.id,
                    msg.id
                )
                msgs.append(media_msg)
        else:
            msgs = self._media_dict[key][subkey]
        for msg in msgs:
            if key == "videos":
                input_media = InputMediaVideo(
                    media=msg.video.file_id,
                    caption=msg.caption
                )
            else:
                input_media = InputMediaDocument(
                    media=msg.document.file_id,
                    caption=msg.caption
                )
            rlist.append(input_media)
        return rlist

    async def _send_screenshots(self, dirpath, outputs):
        inputs = [
            InputMediaPhoto(
                ospath.join(dirpath, p),
                p.rsplit(
                    "/",
                    1
                )[-1]
            )
            for p in outputs
        ]
        self._sent_msg = (
            await self._sent_msg.reply_media_group( # type: ignore
                media=inputs,
                quote=True,
                disable_notification=True,
            )
        )[-1]
        if self._sent_DMmsg:
            try:
                self._sent_DMmsg = (
                    await self._sent_DMmsg.reply_media_group( # type: ignore
                        media=inputs,
                        quote=True,
                        disable_notification=True,
                    )
                )[-1]
            except Exception as err:
                LOGGER.error(
                    f"Unable to send media group in DM {err.__class__.__name__}"
                )
                self._sent_DMmsg = None

    async def _send_media_group(self, subkey, key, msgs):
        for index, msg in enumerate(msgs):
            if self._listener.mixedLeech or not self._user_session: # type: ignore
                msgs[index] = await self._listener.client.get_messages(
                    chat_id=msg[0],
                    message_ids=msg[1]
                )
            else:
                msgs[index] = await user.get_messages( # type: ignore
                    chat_id=msg[0],
                    message_ids=msg[1]
                )
        msgs_list = await msgs[0].reply_to_message.reply_media_group(
            media=self._get_input_media(
                subkey,
                key
            ),
            quote=True,
            disable_notification=True,
        )
        for msg in msgs:
            if msg.link in self._msgs_dict:
                del self._msgs_dict[msg.link]
            await deleteMessage(msg)
        del self._media_dict[key][subkey]
        if (
            self._listener.isSuperChat
            or self._listener.upDest
            or config_dict["DUMP_CHAT_ID"]
        ):
            for m in msgs_list:
                self._msgs_dict[m.link] = m.caption
        self._sent_msg = msgs_list[-1]
        if self._sent_DMmsg:
            await sleep(0.5)
            try:
                if IS_PREMIUM_USER:
                    grouped_media = self._get_input_media(
                        subkey,
                        key,
                        msgs_list
                    )
                dm_msgs_list = await self._sent_DMmsg.reply_media_group(
                    media=grouped_media,
                    quote=True
                )
                self._sent_DMmsg = dm_msgs_list[-1]
            except Exception as err:
                LOGGER.error(
                    f"Unable to send media group in DM {err.__class__.__name__}"
                )
                self._sent_DMmsg = None

    async def upload(self, o_files, ft_delete):
        await self._user_settings()
        res = await self._msg_to_reply()
        if not res:
            return
        for dirpath, _, files in natsorted(
            await sync_to_async(
                walk,
                self._path
            )
        ):
            if dirpath.endswith("/yt-dlp-thumb"):
                continue
            if dirpath.endswith("_zeess"):
                await self._send_screenshots(
                    dirpath,
                    files
                )
                await rmtree(
                    dirpath,
                    ignore_errors=True
                )
                continue
            for file_ in natsorted(files):
                delete_file = False
                self._up_path = f_path = ospath.join(
                    dirpath,
                    file_
                )
                if self._up_path in ft_delete:
                    delete_file = True
                if self._up_path in o_files:
                    continue
                if file_.lower().endswith(
                    tuple(self._listener.extensionFilter)
                ):
                    if (
                        not self._listener.seed
                        or self._listener.newDir
                    ):
                        await remove(self._up_path)
                    continue
                try:
                    f_size = await aiopath.getsize(self._up_path)
                    self._total_files += 1
                    if f_size == 0:
                        LOGGER.error(
                            f"{self._up_path} size is zero, telegram don't upload zero size files"
                        )
                        self._corrupted += 1
                        continue
                    if self._listener.isCancelled:
                        return
                    cap_mono = await self._prepare_file(
                        file_,
                        dirpath,
                        delete_file
                    )
                    cap_mono = await self._prepare_caption_font(cap_mono)
                    if self._last_msg_in_group:
                        group_lists = [
                            x for v in self._media_dict.values() for x in v.keys()
                        ]
                        match = re_match(
                            r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)",
                            f_path
                        )
                        if (
                            not match
                            or match
                            and match.group(0)
                            not in group_lists
                        ):
                            for key, value in list(self._media_dict.items()):
                                for subkey, msgs in list(value.items()):
                                    if len(msgs) > 1:
                                        await self._send_media_group(
                                            subkey,
                                            key,
                                            msgs
                                        )
                    if self._listener.mixedLeech:
                        self._user_session = f_size > 2097152000
                        if self._user_session:
                            self._sent_msg = await user.get_messages( # type: ignore
                                chat_id=self._sent_msg.chat.id,
                                message_ids=self._sent_msg.id,
                            )
                        else:
                            self._sent_msg = await self._listener.client.get_messages(
                                chat_id=self._sent_msg.chat.id, # type: ignore
                                message_ids=self._sent_msg.id, # type: ignore
                            )
                    self._last_msg_in_group = False
                    self._last_uploaded = 0
                    await self._upload_file(
                        cap_mono,
                        file_,
                        f_path
                    )
                    if self._listener.isCancelled:
                        return
                    if (
                        not self._is_corrupted
                        and (self._listener.isSuperChat or self._listener.upDest)
                        and not self._is_private
                    ):
                        self._msgs_dict[self._sent_msg.link] = file_ # type: ignore
                    await sleep(1)
                except Exception as err:
                    if isinstance(
                        err,
                        RetryError
                    ):
                        LOGGER.info(
                            f"Total Attempts: {err.last_attempt.attempt_number}" # type: ignore
                        )
                        err = err.last_attempt.exception() # type: ignore
                    LOGGER.error(f"{err}. Path: {self._up_path}")
                    self._corrupted += 1
                    if self._listener.isCancelled:
                        return
                    continue
                finally:
                    if (
                        not self._listener.isCancelled
                        and await aiopath.exists(self._up_path)
                        and (
                            not self._listener.seed
                            or self._listener.newDir
                            or dirpath.endswith("/splited_files_zee")
                            or "/copied_zee/" in self._up_path
                            or delete_file
                        )
                    ):
                        await remove(self._up_path)
        for key, value in list(self._media_dict.items()):
            for subkey, msgs in list(value.items()):
                if len(msgs) > 1:
                    try:
                        await self._send_media_group(
                            subkey,
                            key,
                            msgs
                        )
                    except Exception as e:
                        LOGGER.info(
                            f"While sending media group at the end of task. Error: {e}"
                        )
        if self._listener.isCancelled:
            return
        if (
            self._listener.seed
            and not self._listener.newDir
        ):
            await clean_unwanted(self._path)
        if self._total_files == 0:
            await self._listener.onUploadError(
                "No files to upload. In case you have filled EXTENSION_FILTER, then check if all files have those extensions or not."
            )
            return
        if self._total_files <= self._corrupted:
            await self._listener.onUploadError(
                "Files Corrupted or unable to upload. Check logs!"
            )
            return
        if config_dict["DUMP_CHAT_ID"]:
            msg = f"<b>File Name</b>: <code>{escape(self._listener.name)}</code>\n\n"
            msg += f"<b>#Leech_Completed</b>!\n"
            msg_ = f"<b>Done By</b>: {self._listener.tag}\n"
            msg_ += f"<b>User ID</b>: <code>{self._listener.message.from_user.id}</code>"
            if self._sent_msg is not None:
                await self._sent_msg.reply(
                    text=msg + msg_,
                    quote=True,
                    disable_web_page_preview=True
                )
            if self._sent_DMmsg:
                await self._sent_DMmsg.reply(
                    text=msg,
                    quote=True,
                    disable_web_page_preview=True
                )
        LOGGER.info(f"Leech Completed: {self._listener.name}")
        await self._listener.onUploadComplete(
            None,
            self._msgs_dict,
            self._total_files,
            self._corrupted
        )

    @retry(
        wait=wait_exponential(
            multiplier=2,
            min=4,
            max=8
        ),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    async def _send_dm(self):
        try:
            self._sent_DMmsg = await self._sent_DMmsg._client.copy_message( # type: ignore
                chat_id=self._sent_DMmsg.chat.id, # type: ignore
                message_id=self._sent_msg.id, # type: ignore
                from_chat_id=self._sent_msg.chat.id, # type: ignore
                reply_to_message_id=self._sent_DMmsg.id # type: ignore
            )
        except Exception as err:
            if isinstance(err, RPCError):
                LOGGER.error(
                    f"Error while sending dm {err.NAME}: {err.MESSAGE}")
            else:
                LOGGER.error(
                    f"Error while sending dm {err.__class__.__name__}")
            self._sent_DMmsg = None

    @retry(
        wait=wait_exponential(
            multiplier=2,
            min=4,
            max=8
        ),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
    )
    async def _upload_file(self, cap_mono, file, o_path, force_document=False):
        if (
            self._thumb is not None
            and not await aiopath.exists(self._thumb)
        ):
            self._thumb = None
        thumb = self._thumb
        self._is_corrupted = False
        try:
            is_video, is_audio, is_image = await get_document_type(self._up_path)

            if not is_image and thumb is None:
                file_name = ospath.splitext(file)[0]
                thumb_path = f"{self._path}/yt-dlp-thumb/{file_name}.jpg"
                if await aiopath.isfile(thumb_path):
                    thumb = thumb_path
                elif is_audio and not is_video:
                    thumb = await get_audio_thumb(self._up_path)

            if (
                self._listener.asDoc
                or force_document
                or (
                    not is_video
                    and not is_audio
                    and not is_image
                )
            ):
                key = "documents"
                if is_video and thumb is None:
                    thumb = await create_thumbnail(
                        self._up_path,
                        None
                    )

                if self._listener.isCancelled:
                    return
                self._sent_msg = await self._sent_msg.reply_document( # type: ignore
                    document=self._up_path,
                    quote=True,
                    thumb=thumb,
                    caption=cap_mono,
                    force_document=True,
                    disable_notification=True,
                    progress=self._upload_progress,
                )
            elif is_video:
                key = "videos"
                duration = (await get_media_info(self._up_path))[0]
                if thumb is None:
                    thumb = await create_thumbnail(
                        self._up_path,
                        duration
                    )
                if thumb is not None:
                    with Image.open(thumb) as img:
                        width, height = img.size
                else:
                    width = 480
                    height = 320
                if self._listener.isCancelled:
                    return
                self._sent_msg = await self._sent_msg.reply_video( # type: ignore
                    video=self._up_path,
                    quote=True,
                    caption=cap_mono,
                    duration=duration,
                    width=width,
                    height=height,
                    thumb=thumb,
                    supports_streaming=True,
                    disable_notification=True,
                    progress=self._upload_progress,
                )
            elif is_audio:
                key = "audios"
                duration, artist, title = await get_media_info(self._up_path)
                if self._listener.isCancelled:
                    return
                self._sent_msg = await self._sent_msg.reply_audio( # type: ignore
                    audio=self._up_path,
                    quote=True,
                    caption=cap_mono,
                    duration=duration,
                    performer=artist,
                    title=title,
                    thumb=thumb,
                    disable_notification=True,
                    progress=self._upload_progress,
                )
            else:
                key = "photos"
                if self._listener.isCancelled:
                    return
                self._sent_msg = await self._sent_msg.reply_photo( # type: ignore
                    photo=self._up_path,
                    quote=True,
                    caption=cap_mono,
                    disable_notification=True,
                    progress=self._upload_progress,
                )

            if (
                not self._listener.isCancelled
                and self._media_group
                and (
                    self._sent_msg.video
                    or self._sent_msg.document
                )
            ):
                key = (
                    "documents"
                    if self._sent_msg.document
                    else "videos"
                )
                if match := re_match(
                    r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)",
                    o_path
                ):
                    pname = match.group(0)
                    if pname in self._media_dict[key].keys():
                        self._media_dict[key][pname].append(
                            [
                                self._sent_msg.chat.id,
                                self._sent_msg.id
                            ]
                        )
                    else:
                        self._media_dict[key][pname] = [
                            [
                                self._sent_msg.chat.id,
                                self._sent_msg.id
                            ]
                        ]
                    msgs = self._media_dict[key][pname]
                    if len(msgs) == 10:
                        await self._send_media_group(
                            pname,
                            key,
                            msgs
                        )
                    else:
                        self._last_msg_in_group = True
                elif (
                    not self._listener.isCancelled
                    and self._sent_DMmsg
                ):
                    await self._send_dm()
            elif (
                not self._listener.isCancelled
                and self._sent_DMmsg
            ):
                await self._send_dm()

            if (
                self._thumb is None
                and thumb is not None
                and await aiopath.exists(thumb)
            ):
                await remove(thumb)
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value * 1.3) # type: ignore
            if (
                self._thumb is None
                and thumb is not None
                and await aiopath.exists(thumb)
            ):
                await remove(thumb)
            return await self._upload_file(
                cap_mono,
                file,
                o_path
            )
        except Exception as err:
            if (
                self._thumb is None
                and thumb is not None
                and await aiopath.exists(thumb)
            ):
                await remove(thumb)
            err_type = (
                "RPCError: "
                if isinstance(
                    err,
                    RPCError
                )
                else ""
            )
            LOGGER.error(f"{err_type}{err}. Path: {self._up_path}")
            if (
                "Telegram says: [400" in str(err)
                and key != "documents"
            ):
                LOGGER.error(f"Retrying As Document. Path: {self._up_path}")
                return await self._upload_file(
                    cap_mono,
                    file,
                    o_path,
                    True
                )
            raise err

    @property
    def speed(self):
        try:
            return self._processed_bytes / (time() - self._start_time)
        except:
            return 0

    @property
    def processed_bytes(self):
        return self._processed_bytes

    async def cancel_task(self):
        self._listener.isCancelled = True
        LOGGER.info(f"Cancelling Upload: {self._listener.name}")
        await self._listener.onUploadError("Your upload has been cancelled!")
