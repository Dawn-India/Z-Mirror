#!/usr/bin/env python3
from asyncio import sleep
from html import escape
from logging import ERROR, getLogger
from os import path as ospath, walk
from re import match as re_match, sub as re_sub
from time import time

from aiofiles.os import makedirs, path as aiopath, remove as aioremove, rename as aiorename
from aioshutil import copy
from natsort import natsorted
from PIL import Image
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import InputMediaDocument, InputMediaVideo
from tenacity import (RetryError, retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

from bot import GLOBAL_EXTENSION_FILTER, IS_PREMIUM_USER, bot, config_dict, user, user_data
from bot.helper.ext_utils.bot_utils import get_readable_file_size, sync_to_async
from bot.helper.ext_utils.fs_utils import clean_unwanted, get_base_name, is_archive
from bot.helper.ext_utils.leech_utils import (get_document_type, get_media_info,
                                              take_ss, remove_unwanted, get_audio_thumb)
from bot.helper.telegram_helper.message_utils import deleteMessage

LOGGER = getLogger(__name__)
getLogger("pyrogram").setLevel(ERROR)


class TgUploader:

    def __init__(self, name=None, path=None, listener=None):
        self.name = name
        self.__last_uploaded = 0
        self.__processed_bytes = 0
        self.__listener = listener
        self.__path = path
        self.__start_time = time()
        self.__total_files = 0
        self.__is_cancelled = False
        self.__thumb = f"Thumbnails/{listener.message.from_user.id}.jpg"
        self.__msgs_dict = {}
        self.__corrupted = 0
        self.__is_corrupted = False
        self.__media_dict = {'videos': {}, 'documents': {}}
        self.__last_msg_in_group = False
        self.__up_path = ''
        self.__lprefix = ''
        self.__lremname = ''
        self.__as_doc = False
        self.__media_group = False
        self.__sent_DMmsg = None
        self.__button = None
        self.__upload_dest = None

    async def __upload_progress(self, current, total):
        if self.__is_cancelled:
            if IS_PREMIUM_USER:
                user.stop_transmission()
            bot.stop_transmission()
        chunk_size = current - self.__last_uploaded
        self.__last_uploaded = current
        self.__processed_bytes += chunk_size

    async def __user_settings(self):
        user_id = self.__listener.message.from_user.id
        user_dict = user_data.get(user_id, {})
        self.__as_doc = user_dict.get(
            'as_doc', False) or (config_dict['AS_DOCUMENT'] if 'as_doc' not in user_dict else False)
        self.__media_group = user_dict.get(
            'media_group') or (config_dict['MEDIA_GROUP'] if 'media_group' not in user_dict else False)
        self.__lprefix = user_dict.get(
            'lprefix') or (config_dict['LEECH_FILENAME_PREFIX'] if 'lprefix' not in user_dict else '')
        self.__lremname = user_dict.get(
            'lremname') or (config_dict['LEECH_REMOVE_UNWANTED'] if 'lremname' not in user_dict else '')
        if not await aiopath.exists(self.__thumb):
            self.__thumb = None
        self.__upload_dest = user_dict.get('user_dump') or config_dict['USER_DUMP']

    async def __msg_to_reply(self):
        if DUMP_CHAT_ID := config_dict['DUMP_CHAT_ID']:
            if self.__listener.logMessage:
                self.__sent_msg = await self.__listener.logMessage.copy(DUMP_CHAT_ID)
            else:
                msg = f'<b>File Name</b>: <code>{escape(self.name)}</code>\n\n<b>#Leech_Completed</b>!\n'
                msg += f'<b>Done By</b>: {self.__listener.tag}\n'
                msg += f'<b>User ID</b>: <code>{self.__listener.message.from_user.id}</code>'
                self.__sent_msg = await bot.send_message(DUMP_CHAT_ID, msg, disable_web_page_preview=True)
            if self.__listener.dmMessage:
                self.__sent_DMmsg = self.__listener.dmMessage
            if IS_PREMIUM_USER:
                try:
                    self.__sent_msg = await user.get_messages(chat_id=self.__sent_msg.chat.id, message_ids=self.__sent_msg.id)
                except RPCError as e:
                    await self.__listener.onUploadError(f'{e.NAME} [{e.CODE}]: {e.MESSAGE}')
                except Exception as e:
                    await self.__listener.onUploadError(e)
        elif IS_PREMIUM_USER:
            if not self.__listener.isSuperGroup:
                await self.__listener.onUploadError('Use SuperGroup to leech with User!')
                return False
            self.__sent_msg = self.__listener.message
            try:
                self.__sent_msg = await user.get_messages(chat_id=self.__sent_msg.chat.id, message_ids=self.__sent_msg.id)
            except RPCError as e:
                await self.__listener.onUploadError(f'{e.NAME} [{e.CODE}]: {e.MESSAGE}')
            except Exception as e:
                await self.__listener.onUploadError(e)
            if self.__listener.dmMessage:
                self.__sent_DMmsg = self.__listener.dmMessage
        elif self.__listener.dmMessage:
            self.__sent_msg = self.__listener.dmMessage
        else:
            self.__sent_msg = self.__listener.message
        if self.__sent_msg is None:
            await self.__listener.onUploadError('Cannot find the message to reply')
            return False
        return True

    async def __prepare_file(self, file_, dirpath):
        if self.__lprefix or self.__lremname:
            file_ = await remove_unwanted(file_, self.__lremname)
            cap_mono = f"<b>{self.__lprefix} {file_}</b>"
            self.__lprefix = re_sub('<.*?>', '', self.__lprefix)
            if self.__listener.seed and not self.__listener.newDir and not dirpath.endswith("/splited_files_z"):
                dirpath = f'{dirpath}/copied_z'
                await makedirs(dirpath, exist_ok=True)
                new_path = ospath.join(dirpath, f"{self.__lprefix} {file_}")
                self.__up_path = await copy(self.__up_path, new_path)
            else:
                new_path = ospath.join(dirpath, f"{self.__lprefix} {file_}")
                await aiorename(self.__up_path, new_path)
                self.__up_path = new_path
        else:
            cap_mono = f"<b>{file_}</b>"
        if len(file_) > 60:
            if is_archive(file_):
                name = get_base_name(file_)
                ext = file_.split(name, 1)[1]
            elif match := re_match(r".+(?=\..+\.0*\d+$)|.+(?=\.part\d+\..+$)", file_):
                name = match.group(0)
                ext = file_.split(name, 1)[1]
            elif len(fsplit := ospath.splitext(file_)) > 1:
                name = fsplit[0]
                ext = fsplit[1]
            else:
                name = file_
                ext = ''
            extn = len(ext)
            remain = 60 - extn
            name = name[:remain]
            if self.__listener.seed and not self.__listener.newDir and not dirpath.endswith("/splited_files_z"):
                dirpath = f'{dirpath}/copied_z'
                await makedirs(dirpath, exist_ok=True)
                new_path = ospath.join(dirpath, f"{name}{ext}")
                self.__up_path = await copy(self.__up_path, new_path)
            else:
                new_path = ospath.join(dirpath, f"{name}{ext}")
                await aiorename(self.__up_path, new_path)
                self.__up_path = new_path
        return cap_mono

    async def __get_input_media(self, subkey, key, msg_list=None):
        rlist = []
        msgs = []
        if msg_list:
            for msg in msg_list:
                media_msg = await bot.get_messages(msg.chat.id, msg.id)
                msgs.append(media_msg)
        else:
            msgs = self.__media_dict[key][subkey]
        for msg in msgs:
            if key == 'videos':
                input_media = InputMediaVideo(
                    media=msg.video.file_id, caption=msg.caption)
            else:
                input_media = InputMediaDocument(
                    media=msg.document.file_id, caption=msg.caption)
            rlist.append(input_media)
        return rlist

    async def __send_media_group(self, subkey, key, msgs):
        grouped_media = await self.__get_input_media(subkey, key)
        msgs_list = await msgs[0].reply_to_message.reply_media_group(media=grouped_media,
                                                                     quote=True,
                                                                     disable_notification=True)
        for msg in msgs:
            if msg.link in self.__msgs_dict:
                del self.__msgs_dict[msg.link]
            await deleteMessage(msg)
        del self.__media_dict[key][subkey]
        if self.__listener.isSuperGroup or config_dict['DUMP_CHAT_ID']:
            for m in msgs_list:
                self.__msgs_dict[m.link] = m.caption
        self.__sent_msg = msgs_list[-1]
        if self.__sent_DMmsg:
            await sleep(0.5)
            try:
                if IS_PREMIUM_USER:
                    grouped_media = await self.__get_input_media(subkey, key, msgs_list)
                dm_msgs_list = await self.__sent_DMmsg.reply_media_group(media=grouped_media, quote=True)
                self.__sent_DMmsg = dm_msgs_list[-1]
            except Exception as err:
                LOGGER.error(f"Error while sending media group in dm {err.__class__.__name__}")
                self.__sent_DMmsg = None

    async def upload(self, o_files, m_size, size):
        res = await self.__msg_to_reply()
        if not res:
            return
        await self.__user_settings()
        for dirpath, _, files in sorted(await sync_to_async(walk, self.__path)):
            if dirpath.endswith('/yt-dlp-thumb'):
                continue
            for file_ in natsorted(files):
                self.__up_path = ospath.join(dirpath, file_)
                if file_.lower().endswith(tuple(GLOBAL_EXTENSION_FILTER)):
                    await aioremove(self.__up_path)
                    continue
                try:
                    f_size = await aiopath.getsize(self.__up_path)
                    if self.__listener.seed and file_ in o_files and f_size in m_size:
                        continue
                    self.__total_files += 1
                    if f_size == 0:
                        LOGGER.error(
                            f"{self.__up_path} size is zero, telegram don't upload zero size files")
                        self.__corrupted += 1
                        continue
                    if self.__is_cancelled:
                        return
                    cap_mono = await self.__prepare_file(file_, dirpath)
                    if self.__last_msg_in_group:
                        group_lists = [x for v in self.__media_dict.values()
                                       for x in v.keys()]
                        match = re_match(r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)", self.__up_path)
                        if not match or match and match.group(0) not in group_lists:
                            for key, value in list(self.__media_dict.items()):
                                for subkey, msgs in list(value.items()):
                                    if len(msgs) > 1:
                                        await self.__send_media_group(subkey, key, msgs)
                    self.__last_msg_in_group = False
                    self.__last_uploaded = 0
                    await self.__switching_client(f_size)
                    await self.__upload_file(cap_mono, file_)
                    if self.__is_cancelled:
                        return
                    if not self.__is_corrupted and (self.__listener.isSuperGroup or config_dict['DUMP_CHAT_ID']):
                        self.__msgs_dict[self.__sent_msg.link] = file_
                    await sleep(1)
                except Exception as err:
                    if isinstance(err, RetryError):
                        LOGGER.info(
                            f"Total Attempts: {err.last_attempt.attempt_number}")
                    else:
                        LOGGER.error(f"{err}. Path: {self.__up_path}")
                    if self.__is_cancelled:
                        return
                    continue
                finally:
                    if not self.__is_cancelled and await aiopath.exists(self.__up_path) and \
                        (not self.__listener.seed or self.__listener.newDir or
                         dirpath.endswith("/splited_files_z") or '/copied_z/' in self.__up_path):
                        await aioremove(self.__up_path)
        for key, value in list(self.__media_dict.items()):
            for subkey, msgs in list(value.items()):
                if len(msgs) > 1:
                    try:
                        await self.__send_media_group(subkey, key, msgs)
                    except Exception as e:
                        LOGGER.error(f"While sending media group at the end of task. Error: {e}")
        if self.__is_cancelled:
            return
        if self.__listener.seed and not self.__listener.newDir:
            await clean_unwanted(self.__path)
        if self.__total_files == 0:
            await self.__listener.onUploadError("No files to upload.")
            return
        if self.__total_files <= self.__corrupted:
            await self.__listener.onUploadError('Files Corrupted or unable to upload.')
            return
        if config_dict['DUMP_CHAT_ID']:
            msg = f'<b>File Name</b>: <code>{escape(self.name)}</code>\n\n'
            msg += f'<b>LeechCompleted</b>!\n<b>Done By</b>: {self.__listener.tag}\n'
            msg += f'<b>User ID</b>: <code>{self.__listener.message.from_user.id}</code>'
            await self.__sent_msg.reply(text=msg, quote=True, disable_web_page_preview=True)
        LOGGER.info(f"Leech Completed: {self.name}")
        await self.__listener.onUploadComplete(None, size, self.__msgs_dict, self.__total_files, self.__corrupted, self.name)

    async def __switching_client(self, f_size):
        if f_size < 2097152000 and not self.__sent_msg._client.me.is_bot:
            LOGGER.info(f'Upload using BOT_SESSION: size {get_readable_file_size(f_size)}')
            self.__sent_msg = await bot.get_messages(chat_id=self.__sent_msg.chat.id, message_ids=self.__sent_msg.id)
        if f_size > 2097152000 and IS_PREMIUM_USER and self.__sent_msg._client.me.is_bot:
            LOGGER.info(f'Upload using USER_SESSION: size {get_readable_file_size(f_size)}')
            self.__sent_msg = await user.get_messages(chat_id=self.__sent_msg.chat.id, message_ids=self.__sent_msg.id)

    async def __send_dm(self):
        try:
            self.__sent_DMmsg = await self.__sent_DMmsg._client.copy_message(
                chat_id=self.__sent_DMmsg.chat.id,
                message_id=self.__sent_msg.id,
                from_chat_id=self.__sent_msg.chat.id,
                reply_to_message_id=self.__sent_DMmsg.id
            )
        except Exception as err:
            if isinstance(err, RPCError):
                LOGGER.error(f"Error while sending dm {err.NAME}: {err.MESSAGE}")
            else:
                LOGGER.error(f"Error while sending dm {err.__class__.__name__}")
            self.__sent_DMmsg = None

    async def __send_to_udump(self):
        try:
            await bot.copy_message(
                chat_id=self.__upload_dest, 
                from_chat_id=self.__sent_msg.chat.id, 
                message_id=self.__sent_msg.id
            )
        except Exception as err:
            if isinstance(err, RPCError):
                LOGGER.error(f"Error while sending to user dump {err.NAME}: {err.MESSAGE}")
            else:
                LOGGER.error(f"Error while sending to user dump {err.__class__.__name__}")
            self.__upload_dest = None

    @retry(wait=wait_exponential(multiplier=2, min=4, max=8), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    async def __upload_file(self, cap_mono, file, force_document=False):
        if self.__thumb is not None and not await aiopath.exists(self.__thumb):
            self.__thumb = None
        thumb = self.__thumb
        self.__is_corrupted = False
        try:
            is_video, is_audio, is_image = await get_document_type(self.__up_path)

            if not is_image and thumb is None:
                file_name = ospath.splitext(file)[0]
                thumb_path = f"{self.__path}/yt-dlp-thumb/{file_name}.jpg"
                if await aiopath.isfile(thumb_path):
                    thumb = thumb_path
                elif is_audio and not is_video:
                    thumb = await get_audio_thumb(self.__up_path)

            if self.__as_doc or force_document or (not is_video and not is_audio and not is_image):
                key = 'documents'
                if is_video and thumb is None:
                    thumb = await take_ss(self.__up_path, None)
                if self.__is_cancelled:
                    return
                self.__sent_msg = await self.__sent_msg.reply_document(document=self.__up_path,
                                                                       quote=True,
                                                                       thumb=thumb,
                                                                       caption=cap_mono,
                                                                       force_document=True,
                                                                       reply_markup=self.__button,
                                                                       disable_notification=True,
                                                                       progress=self.__upload_progress)
            elif is_video:
                key = 'videos'
                duration = (await get_media_info(self.__up_path))[0]
                if thumb is None:
                    thumb = await take_ss(self.__up_path, duration)
                if thumb is not None:
                    with Image.open(thumb) as img:
                        width, height = img.size
                else:
                    width = 480
                    height = 320
                if not self.__up_path.upper().endswith(("MKV", "MP4")):
                    dirpath, file_ = self.__up_path.rsplit('/', 1)
                    if self.__listener.seed and not self.__listener.newDir and not dirpath.endswith("/splited_files_z"):
                        dirpath = f"{dirpath}/copied_z"
                        await makedirs(dirpath, exist_ok=True)
                        new_path = ospath.join(
                            dirpath, f"{ospath.splitext(file_)[0]}.mp4")
                        self.__up_path = await copy(self.__up_path, new_path)
                    else:
                        new_path = f"{ospath.splitext(self.__up_path)[0]}.mp4"
                        await aiorename(self.__up_path, new_path)
                        self.__up_path = new_path
                if self.__is_cancelled:
                    return
                self.__sent_msg = await self.__sent_msg.reply_video(video=self.__up_path,
                                                                    quote=True,
                                                                    caption=cap_mono,
                                                                    duration=duration,
                                                                    width=width,
                                                                    height=height,
                                                                    thumb=thumb,
                                                                    supports_streaming=True,
                                                                    reply_markup=self.__button,
                                                                    disable_notification=True,
                                                                    progress=self.__upload_progress)
            elif is_audio:
                key = 'audios'
                duration, artist, title = await get_media_info(self.__up_path)
                if self.__is_cancelled:
                    return
                self.__sent_msg = await self.__sent_msg.reply_audio(audio=self.__up_path,
                                                                    quote=True,
                                                                    caption=cap_mono,
                                                                    duration=duration,
                                                                    performer=artist,
                                                                    title=title,
                                                                    thumb=thumb,
                                                                    reply_markup=self.__button,
                                                                    disable_notification=True,
                                                                    progress=self.__upload_progress)
            else:
                key = 'photos'
                if self.__is_cancelled:
                    return
                self.__sent_msg = await self.__sent_msg.reply_photo(photo=self.__up_path,
                                                                    quote=True,
                                                                    caption=cap_mono,
                                                                    reply_markup=self.__button,
                                                                    disable_notification=True,
                                                                    progress=self.__upload_progress)

            if not self.__is_cancelled and self.__media_group and (self.__sent_msg.video or self.__sent_msg.document):
                key = 'documents' if self.__sent_msg.document else 'videos'
                if match := re_match(r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)", self.__up_path):
                    pname = match.group(0)
                    if pname in self.__media_dict[key].keys():
                        self.__media_dict[key][pname].append(self.__sent_msg)
                    else:
                        self.__media_dict[key][pname] = [self.__sent_msg]
                    msgs = self.__media_dict[key][pname]
                    if len(msgs) == 10:
                        await self.__send_media_group(pname, key, msgs)
                    else:
                        self.__last_msg_in_group = True
                elif self.__sent_DMmsg:
                    await self.__send_dm()
                if self.__upload_dest:
                    await self.__send_to_udump()
            elif self.__sent_DMmsg:
                await self.__send_dm()
            if self.__upload_dest:
                await self.__send_to_udump()
            if self.__thumb is None and thumb is not None and await aiopath.exists(thumb):
                await aioremove(thumb)
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value)
        except Exception as err:
            if self.__thumb is None and thumb is not None and await aiopath.exists(thumb):
                await aioremove(thumb)
            err_type = "RPCError: " if isinstance(err, RPCError) else ""
            LOGGER.error(f"{err_type}{err}. Path: {self.__up_path}")
            if 'Telegram says: [400' in str(err) and key != 'documents':
                LOGGER.error(f"Retrying As Document. Path: {self.__up_path}")
                return await self.__upload_file(cap_mono, file, True)
            raise err

    @property
    def speed(self):
        try:
            return self.__processed_bytes / (time() - self.__start_time)
        except:
            return 0

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Upload: {self.name}")
        await self.__listener.onUploadError('Leech stopped by user!')
