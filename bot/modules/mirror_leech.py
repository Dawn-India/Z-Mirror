from base64 import b64encode
from html import escape
from os import path
from re import match, split
from threading import Thread
from time import sleep, time

from requests import request
from telegram.ext import CommandHandler

from bot import (DATABASE_URL, DOWNLOAD_DIR, IS_USER_SESSION, LOGGER,
                 categories, config_dict, dispatcher)
from bot.helper.ext_utils.bot_utils import (check_user_tasks, get_content_type,
                                            is_gdrive_link, is_magnet,
                                            is_mega_link, is_Sharerlink,
                                            is_url)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.z_utils import extract_link
from bot.helper.ext_utils.rate_limiter import ratelimiter
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.clonner import start_clone
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.download_utils.gd_downloader import add_gd_download
from bot.helper.mirror_utils.download_utils.mega_downloader import add_mega_download
from bot.helper.mirror_utils.download_utils.qbit_downloader import add_qb_torrent
from bot.helper.mirror_utils.download_utils.telegram_downloader import TelegramDownloadHelper
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      delete_links,
                                                      editMessage, forcesub,
                                                      isAdmin, message_filter,
                                                      open_category_btns,
                                                      sendDmMessage,
                                                      sendLogMessage,
                                                      sendMessage)
from bot.modules.listener import MirrorLeechListener


def _mirror_leech(bot, message, isZip=False, extract=False, isQbit=False, isLeech=False, sameDir={}, isClone=False):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)
    index = 1
    ratio = None
    seed_time = None
    select = False
    seed = False
    multi = 0
    link = ''
    folder_name = ''
    tfile = False
    raw_url = None
    drive_id = None
    index_link = None
    if len(message_args) > 1:
        args = mesg[0].split(maxsplit=5)
        for x in args:
            x = x.strip()
            if x in ['|', 'pswd:']:
                break
            elif x == 's':
               select = True
               index += 1
            elif x == 'd':
                seed = True
                index += 1
            elif x.startswith('d:'):
                seed = True
                index += 1
                dargs = x.split(':')
                ratio = dargs[1] or None
                if len(dargs) == 3:
                    seed_time = dargs[2] or None
            elif x.isdigit():
                multi = int(x)
                mi = index
            elif x.startswith('m:'):
                marg = x.split('m:', 1)
                if len(marg) > 1:
                    folder_name = f"/{marg[-1]}"
                    if not sameDir:
                        sameDir = set()
                    sameDir.add(message.message_id)
            elif x.startswith('id:'):
                index += 1
                drive_id = x.split(':', 1)
                if len(drive_id) > 1:
                    drive_id = drive_id[1]
                    if is_gdrive_link(drive_id):
                        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)
            elif x.startswith('index:'):
                index += 1
                index_link = x.split(':', 1)
                if len(index_link) > 1 and is_url(index_link[1]):
                    index_link = index_link[1]
        if multi == 0:
            message_args = mesg[0].split(maxsplit=index)
            if len(message_args) > index:
                link = message_args[index].strip()
                if link.startswith(("|", "pswd:")):
                    link = ''
        if len(folder_name) > 0:
            seed = False
            ratio = None
            seed_time = None

    def __run_multi():
        if multi <= 1:
            return
        sleep(4)
        nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id,
                                               'message_id': message.reply_to_message.message_id + 1})
        msg = message.text.split(maxsplit=mi+1)
        msg[mi] = f"{multi - 1}"
        nextmsg = sendMessage(" ".join(msg), bot, nextmsg)
        if len(folder_name) > 0:
            sameDir.add(nextmsg.message_id)
        nextmsg.from_user.id = message.from_user.id
        sleep(4)
        Thread(target=_mirror_leech, args=(bot, nextmsg, isZip, extract, isQbit, isLeech, sameDir, isClone)).start()

    dl_path = f'{DOWNLOAD_DIR}{message.message_id}{folder_name}'

    name = mesg[0].split('|', maxsplit=1)
    if len(name) > 1:
        name = '' if 'pswd:' in name[0] else name[1].split('pswd:')[0].strip()
    else:
        name = ''

    pswd = mesg[0].split(' pswd: ')
    pswd = pswd[1] if len(pswd) > 1 else None

    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)

    if link != '':
        link = split(r"pswd:|\|", link)[0]
        link = link.strip()

    reply_to = message.reply_to_message
    if reply_to:
        file_ = reply_to.document or reply_to.video or reply_to.audio or reply_to.photo or None
        if not reply_to.from_user.is_bot:
            if reply_to.from_user.username:
                tag = f"@{reply_to.from_user.username}"
            else:
                tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
        if len(link) == 0 or not is_url(link) and not is_magnet(link):
            if file_ is None:
                reply_text = reply_to.text.split(maxsplit=1)[0].strip()
                if is_url(reply_text) or is_magnet(reply_text):
                    link = reply_to.text.strip()
            elif isinstance(file_, list):
                link = file_[-1].get_file().file_path
            elif not isQbit and file_.mime_type != "application/x-bittorrent" and not isClone:
                if message.from_user.id in [1087968824, 136817688]:
                    message.from_user.id = anno_checker(message)
                    if not message.from_user.id:
                        return
                if not isAdmin(message):
                    if message_filter(bot, message, tag):
                        return
                    if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS']:
                        raw_url = file_.file_unique_id
                        exist = DbManger().check_download(raw_url)
                        if exist:
                            _msg = f'<b>Download is already added by {exist["tag"]}</b>\n\nCheck the download status in @{exist["botname"]}\n\n<b>Link</b>: <code>{exist["_id"]}</code>'
                            delete_links(bot, message)
                            return sendMessage(_msg, bot, message)
                    if forcesub(bot, message, tag):
                        return
                    if (maxtask:= config_dict['USER_MAX_TASKS']) and check_user_tasks(message.from_user.id, maxtask):
                        return sendMessage(f"Your tasks limit exceeded for {maxtask} tasks", bot, message)
                    if isLeech and config_dict['DISABLE_LEECH']:
                        delete_links(bot, message)
                        return sendMessage('Locked!', bot, message)
                    if not isLeech and not drive_id and len(categories) > 1:
                        drive_id, index_link = open_category_btns(message)
                    if not isLeech and not config_dict['GDRIVE_ID'] and not drive_id:
                        sendMessage('GDRIVE_ID not Provided!', bot, message)
                        return
                    if not isLeech and drive_id and not GoogleDriveHelper().getFolderData(drive_id):
                        return sendMessage("Google Drive id validation failed!!", bot, message)
                if (dmMode:=config_dict['DM_MODE']) and message.chat.type == message.chat.SUPERGROUP:
                    if isLeech and IS_USER_SESSION and not config_dict['DUMP_CHAT']:
                        return sendMessage('DM_MODE and User Session need DUMP_CHAT', bot, message)
                    dmMessage = sendDmMessage(bot, message, dmMode, isLeech)
                    if dmMessage == 'BotNotStarted':
                        return
                else:
                    dmMessage = None
                logMessage = sendLogMessage(bot, message, link, tag)
                listener = MirrorLeechListener(bot, message,
                                isZip, extract, isQbit, isLeech, isClone,
                                pswd, tag, select, seed, sameDir,
                                raw_url, drive_id, index_link, dmMessage, logMessage)
                Thread(target=TelegramDownloadHelper(listener).add_download, args=(message, f'{dl_path}/', name)).start()
                __run_multi()
                return
            else:
                tfile = True
                link = file_.get_file().file_path
    if isClone and not is_gdrive_link(link) and not is_Sharerlink(link) or (link.isdigit() and multi == 0):
        msg_ = "Send Gdrive link along with command or by replying to the link by command\n"
        msg_ += "\n<b>Multi links only by replying to first link:</b>\n<code>/cmd</code> 10(number of links)"
        return sendMessage(msg_, bot, message)
    if not is_url(link) and not is_magnet(link) or (link.isdigit() and multi == 0):
        help_msg = '''
<code>/{cmd}</code> link |newname pswd: xx(zip/unzip)

<b>By replying to link/file:</b>
<code>/{cmd}</code> |newname pswd: xx(zip/unzip)

<b>Multi links within same upload directory only by replying to first link/file:</b>
<code>/{cmd}</code> 10(number of links/files) m:folder_name
Number and m:folder_name should be always before |newname or pswd:

<b>Upload Custom Drive</b>
<code>/{cmd}</code> <b>id:</b><code>drive_folder_link</code> or <code>drive_id</code> <b>index:</b><code>https://anything.in/0:</code> link or by replying to file/link
drive_id must be folder id and index must be url else it will not accept
This options  should be always before |newname or pswd:

<b>Direct link authorization:</b>
<code>/{cmd}</code> link |newname pswd: xx(zip/unzip)
<b>username</b>
<b>password</b>

<b>Bittorrent selection:</b>
<code>/{cmd}</code> <b>s</b> link or by replying to file/link
This option should be always before |newname or pswd:

<b>Bittorrent seed</b>:
<code>/{cmd}</code> <b>d</b> link or by replying to file/link
To specify ratio and seed time add d:ratio:time. Ex: d:0.7:10 (ratio and time) or d:0.7 (only ratio) or d::10 (only time) where time in minutes.
This options  should be always before |newname or pswd:

<b>Multi links only by replying to first link/file:</b>
<code>/{cmd}</code> 10(number of links/files)
Number should be always before |newname or pswd:

<b>NOTES:</b>
1. When use cmd by reply don't add any option in link msg! always add them after cmd msg!
2. You can't add this those options <b>|newname, pswd: and authorization</b> randomly. They should be arranged like example above, rename then pswd. Those options should be after the link if link along with the cmd and after any other option
3. You can add this those options <b>d, s and multi</b> randomly. Ex: <code>/{cmd}</code> d:1:20 s 10 <b>or</b> <code>/{cmd}</code> s 10 d:0.5:100
4. Commands that start with <b>qb</b> are ONLY for torrents.
'''.format_map({'cmd': BotCommands.MirrorCommand[0]})
        delete_links(bot, message)
        sendMessage(help_msg, bot, message)
        return
    if message.from_user.id in [1087968824, 136817688]:
        message.from_user.id = anno_checker(message)
        if not message.from_user.id:
            return
    if not isAdmin(message):
        if message_filter(bot, message, tag):
            __run_multi()
            return
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS']:
            raw_url = extract_link(link, tfile)
            exist = DbManger().check_download(raw_url)
            if exist:
                _msg = f'<b>Download is already added by {exist["tag"]}</b>\n\nCheck the download status in @{exist["botname"]}\n\n<b>Link</b>: <code>{exist["_id"]}</code>'
                delete_links(bot, message)
                sendMessage(_msg, bot, message)
                __run_multi()
                return
        if forcesub(bot, message, tag):
            return
        if (maxtask:= config_dict['USER_MAX_TASKS']) and check_user_tasks(message.from_user.id, maxtask):
            return sendMessage(f"Your tasks limit exceeded for {maxtask} tasks", bot, message)
        if isLeech and config_dict['DISABLE_LEECH']:
            delete_links(bot, message)
            return sendMessage('Locked!', bot, message)
    if not isLeech and not drive_id and len(categories) > 1:
        drive_id, index_link = open_category_btns(message)
    if not isLeech and not config_dict['GDRIVE_ID'] and not drive_id:
        sendMessage('GDRIVE_ID not Provided!', bot, message)
        return
    if not isLeech and drive_id and not GoogleDriveHelper().getFolderData(drive_id):
        return sendMessage("Google Drive id validation failed!!", bot, message)
    if (dmMode:=config_dict['DM_MODE']) and message.chat.type == message.chat.SUPERGROUP:
        if isLeech and IS_USER_SESSION and not config_dict['DUMP_CHAT']:
            return sendMessage('DM_MODE and User Session need DUMP_CHAT', bot, message)
        dmMessage = sendDmMessage(bot, message, dmMode, isLeech)
        if dmMessage == 'BotNotStarted':
            return
    else:
        dmMessage = None
    logMessage = sendLogMessage(bot, message, link, tag)
    listener = MirrorLeechListener(bot, message,
                                isZip, extract, isQbit, isLeech, isClone,
                                pswd, tag, select, seed, sameDir,
                                raw_url, drive_id, index_link, dmMessage, logMessage)
    LOGGER.info(f"{link} added by: {message.from_user.id}")
    if not is_mega_link(link) and not isQbit and not is_magnet(link)     and not is_gdrive_link(link) and not link.endswith('.torrent'):
        content_type = get_content_type(link)
        if content_type is None or match(r'text/html|text/plain', content_type):
            _tempmsg = sendMessage(f"Processing: <code>{link}</code>", bot, message)
            try:
                link = direct_link_generator(link)
                LOGGER.info(f"Generated link: {link}")
                editMessage(f"Generated link: <code>{link}</code>", _tempmsg)
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith('ERROR:'):
                    delete_links(bot, message)
                    editMessage(escape(str(e)), _tempmsg)
                    __run_multi()
                    return
            _tempmsg.delete()
    elif isQbit and not is_magnet(link) and not isClone:
        if link.endswith('.torrent') or "https://api.telegram.org/file/" in link:
            content_type = None
        else:
            content_type = get_content_type(link)
        if content_type is None or match(r'application/x-bittorrent|application/octet-stream', content_type):
            try:
                resp = request('GET', link, timeout=10, headers = {'user-agent': 'Wget/1.12'})
                if resp.status_code != 200:
                    delete_links(bot, message)
                    sendMessage(f"{tag} ERROR: link got HTTP response: {resp.status_code}", bot, message)
                    __run_multi()
                    return
                file_name = str(time()).replace(".", "") + ".torrent"
                with open(file_name, "wb") as t:
                    t.write(resp.content)
                link = str(file_name)
            except Exception as e:
                error = str(e).replace('<', ' ').replace('>', ' ')
                if error.startswith('No connection adapters were found for'):
                    link = error.split("'")[1]
                else:
                    LOGGER.error(str(e))
                    delete_links(bot, message)
                    sendMessage(f"{tag} {error}", bot, message)
                    __run_multi()
                    return
        else:
            msg = "qBittorrent for torrents only. if you are trying to download torrent then report."
            sendMessage(msg, bot, message)
            __run_multi()
            return
    if is_gdrive_link(link):
        if not any([isZip, extract, isLeech, isClone]):
            gmsg = f"Use /{BotCommands.CloneCommand} to clone Google Drive file/folder\n\n"
            gmsg += f"Use /{BotCommands.ZipMirrorCommand[0]} to make zip of Google Drive folder\n\n"
            gmsg += f"Use /{BotCommands.UnzipMirrorCommand[0]} to extracts Google Drive archive folder/file"
            delete_links(bot, message)
            sendMessage(gmsg, bot, message)
        elif isClone:
            Thread(target=start_clone, args=(link, listener)).start()
        else:
            Thread(target=add_gd_download, args=(link, dl_path, listener, name)).start()
    elif is_mega_link(link):
        listener.ismega = sendMessage("<b>Mega link detected.\nThis might take a minute.</b>", bot, message)
        Thread(target=add_mega_download, args=(link, f'{dl_path}/', listener, name)).start()
    elif isQbit and (is_magnet(link) or path.exists(link)):
        Thread(target=add_qb_torrent, args=(link, dl_path, listener, ratio, seed_time)).start()
    else:
        mesg = message.text.split('\n')
        if len(mesg) > 1:
            ussr = mesg[1]
            pssw = mesg[2] if len(mesg) > 2 else ''
            auth = f"{ussr}:{pssw}"
            auth = "Basic " + b64encode(auth.encode()).decode('ascii')
        else:
            auth = ''
        Thread(target=add_aria2c_download, args=(link, dl_path, listener, name, auth, ratio, seed_time)).start()
    __run_multi()

@ratelimiter
def mirror(update, context):
    _mirror_leech(context.bot, update.message)

@ratelimiter
def mirror(update, context):
    _mirror_leech(context.bot, update.message)

@ratelimiter
def unzip_mirror(update, context):
    _mirror_leech(context.bot, update.message, extract=True)

@ratelimiter
def zip_mirror(update, context):
    _mirror_leech(context.bot, update.message, True)

@ratelimiter
def qb_mirror(update, context):
    _mirror_leech(context.bot, update.message, isQbit=True)

@ratelimiter
def qb_unzip_mirror(update, context):
    _mirror_leech(context.bot, update.message, extract=True, isQbit=True)

@ratelimiter
def qb_zip_mirror(update, context):
    _mirror_leech(context.bot, update.message, True, isQbit=True)

@ratelimiter
def leech(update, context):
    _mirror_leech(context.bot, update.message, isLeech=True)

@ratelimiter
def unzip_leech(update, context):
    _mirror_leech(context.bot, update.message, extract=True, isLeech=True)

@ratelimiter
def zip_leech(update, context):
    _mirror_leech(context.bot, update.message, True, isLeech=True)

@ratelimiter
def qb_leech(update, context):
    _mirror_leech(context.bot, update.message, isQbit=True, isLeech=True)

@ratelimiter
def qb_unzip_leech(update, context):
    _mirror_leech(context.bot, update.message, extract=True, isQbit=True, isLeech=True)

@ratelimiter
def qb_zip_leech(update, context):
    _mirror_leech(context.bot, update.message, True, isQbit=True, isLeech=True)

@ratelimiter
def cloneNode(update, context):
    _mirror_leech(context.bot, update.message, isClone=True)

mirror_handler = CommandHandler(BotCommands.MirrorCommand, mirror,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
unzip_mirror_handler = CommandHandler(BotCommands.UnzipMirrorCommand, unzip_mirror,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
zip_mirror_handler = CommandHandler(BotCommands.ZipMirrorCommand, zip_mirror,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
qb_mirror_handler = CommandHandler(BotCommands.QbMirrorCommand, qb_mirror,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
qb_unzip_mirror_handler = CommandHandler(BotCommands.QbUnzipMirrorCommand, qb_unzip_mirror,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
qb_zip_mirror_handler = CommandHandler(BotCommands.QbZipMirrorCommand, qb_zip_mirror,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
leech_handler = CommandHandler(BotCommands.LeechCommand, leech,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
unzip_leech_handler = CommandHandler(BotCommands.UnzipLeechCommand, unzip_leech,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
zip_leech_handler = CommandHandler(BotCommands.ZipLeechCommand, zip_leech,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
qb_leech_handler = CommandHandler(BotCommands.QbLeechCommand, qb_leech,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
qb_unzip_leech_handler = CommandHandler(BotCommands.QbUnzipLeechCommand, qb_unzip_leech,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
qb_zip_leech_handler = CommandHandler(BotCommands.QbZipLeechCommand, qb_zip_leech,
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, 
                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)

dispatcher.add_handler(mirror_handler)
dispatcher.add_handler(unzip_mirror_handler)
dispatcher.add_handler(zip_mirror_handler)
dispatcher.add_handler(qb_mirror_handler)
dispatcher.add_handler(qb_unzip_mirror_handler)
dispatcher.add_handler(qb_zip_mirror_handler)
dispatcher.add_handler(leech_handler)
dispatcher.add_handler(unzip_leech_handler)
dispatcher.add_handler(zip_leech_handler)
dispatcher.add_handler(qb_leech_handler)
dispatcher.add_handler(qb_unzip_leech_handler)
dispatcher.add_handler(qb_zip_leech_handler)
dispatcher.add_handler(clone_handler)
