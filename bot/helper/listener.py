from asyncio import Event, create_subprocess_exec, sleep
from html import escape
from os import path as ospath
from os import walk
from time import time

from aiofiles.os import listdir, makedirs
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from aiofiles.os import rename
from aioshutil import move
from urllib.parse import quote as url_quote

from bot import (bot, DATABASE_URL, DOWNLOAD_DIR, LOGGER, MAX_SPLIT_SIZE,
                 SHORTENERES, Interval, aria2, config_dict, download_dict,
                 download_dict_lock, non_queued_dl, non_queued_up,
                 queue_dict_lock, queued_dl, queued_up, status_reply_dict_lock,
                 user_data)
from bot.helper.ext_utils.bot_utils import (extra_btns, get_readable_time,
                                            sync_to_async)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive
from bot.helper.ext_utils.fs_utils import (clean_download, clean_target,
                                           get_base_name, get_path_size,
                                           is_archive, is_archive_split,
                                           is_first_archive_split, split_file)
from bot.helper.ext_utils.queued_starter import start_from_queued
from bot.helper.ext_utils.shortener import short_url
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.tg_upload_status import TgUploadStatus
from bot.helper.mirror_utils.status_utils.upload_status import UploadStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (delete_all_messages,
                                                      delete_links,
                                                      sendMessage,
                                                      update_all_messages)


class MirrorLeechListener:
    def __init__(self, message, isZip=False, extract=False, isQbit=False,
                isLeech=False, isClone=False, pswd=None, tag=None, select=False,
                seed=False, sameDir=None, raw_url=None,
                drive_id=None, index_link=None, dmMessage=None, logMessage=None):
        if not sameDir:
            sameDir = {}
        self.message = message
        self.uid = self.message.id
        self.extract = extract
        self.isZip = isZip
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.isClone = isClone
        self.pswd = pswd
        self.tag = tag
        self.seed = seed
        self.newDir = ""
        self.dir = f"{DOWNLOAD_DIR}{self.uid}"
        self.select = select
        self.isSuperGroup = self.message.chat.type in [self.message.chat.type.SUPERGROUP, self.message.chat.type.CHANNEL]
        self.suproc = None
        self.queuedUp = None
        self.sameDir = sameDir
        self.raw_url = raw_url
        self.drive_id = drive_id
        self.index_link = index_link
        self.dmMessage = dmMessage
        self.logMessage = logMessage
        self.startTime = time()
        self.__setMode()
        self.__source()

    async def clean(self):
        try:
            async with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
            await sync_to_async(aria2.purge)
            await delete_all_messages()
        except:
            pass

    def __setMode(self):
        if self.isLeech:
            mode = 'Leech'
        elif self.isClone:
            mode = 'Clone'
        else:
            mode = 'Drive'
        if self.isZip:
            mode += ' as Zip'
        elif self.extract:
            mode += ' as Unzip'
        self.mode = mode

    def __source(self):
        if sender_chat:= self.message.sender_chat:
            source = sender_chat.title
        else:
            source = self.message.from_user.username or self.message.from_user.id
        if reply_to := self.message.reply_to_message:
            if sender_chat:=reply_to.sender_chat:
                source = reply_to.sender_chat.title
            elif not reply_to.from_user.is_bot:
                source = reply_to.from_user.username or reply_to.from_user.id
        if self.isSuperGroup:
            self.source = f"<a href='{self.message.link}'>{source}</a>"
        else:
            self.source = f"<i>{source}</i>"

    async def onDownloadStart(self):
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            await DbManger().add_download_url(self.raw_url, self.tag)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)

    async def onDownloadComplete(self):
        if len(self.sameDir) == 1:
            await sleep(3)
        multi_links = False
        async with download_dict_lock:
            if len(self.sameDir) > 1:
                self.sameDir.remove(self.uid)
                folder_name = (await listdir(self.dir))[-1]
                path = f"{self.dir}/{folder_name}"
                des_path = f"{DOWNLOAD_DIR}{list(self.sameDir)[0]}/{folder_name}"
                await makedirs(des_path, exist_ok=True)
                for subdir in await listdir(path):
                    sub_path = f"{self.dir}/{folder_name}/{subdir}"
                    if subdir in await listdir(des_path):
                        sub_path = await rename(sub_path, f"{self.dir}/{folder_name}/1-{subdir}")
                    await move(sub_path, des_path)
                multi_links = True
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
        LOGGER.info(f"Download completed: {name}")
        if multi_links:
            await self.onUploadError('Downloaded! Waiting for other tasks...')
            return
        if name == "None" or self.isQbit or not await aiopath.exists(f"{self.dir}/{name}"):
            name = (await listdir(self.dir))[-1]
        m_path = f"{self.dir}/{name}"
        size = await get_path_size(m_path)
        async with queue_dict_lock:
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
        await start_from_queued()
        user_dict = user_data.get(self.message.from_user.id, {})
        if self.isZip:
            if self.seed and self.isLeech:
                self.newDir = f"{self.dir}10000"
                path = f"{self.newDir}/{name}.zip"
            else:
                path = f"{m_path}.zip"
            async with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            LEECH_SPLIT_SIZE = user_dict.get('split_size', False) or config_dict['LEECH_SPLIT_SIZE']
            cmd = ["7z", f"-v{LEECH_SPLIT_SIZE}b", "a", "-mx=0", f"-p{self.pswd}", path, m_path]
            if self.isLeech and int(size) > LEECH_SPLIT_SIZE:
                if not self.pswd:
                    del cmd[4]
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
            else:
                del cmd[1]
                if not self.pswd:
                    del cmd[3]
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
            self.suproc = await create_subprocess_exec(*cmd)
            await self.suproc.wait()
            if self.suproc.returncode == -9:
                return
            elif not self.seed:
                await clean_target(m_path)
        elif self.extract:
            try:
                if await aiopath.isfile(m_path):
                    path = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                async with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(name, size, gid, self)
                if await aiopath.isdir(m_path):
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        path = f"{self.newDir}/{name}"
                    else:
                        path = m_path
                    for dirpath, subdir, files in await sync_to_async(walk, m_path, topdown=False):
                        for file_ in files:
                            if is_first_archive_split(file_) or is_archive(file_) and not file_.endswith('.rar'):
                                f_path = ospath.join(dirpath, file_)
                                t_path = dirpath.replace(self.dir, self.newDir) if self.seed else dirpath
                                cmd = ["7z", "x", f"-p{self.pswd}", f_path, f"-o{t_path}", "-aot", "-xr!@PaxHeader"]
                                if not self.pswd:
                                    del cmd[2]
                                self.suproc = await create_subprocess_exec(*cmd)
                                await self.suproc.wait()
                                if self.suproc.returncode == -9:
                                    return
                                elif self.suproc.returncode != 0:
                                    LOGGER.error('Unable to extract archive splits!')
                        if not self.seed and self.suproc and self.suproc.returncode == 0:
                            for file_ in files:
                                if is_archive_split(file_) or is_archive(file_):
                                    del_path = ospath.join(dirpath, file_)
                                    try:
                                        await aioremove(del_path)
                                    except:
                                        return
                else:
                    if self.seed and self.isLeech:
                        self.newDir = f"{self.dir}10000"
                        path = path.replace(self.dir, self.newDir)
                    cmd = ["7z", "x", f"-p{self.pswd}", m_path, f"-o{path}", "-aot", "-xr!@PaxHeader"]
                    if not self.pswd:
                        del cmd[2]
                    self.suproc = await create_subprocess_exec(*cmd)
                    await self.suproc.wait()
                    if self.suproc.returncode == -9:
                        return
                    elif self.suproc.returncode == 0:
                        LOGGER.info(f"Extracted Path: {path}")
                        if not self.seed:
                            try:
                                await aioremove(m_path)
                            except:
                                return
                    else:
                        LOGGER.error('Unable to extract archive! Uploading anyway')
                        self.newDir = ""
                        path = m_path
            except NotSupportedExtractionArchive:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                self.newDir = ""
                path = m_path
        else:
            path = m_path
        up_dir, up_name = path.rsplit('/', 1)
        size = await get_path_size(up_dir)
        if self.isLeech:
            m_size = []
            o_files = []
            if not self.isZip:
                checked = False
                LEECH_SPLIT_SIZE = user_dict.get('split_size', False) or config_dict['LEECH_SPLIT_SIZE']
                for dirpath, subdir, files in await sync_to_async(walk, up_dir, topdown=False):
                    for file_ in files:
                        f_path = ospath.join(dirpath, file_)
                        f_size = await aiopath.getsize(f_path)
                        if f_size > LEECH_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                async with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(up_name, size, gid, self)
                                LOGGER.info(f"Splitting: {up_name}")
                            res = await split_file(f_path, f_size, file_, dirpath, LEECH_SPLIT_SIZE, self)
                            if not res:
                                return
                            if res == "errored":
                                if f_size <= MAX_SPLIT_SIZE:
                                    continue
                                try:
                                    await aioremove(f_path)
                                except:
                                    return
                            elif not self.seed or self.newDir:
                                try:
                                    await aioremove(f_path)
                                except:
                                    return
                            else:
                                m_size.append(f_size)
                                o_files.append(file_)

        up_limit = config_dict['QUEUE_UPLOAD']
        all_limit = config_dict['QUEUE_ALL']
        added_to_queue = False
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not up_limit or up >= up_limit)) or (up_limit and up >= up_limit):
                added_to_queue = True
                LOGGER.info(f"Added to Queue/Upload: {name}")
                queued_up[self.uid] = self
        if added_to_queue:
            async with download_dict_lock:
                download_dict[self.uid] = QueueStatus(name, size, gid, self, 'Up')
            self.queuedUp = Event()
            await self.queuedUp.wait()
            async with download_dict_lock:
                if self.uid not in download_dict.keys():
                    return
            LOGGER.info(f'Start from Queued/Upload: {name}')
        async with queue_dict_lock:
            non_queued_up.add(self.uid)

        if self.isLeech:
            size = await get_path_size(up_dir)
            for s in m_size:
                size = size - s
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, up_dir, size, self)
            tg_upload_status = TgUploadStatus(tg, size, gid, self)
            async with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            await update_all_messages()
            await tg.upload(o_files, m_size)
        else:
            up_path = f'{up_dir}/{up_name}'
            size = await get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, up_dir, size, self)
            upload_status = UploadStatus(drive, size, gid, self)
            async with download_dict_lock:
                download_dict[self.uid] = upload_status
            await update_all_messages()
            await sync_to_async(drive.upload, up_name, self.drive_id or config_dict['GDRIVE_ID'])

    async def onUploadComplete(self, link: str, size, files, folders, typ, name, drive_id=None):
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            await DbManger().remove_download(self.raw_url)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)
        lmsg = f'<b>File Name</b>: <code>{escape(name)}</code>'
        lmsg += f'\n\n<b>#cc</b>: {self.tag}'
        gmsg = f'Hey <b>{self.tag}</b>! Your job is done.'
        msg = f'\n\n<b>Size</b>: {size}'
        msg += f"\n<b>Elapsed</b>: {get_readable_time(time() - self.startTime)}"
        msg += f"\n<b>Upload</b>: {self.mode}"
        buttons = ButtonMaker()
        if self.isLeech:
            msg += f'\n<b>Total Files</b>: {folders}\n\n'
            if typ != 0:
                msg += f'\n<b>Corrupted Files</b>: {typ}'
            msg_ = '\n<b>Files has been sent in your DM.</b>'
            if not self.dmMessage:
                if not files:
                    await sendMessage(self.message, lmsg + msg)
                    if self.logMessage:
                        await sendMessage(self.logMessage, lmsg + msg)
                else:
                    fmsg = ''
                    for index, (link, name) in enumerate(files.items(), start=1):
                        fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                        if len(fmsg.encode() + msg.encode()) > 4000:
                            if self.logMessage:
                                await sendMessage(self.logMessage, lmsg + msg + fmsg)
                            await sendMessage(self.message, lmsg + msg + fmsg)
                            await sleep(1)
                            fmsg = ''
                    if fmsg != '':
                        if self.logMessage:
                            await sendMessage(self.logMessage, lmsg + msg + fmsg)
                        await sendMessage(self.message, lmsg + msg + fmsg)
            else:
                if not files:
                    await sendMessage(self.message, gmsg + msg + msg_)
                    if self.logMessage:
                        await sendMessage(self.logMessage, lmsg + msg)
                elif self.dmMessage and not config_dict['DUMP_CHAT']:
                    await sendMessage(self.dmMessage, lmsg + msg)
                    await sendMessage( self.message, gmsg + msg + msg_)
                    if self.logMessage:
                        await sendMessage(self.logMessage, lmsg + msg)
                else:
                    fmsg = ''
                    for index, (link, name) in enumerate(files.items(), start=1):
                        fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                        if len(fmsg.encode() + msg.encode()) > 4000:
                            if self.logMessage:
                                await sendMessage(self.logMessage, lmsg + msg + fmsg)
                            await sendMessage(self.message, gmsg + msg + fmsg + msg_)
                            await sleep(1)
                            fmsg = ''
                    if fmsg != '':
                        if self.logMessage:
                            await sendMessage(self.logMessage, lmsg + msg + fmsg)
                        await sendMessage(self.message, gmsg + msg + fmsg + msg_)
            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                return
        else:
            msg += f'\n<b>Type</b>: {typ}'
            if typ == "Folder":
                msg += f' |<b>SubFolders</b>: {folders}'
                msg += f' |<b>Files</b>: {files}'
            if not config_dict['DISABLE_DRIVE_LINK']:
                link = await sync_to_async(short_url, link)
                buttons.ubutton("🔐 Drive Link", link)
            LOGGER.info(f'Done Uploading {name}')
            if INDEX_URL:= self.index_link or config_dict['INDEX_URL']:
                url_path = url_quote(f'{name}')
                if typ == "Folder":
                    share_url = await sync_to_async(short_url, f'{INDEX_URL}/{url_path}/')
                    buttons.ubutton("📁 Index Link", share_url)
                else:
                    share_url = await sync_to_async(short_url, f'{INDEX_URL}/{url_path}')
                    buttons.ubutton("🚀 Index Link", share_url)
                    if config_dict['VIEW_LINK']:
                        share_urls = await sync_to_async(short_url, f'{INDEX_URL}/{url_path}?a=view')
                        buttons.ubutton("💻 View Link", share_urls)
            buttons = extra_btns(buttons)
            if self.dmMessage:
                await sendMessage(self.dmMessage, lmsg + msg, buttons.build_menu(2))
                msg_ = '\n\n<b>Links has been sent in your DM.</b>'
                await sendMessage(self.message, gmsg + msg + msg_)
            else:
                await sendMessage(self.message, lmsg + msg, buttons.build_menu(2))
            if self.logMessage:
                if config_dict['DISABLE_DRIVE_LINK']:
                    buttons.ubutton("🔐 Drive Link", link, 'header')
                await sendMessage(self.logMessage, lmsg + msg, buttons.build_menu(2))
            if self.seed and not self.isClone:
                if self.isZip:
                    await clean_target(f"{self.dir}/{name}")
                elif self.newDir:
                    await clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                return
        if not self.isClone:
            await clean_download(self.dir)
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        async with queue_dict_lock:
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()
        await delete_links(self.message)

    async def onDownloadError(self, error, button=None):
        if not self.isClone:
            await clean_download(self.dir)
            if self.newDir:
                await clean_download(self.newDir)
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
            if self.uid in self.sameDir:
                self.sameDir.remove(self.uid)
        msg = f"{self.tag} your download has been stopped due to: {escape(error)}\n<b>Elapsed</b>: {get_readable_time(time() - self.startTime)}"
        msg += f"\n<b>Upload</b>: {self.mode}"
        await sendMessage(self.message, msg, button)
        if self.logMessage:
            await sendMessage(self.logMessage, msg, button)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            await DbManger().remove_download(self.raw_url)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)

        async with queue_dict_lock:
            if self.uid in queued_dl:
                del queued_dl[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in queued_up:
                del queued_up[self.uid]
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)
        if self.queuedUp is not None:
            self.queuedUp.set()
        await start_from_queued()
        await delete_links(self.message)

    async def onUploadError(self, error):
        if not self.isClone:
            await clean_download(self.dir)
            if self.newDir:
                await clean_download(self.newDir)
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
            if self.uid in self.sameDir:
                self.sameDir.remove(self.uid)
        msg = f"{self.tag} {escape(error)}\n<b>Elapsed</b>: {get_readable_time(time() - self.startTime)}"
        msg += f"\n<b>Upload</b>: {self.mode}"
        await sendMessage(self.message, msg)
        if self.logMessage:
            await sendMessage(self.logMessage, msg)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            await DbManger().remove_download(self.raw_url)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)
        async with queue_dict_lock:
            if self.uid in queued_dl:
                del queued_dl[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in queued_up:
                del queued_up[self.uid]
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        if self.queuedUp is not None:
            self.queuedUp.set()
        await start_from_queued()
        await delete_links(self.message)