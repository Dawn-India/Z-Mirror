from html import escape
from os import listdir, makedirs, path, remove, rename, walk
from re import search
from shutil import move
from subprocess import Popen
from time import sleep, time

from requests import utils as rutils

from bot import (bot, DATABASE_URL, DOWNLOAD_DIR, LOGGER, MAX_SPLIT_SIZE,
                 SHORTENERES, Interval, aria2, config_dict, download_dict,
                 download_dict_lock, non_queued_dl, non_queued_up,
                 queue_dict_lock, queued_dl, queued_up, status_reply_dict_lock,
                 user_data)
from bot.helper.ext_utils.bot_utils import extra_btns, get_readable_time
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive
from bot.helper.ext_utils.fs_utils import (clean_download, clean_target,
                                           get_base_name, get_path_size,
                                           split_file)
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
    def __init__(self, bot, message, isZip=False, extract=False, isQbit=False,
                isLeech=False, isClone=False, pswd=None, tag=None, select=False,
                seed=False, sameDir=None, raw_url=None,
                drive_id=None, index_link=None, dmMessage=None, logMessage=None):
        if not sameDir:
            sameDir = {}
        self.bot = bot
        self.message = message
        self.uid = message.message_id
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
        self.isPrivate = message.chat.type in ['private', 'group']
        self.suproc = None
        self.raw_url = raw_url
        self.drive_id = drive_id
        self.index_link = index_link
        self.dmMessage = dmMessage
        self.logMessage = logMessage
        self.queuedUp = False
        self.sameDir = sameDir
        self.startTime = time()
        self.__setMode()

    def clean(self):
        try:
            with status_reply_dict_lock:
                Interval[0].cancel()
                Interval.clear()
            aria2.purge()
            delete_all_messages()
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


    def onDownloadStart(self):
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            DbManger().add_download_url(self.raw_url, self.tag)
        if not self.isPrivate and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)

    def onDownloadComplete(self):
        with download_dict_lock:
            if len(self.sameDir) > 1:
                self.sameDir.remove(self.uid)
                folder_name = listdir(self.dir)[-1]
                des_path = f"{DOWNLOAD_DIR}{list(self.sameDir)[0]}/{folder_name}"
                makedirs(des_path, exist_ok=True)
                for subdir in listdir(f"{self.dir}/{folder_name}"):
                    sub_path = f"{self.dir}/{folder_name}/{subdir}"
                    if subdir in listdir(des_path):
                        sub_path = rename(sub_path, f"{self.dir}/{folder_name}/1-{subdir}")
                    move(sub_path, des_path)
                del download_dict[self.uid]
                return
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
        LOGGER.info(f"Download completed: {name}")
        if name == "None" or self.isQbit or not path.exists(f"{self.dir}/{name}"):
            name = listdir(self.dir)[-1]
        m_path = f"{self.dir}/{name}"
        size = get_path_size(m_path)
        with queue_dict_lock:
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
        start_from_queued()
        user_dict = user_data.get(self.message.from_user.id, {})
        if self.isZip:
            if self.seed and self.isLeech:
                self.newDir = f"{self.dir}10000"
                path_ = f"{self.newDir}/{name}.zip"
            else:
                path_ = f"{m_path}.zip"
            with download_dict_lock:
                download_dict[self.uid] = ZipStatus(name, size, gid, self)
            LEECH_SPLIT_SIZE = user_dict.get('split_size', False) or config_dict['LEECH_SPLIT_SIZE']
            if self.pswd:
                if self.isLeech and int(size) > LEECH_SPLIT_SIZE:
                    LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path_}.0*')
                    self.suproc = Popen(["7z", f"-v{LEECH_SPLIT_SIZE}b", "a", "-mx=0", f"-p{self.pswd}", path_, m_path])
                else:
                    LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path_}')
                    self.suproc = Popen(["7z", "a", "-mx=0", f"-p{self.pswd}", path_, m_path])
            elif self.isLeech and int(size) > LEECH_SPLIT_SIZE:
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path_}.0*')
                self.suproc = Popen(["7z", f"-v{LEECH_SPLIT_SIZE}b", "a", "-mx=0", path_, m_path])
            else:
                LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path_}')
                self.suproc = Popen(["7z", "a", "-mx=0", path_, m_path])
            self.suproc.wait()
            if self.suproc.returncode == -9:
                return
            elif not self.seed:
                clean_target(m_path)
        elif self.extract:
            try:
                if path.isfile(m_path):
                    path_ = get_base_name(m_path)
                LOGGER.info(f"Extracting: {name}")
                with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(name, size, gid, self)
                if path.isdir(m_path):
                    if self.seed:
                        self.newDir = f"{self.dir}10000"
                        path_ = f"{self.newDir}/{name}"
                    else:
                        path_ = m_path
                    for dirpath, _, files in walk(m_path, topdown=False):
                        for file_ in files:
                            if search('\.part0*1\.rar$|\.7z\.0*1$|\.zip\.0*1$|\.zip$|\.7z$|^.(?!.*\.part\d+\.rar)(?=.*\.rar$)', file_):
                                f_path = path.join(dirpath, file_)
                                t_path = dirpath.replace(self.dir, self.newDir) if self.seed else dirpath
                                if self.pswd:
                                    self.suproc = Popen(["7z", "x", f"-p{self.pswd}", f_path, f"-o{t_path}", "-aot"])
                                else:
                                    self.suproc = Popen(["7z", "x", f_path, f"-o{t_path}", "-aot"])
                                self.suproc.wait()
                                if self.suproc.returncode == -9:
                                    return
                                elif self.suproc.returncode != 0:
                                    LOGGER.error('Unable to extract archive splits!')
                        if not self.seed and self.suproc and self.suproc.returncode == 0:
                            for file_ in files:
                                if search('\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$|\.zip$|\.rar$|\.7z$', file_):
                                    del_path = path.join(dirpath, file_)
                                    try:
                                        remove(del_path)
                                    except:
                                        return
                else:
                    if self.seed and self.isLeech:
                        self.newDir = f"{self.dir}10000"
                        path_ = path_.replace(self.dir, self.newDir)
                    if self.pswd:
                        self.suproc = Popen(["7z", "x", f"-p{self.pswd}", m_path, f"-o{path_}", "-aot"])
                    else:
                        self.suproc = Popen(["7z", "x", m_path, f"-o{path_}", "-aot"])
                    self.suproc.wait()
                    if self.suproc.returncode == -9:
                        return
                    elif self.suproc.returncode == 0:
                        LOGGER.info(f"Extracted Path: {path_}")
                        if not self.seed:
                            try:
                                remove(m_path)
                            except:
                                return
                    else:
                        LOGGER.error('Unable to extract archive! Uploading anyway')
                        self.newDir = ""
                        path_ = m_path
            except NotSupportedExtractionArchive:
                LOGGER.info("Not any valid archive, uploading file as it is.")
                self.newDir = ""
                path_ = m_path
        else:
            path_ = m_path
        up_dir, up_name = path_.rsplit('/', 1)
        size = get_path_size(up_dir)
        if self.isLeech:
            m_size = []
            o_files = []
            if not self.isZip:
                checked = False
                LEECH_SPLIT_SIZE = user_dict.get('split_size', False) or config_dict['LEECH_SPLIT_SIZE']
                for dirpath, subdir, files in walk(up_dir, topdown=False):
                    for file_ in files:
                        f_path = path.join(dirpath, file_)
                        f_size = path.getsize(f_path)
                        if f_size > LEECH_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(up_name, size, gid, self)
                                LOGGER.info(f"Splitting: {up_name}")
                            res = split_file(f_path, f_size, file_, dirpath, LEECH_SPLIT_SIZE, self)
                            if not res:
                                return
                            if res == "errored":
                                if f_size <= MAX_SPLIT_SIZE:
                                    continue
                                try:
                                    remove(f_path)
                                except:
                                    return
                            elif not self.seed or self.newDir:
                                try:
                                    remove(f_path)
                                except:
                                    return
                            else:
                                m_size.append(f_size)
                                o_files.append(file_)
        up_limit = config_dict['QUEUE_UPLOAD']
        all_limit = config_dict['QUEUE_ALL']
        added_to_queue = False
        with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not up_limit or up >= up_limit)) or (up_limit and up >= up_limit):
                added_to_queue = True
                LOGGER.info(f"Added to Queue/Upload: {name}")
                queued_up[self.uid] = [self]
        if added_to_queue:
            with download_dict_lock:
                download_dict[self.uid] = QueueStatus(name, size, gid, self, 'Up')
                self.queuedUp = True
            while self.queuedUp:
                sleep(1)
            with download_dict_lock:
                if self.uid not in download_dict.keys():
                    return
            LOGGER.info(f'Start from Queued/Upload: {name}')
        with queue_dict_lock:
            non_queued_up.add(self.uid)

        if self.isLeech:
            size = get_path_size(up_dir)
            for s in m_size:
                size = size - s
            LOGGER.info(f"Leech Name: {up_name}")
            tg = TgUploader(up_name, up_dir, size, self)
            tg_upload_status = TgUploadStatus(tg, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = tg_upload_status
            update_all_messages()
            tg.upload(o_files, m_size)
        else:
            up_path = f'{up_dir}/{up_name}'
            size = get_path_size(up_path)
            LOGGER.info(f"Upload Name: {up_name}")
            drive = GoogleDriveHelper(up_name, up_dir, size, self)
            upload_status = UploadStatus(drive, size, gid, self)
            with download_dict_lock:
                download_dict[self.uid] = upload_status
            update_all_messages()
            drive.upload(up_name, self.drive_id or config_dict['GDRIVE_ID'])

    def onUploadComplete(self, link: str, size, files, folders, typ, name: str, drive_id=None):
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            DbManger().remove_download(self.raw_url)
        if not self.isPrivate and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            DbManger().rm_complete_task(self.message.link)
        if self.isLeech:
            if self.dmMessage:
                msg = f'Hey <b>{self.tag}</b>, \nYour job is done!'
            else:
                msg = f'<b>File Name</b>: <code>{escape(name)}</code>'
                msg += f'\n\n<b>#cc</b>: {self.tag}'
            msg += f'\n\n<b>Size</b>: {size}'
            msg += f'\n<b>Total Files</b>: {folders}'
            msg += f"\n<b>Elapsed</b>: {get_readable_time(time() - self.startTime)}"
            if typ != 0:
                msg += f'\n<b>Corrupted Files</b>: {typ}'
            msg += f"\n<b>Upload</b>: {self.mode}\n\n"
            msg_ = '<b>Files has been sent in your DM.</b>'
            if not files:
                if self.dmMessage:
                    buttons = ButtonMaker()
                    buttons.buildbutton("View in DM", f"{bot.link}")
                    button = buttons.build_menu(1)
                    sendMessage(msg + msg_, self.bot, self.message, button)
                else:
                    msg__ = '<b>Files has been sent in Leech Dump.</b>'
                    sendMessage(msg + msg__, self.bot, self.message)
                if self.logMessage:
                    if self.dmMessage:
                        msg += f'<b>File Name</b>: <code>{escape(name)}</code>'
                    sendMessage(msg, self.bot, self.logMessage)
            elif self.dmMessage and not config_dict['DUMP_CHAT']:
                sendMessage(msg, self.bot, self.dmMessage)
                buttons = ButtonMaker()
                buttons.buildbutton("View in DM", f"{bot.link}")
                button = buttons.build_menu(1)
                sendMessage(msg + msg_, self.bot, self.message, button)
                if self.logMessage:
                    if self.dmMessage:
                        msg += f'<b>File Name</b>: <code>{escape(name)}</code>'
                    sendMessage(msg, self.bot, self.logMessage)
            else:
                fmsg = ''
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    if len(fmsg.encode() + msg.encode()) > 4000:
                        if self.logMessage:
                            if self.dmMessage:
                                msg += f'<b>File Name</b>: <code>{escape(name)}</code>'
                            sendMessage(msg + fmsg, self.bot, self.logMessage)
                        buttons = ButtonMaker()
                        buttons = extra_btns(buttons)
                        if self.message.chat.type != 'private':
                            buttons.sbutton('Save This Message', 'save', 'footer')
                        sendMessage(msg + fmsg, self.bot, self.message, buttons.build_menu(2))
                        sleep(1)
                        fmsg = ''
                if fmsg != '':
                    if self.dmMessage:
                        _msg_ = f'\n<b>Files has been sent in your DM.</b>'
                    else:
                        _msg_ = f''
                    if self.logMessage:
                        if self.dmMessage:
                            __msg = f'<b>File Name</b>: <code>{escape(name)}</code>\n\n'
                        else:
                            __msg = f''
                        sendMessage(msg + __msg + fmsg, self.bot, self.logMessage)
                    buttons = ButtonMaker()
                    buttons = extra_btns(buttons)
                    if self.message.chat.type != 'private':
                        buttons.sbutton('Save This Message', 'save', 'footer')
                    sendMessage(msg + fmsg + _msg_, self.bot, self.message, buttons.build_menu(2))
            if self.seed:
                if self.newDir:
                    clean_target(self.newDir)
                with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                return
        else:
            if SHORTENERES:
                if self.dmMessage:
                    msg = f'Hey <b>{self.tag}</b>,\nYour job is done!'
                else:
                    msg = f'<b>Name</b>: <code>.{escape(name).replace(" ", "-").replace(".", ",")}</code>'
            else:
                if self.dmMessage:
                    msg = f'Hey <b>{self.tag}</b>,\nYour job is done!'
                else:
                    msg = f'<b>Name</b>: <code>{escape(name)}</code>'
                    msg += f'\n\n<b>#cc</b>: {self.tag}'
            msg += f'\n\n<b>Size</b>: {size}'
            msg += f'\n<b>Type</b>: {typ}'
            if typ == "Folder":
                msg += f' |<b>SubFolders</b>: {folders}'
                msg += f' |<b>Files</b>: {files}'
            msg += f'\n<b>Elapsed</b>: {get_readable_time(time() - self.message.date.timestamp())}'
            msg += f"\n<b>Upload</b>: {self.mode}"
            buttons = ButtonMaker()
            if not config_dict['DISABLE_DRIVE_LINK']:
                link = short_url(link)
                buttons.buildbutton("🔐 Drive Link", link)
            LOGGER.info(f'Done Uploading {name}')
            if INDEX_URL:= self.index_link or config_dict['INDEX_URL']:
                url_path = rutils.quote(f'{name}')
                if typ == "Folder":
                    share_url = short_url(f'{INDEX_URL}/{url_path}/')
                    buttons.buildbutton("📁 Index Link", share_url)
                else:
                    share_url = short_url(f'{INDEX_URL}/{url_path}')
                    buttons.buildbutton("🚀 Index Link", share_url)
                    if config_dict['VIEW_LINK']:
                        share_urls = short_url(f'{INDEX_URL}/{url_path}?a=view')
                        buttons.buildbutton("💻 View Link", share_urls)
            buttons = extra_btns(buttons)
            if self.dmMessage:
                sendMessage(msg, self.bot, self.dmMessage, buttons.build_menu(2))
                _msg = '\n\n<b>Links has been sent in your DM.</b>'
                buttons = ButtonMaker()
                buttons.buildbutton("View in DM", f"{bot.link}")
                button = buttons.build_menu(1)
                sendMessage(msg + _msg, self.bot, self.message, button)
            else:
                if self.message.chat.type != 'private':
                    buttons.sbutton("Save This Message", 'save', 'footer')
                sendMessage(msg, self.bot, self.message, buttons.build_menu(2))
            if self.logMessage:
                if self.dmMessage:
                    msg += f'\n\n<b>File Name</b>: <code>{escape(name)}</code>'
                if config_dict['DISABLE_DRIVE_LINK']:
                    link = short_url(link)
                    buttons.buildbutton("🔐 Drive Link", link, 'header')
                sendMessage(msg, self.bot, self.logMessage, buttons.build_menu(2))
            if not self.isClone and self.seed:
                if self.isZip:
                    clean_target(f"{self.dir}/{name}")
                elif self.newDir:
                    clean_target(self.newDir)
                with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                return
        self._clean_update()

    def onDownloadError(self, error, button=None):
        error = error.replace('<', ' ').replace('>', ' ')
        msg = f"{self.tag} your download has been stopped due to: {error}\n<b>Elapsed</b>: {get_readable_time(time() - self.startTime)}"
        self._clean_update(msg, button)

    def onUploadError(self, error):
        e_str = error.replace('<', '').replace('>', '')
        msg = f"{self.tag} {e_str}\n<b>Elapsed</b>: {get_readable_time(time() - self.startTime)}"
        self._clean_update(msg)

    def _clean_update(self, msg=None, button=None):
        if not self.isClone:
            clean_download(self.dir)
            if self.newDir:
                clean_download(self.newDir)
        with download_dict_lock:
            if self.uid in download_dict:
                del download_dict[self.uid]
            count = len(download_dict)
            if self.uid in self.sameDir:
                self.sameDir.remove(self.uid)
        if msg:
            msg += f"\n<b>Upload</b>: {self.mode}"
            sendMessage(msg, self.bot, self.message, button)
            if self.logMessage:
                sendMessage(msg, self.bot, self.logMessage, button)
        if count == 0:
            self.clean()
        else:
            update_all_messages()
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and self.raw_url:
            DbManger().remove_download(self.raw_url)
        if not self.isPrivate and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            DbManger().rm_complete_task(self.message.link)
        with queue_dict_lock:
            if self.uid in queued_dl:
                del queued_dl[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in queued_up:
                del queued_up[self.uid]
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        self.queuedUp = False
        start_from_queued()
        delete_links(self.bot, self.message)
