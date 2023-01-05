from bot import GLOBAL_EXTENSION_FILTER, app, config_dict, user_data
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.ext_utils.fs_utils import (clean_unwanted, get_media_info, get_media_streams, take_ss)
from copy import copy
from logging import ERROR, getLogger
from os import path as ospath
from os import remove, rename, walk
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument, InputMediaVideo)
from PIL import Image
from re import search, sub
from threading import RLock
from time import sleep, time
from telegram import InputMediaDocument as ptbInputMediaDocument
from telegram import InputMediaVideo as ptbInputMediaVideo

LOGGER = getLogger(__name__)
getLogger("pyrogram").setLevel(ERROR)

IMAGE_SUFFIXES = ("JPG", "JPX", "PNG", "CR2", "TIF", "BMP", "JXR", "PSD", "ICO", "HEIC", "JPEG")


class TgUploader:

    def __init__(self, name=None, path=None, size=0, listener=None):
        self.name = name
        self.uploaded_bytes = 0
        self._last_uploaded = 0
        self.__listener = listener
        self.__path = path
        self.__start_time = time()
        self.__total_files = 0
        self.__is_cancelled = False
        self.__thumb = f"Thumbnails/{listener.message.from_user.id}.jpg"
        self.__msgs_dict = {}
        self.__corrupted = 0
        self.__resource_lock = RLock()
        self.__is_corrupted = False
        self.__size = size
        self.__button = None
        self.__in_media_group = False
        self.__media_dict = {'videos': {}, 'documents': {}}
        self.__sent_DMmsg = None
        self.__msg_to_reply()
        self.__user_settings()

    def upload(self, o_files, m_size):
        for dirpath, _, files in sorted(walk(self.__path)):
            for file_ in sorted(files):
                up_path = ospath.join(dirpath, file_)
                f_size = ospath.getsize(up_path)
                if self.__listener.seed and file_ in o_files and f_size in m_size:
                    continue
                if not file_.lower().endswith(tuple(GLOBAL_EXTENSION_FILTER)):
                    self.__total_files += 1
                    try:
                        if f_size == 0:
                            LOGGER.error(f"{up_path} size is zero, telegram don't upload zero size files")
                            self.__corrupted += 1
                            continue
                    except Exception as e:
                        if self.__is_cancelled:
                            return
                        LOGGER.error(e)
                        continue
                    if self.__in_media_group:
                        group_lists = [x for v in self.__media_dict.values() for x in v.keys()]
                        match = search(r'.+(?=\.0*\d+$)|.+(?=\.part\d+\..+)', file_)
                        if match and match.group(0) not in group_lists:
                            for key, value in list(self.__media_dict.items()):
                                for pname, msgs in list(value.items()):
                                    if len(msgs) > 1:
                                        self.__send_media_group(pname, key, msgs)
                    self.__in_media_group = False
                    self.__upload_file(up_path, file_, dirpath)
                    if self.__is_cancelled:
                        return
                    if (not self.__listener.isPrivate or config_dict['DUMP_CHAT']) and not self.__is_corrupted and \
                          not self.__in_media_group:
                        self.__msgs_dict[self.__sent_msg.link] = file_
                    self._last_uploaded = 0
                    sleep(1)
        for key, value in list(self.__media_dict.items()):
            for pname, msgs in list(value.items()):
                if len(msgs) > 1:
                    self.__send_media_group(pname, key, msgs)
                elif not self.__listener.isPrivate or config_dict['DUMP_CHAT']:
                    self.__msgs_dict[msgs[0].link] = msgs[0].caption
        if self.__listener.seed and not self.__listener.newDir:
            clean_unwanted(self.__path)
        if self.__total_files == 0:
            self.__listener.onUploadError("No files to upload. In case you have filled EXTENSION_FILTER, then check if all file have those extensions or not.")
            return
        if self.__total_files <= self.__corrupted:
            self.__listener.onUploadError('Files Corrupted or unable to upload. Check logs!')
            return
        LOGGER.info(f"Leech Completed: {self.name}")
        size = get_readable_file_size(self.__size)
        self.__listener.onUploadComplete(None, size, self.__msgs_dict, self.__total_files, self.__corrupted, self.name)

    def __upload_file(self, up_path, file_, dirpath):
        if self.__lprefix:
            cap_mono = f"{self.__lprefix} <code>{file_}</code>"
            self.__lprefix = sub('<.*?>', '', self.__lprefix)
            file_ = f"{self.__lprefix} {file_}"
            new_path = ospath.join(dirpath, file_)
            rename(up_path, new_path)
            up_path = new_path
        else:
            cap_mono = f"<code>{file_}</code>"
        notMedia = False
        thumb = self.__thumb
        self.__is_corrupted = False
        try:
            is_video, is_audio = get_media_streams(up_path)
            if not self.__as_doc:
                if is_video:
                    duration = get_media_info(up_path)[0]
                    if thumb is None:
                        thumb = take_ss(up_path, duration)
                        if self.__is_cancelled:
                            if self.__thumb is None and thumb and ospath.lexists(thumb):
                                remove(thumb)
                            return
                    if thumb:
                        with Image.open(thumb) as img:
                            width, height = img.size
                    else:
                        width = 480
                        height = 320
                    if not file_.upper().endswith(("MKV", "MP4")):
                        file_ = f"{ospath.splitext(file_)[0]}.mp4"
                        new_path = ospath.join(dirpath, file_)
                        rename(up_path, new_path)
                        up_path = new_path
                    self.__sent_msg = self.__sent_msg.reply_video(video=up_path,
                                                                  quote=True,
                                                                  caption=cap_mono,
                                                                  duration=duration,
                                                                  width=width,
                                                                  height=height,
                                                                  thumb=thumb,
                                                                  supports_streaming=True,
                                                                  disable_notification=True,
                                                                  reply_markup=self.__button,
                                                                  progress=self.__upload_progress)
                elif is_audio:
                    duration , artist, title = get_media_info(up_path)
                    self.__sent_msg = self.__sent_msg.reply_audio(audio=up_path,
                                                                  quote=True,
                                                                  caption=cap_mono,
                                                                  duration=duration,
                                                                  performer=artist,
                                                                  title=title,
                                                                  thumb=thumb,
                                                                  disable_notification=True,
                                                                  reply_markup=self.__button,
                                                                  progress=self.__upload_progress)
                elif file_.upper().endswith(IMAGE_SUFFIXES):
                    self.__sent_msg = self.__sent_msg.reply_photo(photo=up_path,
                                                                  quote=True,
                                                                  caption=cap_mono,
                                                                  disable_notification=True,
                                                                  reply_markup=self.__button,
                                                                  progress=self.__upload_progress)
                else:
                    notMedia = True
            if self.__as_doc or notMedia:
                if is_video and thumb is None:
                    thumb = take_ss(up_path, None)
                    if self.__is_cancelled:
                        if self.__thumb is None and thumb and ospath.lexists(thumb):
                            remove(thumb)
                        return
                self.__sent_msg = self.__sent_msg.reply_document(document=up_path,
                                                                 quote=True,
                                                                 thumb=thumb,
                                                                 caption=cap_mono,
                                                                 disable_notification=True,
                                                                 reply_markup=self.__button,
                                                                 progress=self.__upload_progress)

            if self.__media_group and (self.__as_doc or notMedia or is_video):
                if match := search(r'.+(?=\.0*\d+$)|.+(?=\.part\d+\..+)', file_):
                    pname = match.group(0)
                    key = 'documents' if self.__as_doc or notMedia else 'videos'
                    if pname in self.__media_dict[key].keys():
                        self.__media_dict[key][pname].append(self.__sent_msg)
                    else:
                        self.__media_dict[key][pname] = [self.__sent_msg]
                    msgs = self.__media_dict[key][pname]
                    if len(msgs) == 10:
                        self.__send_media_group(pname, key, msgs)
                    else:
                        self.__in_media_group = True

            if not self.__in_media_group and self.__sent_DMmsg:
                sleep(1)
                __ptb = self.__sent_DMmsg.reply_copy(
                from_chat_id=self.__sent_msg.chat.id,
                reply_to_message_id=self.__sent_DMmsg.message_id,
                message_id=self.__sent_msg.id)
                self.__sent_DMmsg.message_id = __ptb['message_id']
        except FloodWait as f:
            LOGGER.warning(str(f))
            sleep(f.value)
        except RPCError as e:
            LOGGER.error(f"RPCError: {e} Path: {up_path}")
            self.__corrupted += 1
            self.__is_corrupted = True
        except Exception as err:
            LOGGER.error(f"{err} Path: {up_path}")
            self.__corrupted += 1
            self.__is_corrupted = True
        if not self.__thumb and thumb and ospath.lexists(thumb):
            remove(thumb)
        if not self.__is_cancelled and \
                   (not self.__listener.seed or self.__listener.newDir or dirpath.endswith("splited_files_mltb")):
            try:
                remove(up_path)
            except:
                pass

    def __upload_progress(self, current, total):
        if self.__is_cancelled:
            app.stop_transmission()
            return
        with self.__resource_lock:
            chunk_size = current - self._last_uploaded
            self._last_uploaded = current
            self.uploaded_bytes += chunk_size

    def __user_settings(self):
        user_id = self.__listener.message.from_user.id
        user_dict = user_data.get(user_id, False)
        self.__as_doc = user_dict and user_dict.get('as_doc', False) or config_dict['AS_DOCUMENT']
        self.__media_group = user_dict and user_dict.get('media_group', False) or config_dict['MEDIA_GROUP']
        self.__lprefix = user_dict and user_dict.get('lprefix', False) or config_dict['LEECH_FILENAME_PREFIX']
        if not ospath.lexists(self.__thumb):
            self.__thumb = None

    def __msg_to_reply(self):
        if DUMP_CHAT:= config_dict['DUMP_CHAT']:
            msg = self.__listener.message.text if self.__listener.isPrivate else self.__listener.message.link
            self.__sent_msg = app.send_message(DUMP_CHAT, msg, disable_web_page_preview=True)
            if self.__listener.dmMessage:
                self.__sent_DMmsg = copy(self.__listener.dmMessage)
        elif self.__listener.dmMessage:
            self.__sent_msg = app.get_messages(self.__listener.message.from_user.id, self.__listener.dmMessage.message_id)
        else:
            self.__sent_msg = app.get_messages(self.__listener.message.chat.id, self.__listener.uid)
        if self.__listener.message.chat.type != 'private' and not self.__listener.dmMessage:
            self.__button = InlineKeyboardMarkup([[InlineKeyboardButton(text='Send in PM', callback_data="save")]])

    def __get_input_media(self, pname, key):
        rlist = []
        for msg in self.__media_dict[key][pname]:
            if key == 'videos':
                input_media = InputMediaVideo(media=msg.video.file_id, caption=msg.caption)
            else:
                input_media = InputMediaDocument(media=msg.document.file_id, caption=msg.caption)
            rlist.append(input_media)
        return rlist

    def __get_ptb_input_media(self, pname, key):
        rlist = []
        for msg in self.__media_dict[key][pname]:
            if key == 'videos':
                input_media = ptbInputMediaVideo(media=msg.video.file_id, caption=msg.caption)
            else:
                input_media = ptbInputMediaDocument(media=msg.document.file_id, caption=msg.caption)
            rlist.append(input_media)
        return rlist

    def __send_media_group(self, pname, key, msgs):
        msgs_list = msgs[0].reply_to_message.reply_media_group(
            media=self.__get_input_media(pname, key),
            disable_notification=True)
        for msg in msgs:
            msg.delete()
        if not self.__listener.isPrivate or config_dict['DUMP_CHAT']:
            for m in msgs_list:
                self.__msgs_dict[m.link] = f'{m.caption} (Grouped)'
        self.__sent_msg = msgs_list[-1]
        if self.__sent_DMmsg:
            msgs_list = self.__sent_DMmsg.reply_media_group(
                self.__get_ptb_input_media(pname, key),
                reply_to_message_id=self.__sent_DMmsg.message_id,
                disable_notification=True
            )
            self.__sent_DMmsg = msgs_list[-1]
        del self.__media_dict[key][pname]

    @property
    def speed(self):
        with self.__resource_lock:
            try:
                return self.uploaded_bytes / (time() - self.__start_time)
            except:
                return 0

    def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Upload: {self.name}")
        self.__listener.onUploadError('your upload has been stopped!')
