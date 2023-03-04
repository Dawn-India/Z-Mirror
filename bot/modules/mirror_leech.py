from asyncio import sleep
from base64 import b64encode
from re import match as re_match
from re import split as re_split

from aiofiles.os import path as aiopath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import (DATABASE_URL, DOWNLOAD_DIR, IS_PREMIUM_USER, LOGGER, bot,
                 categories, config_dict)
from bot.helper.ext_utils.bot_utils import (check_user_tasks, get_content_type,
                                            is_gdrive_link, is_magnet,
                                            is_mega_link, is_share_link,
                                            is_url, new_task, sync_to_async)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.z_utils import extract_link
from bot.helper.listener import MirrorLeechListener
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

@new_task
async def _mirror_leech(client, message, isZip=False, extract=False, isQbit=False, isLeech=False, sameDir={}, isClone=False):
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
    raw_url = None
    drive_id = None
    index_link = None
    auth = ''

    if len(message_args) > 1:
        args = mesg[0].split(maxsplit=6)
        args.pop(0)
        for x in args:
            x = x.strip()
            if x == 's':
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
                    folder_name = f"/{marg[1]}"
                    if not sameDir:
                        sameDir = set()
                    sameDir.add(message.id)
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
            else:
                break
        if multi == 0:
            message_args = mesg[0].split(maxsplit=index)
            if len(message_args) > index:
                x = message_args[index].strip()
                if not x.startswith(('n:', 'pswd:')):
                    link = re_split(r' pswd: | n: ', x)[0].strip()
        if len(folder_name) > 0:
            seed = False
            ratio = None
            seed_time = None

    @new_task
    async def __run_multi():
        if multi <= 1:
            return
        await sleep(4)
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=message.reply_to_message_id + 1)
        msg = message.text.split(maxsplit=mi+1)
        msg[mi] = f"{multi - 1}"
        nextmsg = await sendMessage(nextmsg, " ".join(msg))
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=nextmsg.id)
        if len(folder_name) > 0:
            sameDir.add(nextmsg.id)
        nextmsg.from_user = message.from_user
        await sleep(4)
        _mirror_leech(client, nextmsg, isZip, extract, isQbit, isLeech, sameDir, isClone)

    path = f'{DOWNLOAD_DIR}{message.id}{folder_name}'

    name = mesg[0].split(' n: ', 1)
    name = name[1].split(' pswd: ')[0].strip() if len(name) > 1 else ''

    pswd = mesg[0].split(' pswd: ', 1)
    pswd = pswd[1].split(' n: ')[0] if len(pswd) > 1 else None
    if len(mesg) > 1 and mesg[1].startswith('Tag: '):
        tag, id_ = mesg[1].split('Tag: ')[1].split()
        message.from_user = await client.get_users(id_)
        try:
            await message.unpin()
        except:
            pass
    elif sender_chat:= message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    if reply_to := message.reply_to_message:
        file_ = reply_to.document or reply_to.photo or reply_to.video or reply_to.audio or \
                 reply_to.voice or reply_to.video_note or reply_to.sticker or reply_to.animation or None
        if sender_chat:= reply_to.sender_chat:
            tag = sender_chat.title
        elif not reply_to.from_user.is_bot:
            if username := reply_to.from_user.username:
                tag = f"@{username}"
            else:
                tag = reply_to.from_user.mention

        if len(link) == 0 or not is_url(link) and not is_magnet(link):
            if file_ is None:
                reply_text = reply_to.text.split('\n', 1)[0].strip()
                if is_url(reply_text) or is_magnet(reply_text):
                    link = reply_text
            elif reply_to.document and (file_.mime_type == 'application/x-bittorrent' or file_.file_name.endswith('.torrent')):
                link = await reply_to.download()
            elif not isClone:
                if not message.from_user:
                    message.from_user = await anno_checker(message)
                if not message.from_user:
                    return
                if not await isAdmin(message):
                    if await message_filter(message, tag):
                        return
                    if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS']:
                        raw_url = file_.file_unique_id
                        exist = await DbManger().check_download(raw_url)
                        if exist:
                            _msg = f'<b>Download is already added by {exist["tag"]}</b>\n\nCheck the download status in @{exist["botname"]}\n\n<b>Link</b>: <code>{exist["_id"]}</code>'
                            await delete_links(message)
                            return await sendMessage(message, _msg)
                    if await forcesub(message, tag):
                        return
                    if (maxtask:= config_dict['USER_MAX_TASKS']) and await check_user_tasks(message.from_user.id, maxtask):
                        return await sendMessage(message, f"Your tasks limit exceeded for {maxtask} tasks")
                    if isLeech and config_dict['DISABLE_LEECH']:
                        await delete_links(message)
                        return await sendMessage(message, 'Locked!')
                if not isLeech and not drive_id and len(categories) > 1:
                    drive_id, index_link = await open_category_btns(message)
                if not isLeech and not config_dict['GDRIVE_ID'] and not drive_id:
                    await sendMessage(message, 'GDRIVE_ID not Provided!')
                    return
                if not isLeech and drive_id and not await sync_to_async(GoogleDriveHelper().getFolderData, drive_id):
                    return await sendMessage(message, "Google Drive id validation failed!!")
                if (dmMode:=config_dict['DM_MODE']) and message.chat.type == message.chat.type.SUPERGROUP:
                    if isLeech and IS_PREMIUM_USER and not config_dict['DUMP_CHAT']:
                        return await sendMessage(message, 'DM_MODE and User Session need DUMP_CHAT')
                    dmMessage = await sendDmMessage(message, dmMode, isLeech)
                    if dmMessage == 'BotNotStarted':
                        return
                else:
                    dmMessage = None
                logMessage = await sendLogMessage(message, link, tag)
                listener = MirrorLeechListener(message,
                                isZip, extract, isQbit, isLeech, isClone,
                                pswd, tag, select, seed, sameDir,
                                raw_url, drive_id, index_link, dmMessage, logMessage)
                __run_multi()
                await TelegramDownloadHelper(listener).add_download(reply_to, f'{path}/', name)
                return

    if isClone and not is_gdrive_link(link) and not is_share_link(link) and is_mega_link(link) or (link.isdigit() and multi == 0):
        msg_ = "Send Gdrive link along with command or by replying to the link by command\n"
        msg_ += "\n<b>Multi links only by replying to first link:</b>\n<code>/cmd</code> 10(number of links)"
        return await sendMessage(message, msg_)

    if not is_url(link) and not is_magnet(link) and not await aiopath.exists(link) or (link.isdigit() and multi == 0):
        help_msg = '''
<code>/{cmd}</code> link n: newname pswd: xx(zip/unzip)

<b>By replying to link/file:</b>
<code>/{cmd}</code> n: newname pswd: xx(zip/unzip)

<b>Multi links within same upload directory only by replying to first link/file:</b>
<code>/{cmd}</code> 10(number of links/files) m:folder_name
Number and m:folder_name should be always before n: or pswd:

<b>Upload Custom Drive</b>
<code>/{cmd}</code> <b>id:</b><code>drive_folder_link</code> or <code>drive_id</code> <b>index:</b><code>https://anything.in/0:</code> link or by replying to file/link
drive_id must be folder id and index must be url else it will not accept
This options  should be always before n: or pswd:

<b>Direct link authorization:</b>
<code>/{cmd}</code> link n: newname pswd: xx(zip/unzip)
<b>username</b>
<b>password</b>

<b>Bittorrent selection:</b>
<code>/{cmd}</code> <b>s</b> link or by replying to file/link
This option should be always before n: or pswd:

<b>Bittorrent seed</b>:
<code>/{cmd}</code> <b>d</b> link or by replying to file/link
To specify ratio and seed time add d:ratio:time. Ex: d:0.7:10 (ratio and time) or d:0.7 (only ratio) or d::10 (only time) where time in minutes.
This options  should be always before n: or pswd:

<b>Multi links only by replying to first link/file:</b>
<code>/{cmd}</code> 10(number of links/files)
Number should be always before |newname or pswd:

<b>NOTES:</b>
1. When use cmd by reply don't add any option in link msg! Always add them after cmd msg!
2. Options (<b>n: and pswd:</b>) should be added randomly after the link if link along with the cmd and after any other option
3. Options (<b>d, s, m: and multi</b>) should be added randomly before the link and before any other option.
4. Commands that start with <b>qb</b> are ONLY for torrents.
'''.format_map({'cmd': BotCommands.MirrorCommand[0]})
        await sendMessage(message, help_msg)
        await delete_links(message)
        return
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        return
    if not await isAdmin(message):
        if await message_filter(message, tag):
            return
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS']:
            raw_url = await extract_link(link)
            exist = await DbManger().check_download(raw_url)
            if exist:
                _msg = f'<b>Download is already added by {exist["tag"]}</b>\n\nCheck the download status in @{exist["botname"]}\n\n<b>Link</b>: <code>{exist["_id"]}</code>'
                await delete_links(message)
                return await sendMessage(message, _msg)
        if await forcesub(message, tag):
            return
        if (maxtask:= config_dict['USER_MAX_TASKS']) and await check_user_tasks(message.from_user.id, maxtask):
            return await sendMessage(message, f"Your tasks limit exceeded for {maxtask} tasks")
        if isLeech and config_dict['DISABLE_LEECH']:
            await delete_links(message)
            return await sendMessage(message, 'Locked!')
    if not isLeech and not drive_id and len(categories) > 1:
        drive_id, index_link = await open_category_btns(message)
    if not isLeech and not config_dict['GDRIVE_ID'] and not drive_id:
        await sendMessage(message, 'GDRIVE_ID not Provided!')
        return
    if not isLeech and drive_id and not await sync_to_async(GoogleDriveHelper().getFolderData, drive_id):
        return await sendMessage(message, "Google Drive id validation failed!!")
    if (dmMode:=config_dict['DM_MODE']) and message.chat.type == message.chat.type.SUPERGROUP:
        if isLeech and IS_PREMIUM_USER and not config_dict['DUMP_CHAT']:
            return await sendMessage(message, 'DM_MODE and User Session need DUMP_CHAT')
        dmMessage = await sendDmMessage(message, dmMode, isLeech)
        if dmMessage == 'BotNotStarted':
            return
    else:
        dmMessage = None
    logMessage = await sendLogMessage(message, link, tag)

    LOGGER.info(link)

    if not is_mega_link(link) and not isQbit and not is_magnet(link) \
       and not is_gdrive_link(link) and not link.endswith('.torrent'):
        content_type = await sync_to_async(get_content_type, link)
        if content_type is None or re_match(r'text/html|text/plain', content_type):
            process_msg = await sendMessage(message, f"Processing: <code>{link}</code>")
            try:
                link = await sync_to_async(direct_link_generator, link)
                LOGGER.info(f"Generated link: {link}")
                await editMessage(process_msg, f"Generated link: <code>{link}</code>")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                if str(e).startswith('ERROR:'):
                    await editMessage(process_msg, str(e))
                    __run_multi()
                    return
            await process_msg.delete()
    __run_multi()

    listener = MirrorLeechListener(message,
                                isZip, extract, isQbit, isLeech, isClone,
                                pswd, tag, select, seed, sameDir,
                                raw_url, drive_id, index_link, dmMessage, logMessage)

    if is_gdrive_link(link):
        if not any([isZip, extract, isLeech, isClone]):
            gmsg = f"Use /{BotCommands.CloneCommand} to clone Google Drive file/folder\n\n"
            gmsg += f"Use /{BotCommands.ZipMirrorCommand[0]} to make zip of Google Drive folder\n\n"
            gmsg += f"Use /{BotCommands.UnzipMirrorCommand[0]} to extracts Google Drive archive folder/file"
            await delete_links(message)
            await sendMessage(message, gmsg)
        elif isClone:
            await start_clone(link, listener)
        else:
            await add_gd_download(link, path, listener, name)
    elif is_mega_link(link):
        listener.ismega = await sendMessage(message, "<b>Mega link detected.\nThis might take a minute.</b>")
        await add_mega_download(link, f'{path}/', listener, name)
    elif isQbit:
        await add_qb_torrent(link, path, listener, ratio, seed_time)
    else:
        if len(mesg) > 1 and not mesg[1].startswith('Tag:'):
            ussr = mesg[1]
            pssw = mesg[2] if len(mesg) > 2 else ''
            auth = f"{ussr}:{pssw}"
            auth = f"authorization: Basic {b64encode(auth.encode()).decode('ascii')}"
        await add_aria2c_download(link, path, listener, name, auth, ratio, seed_time)

async def mirror(client, message):
    _mirror_leech(client, message)

async def unzip_mirror(client, message):
    _mirror_leech(client, message, extract=True)

async def zip_mirror(client, message):
    _mirror_leech(client, message, True)

async def qb_mirror(client, message):
    _mirror_leech(client, message, isQbit=True)

async def qb_unzip_mirror(client, message):
    _mirror_leech(client, message, extract=True, isQbit=True)

async def qb_zip_mirror(client, message):
    _mirror_leech(client, message, True, isQbit=True)

async def leech(client, message):
    _mirror_leech(client, message, isLeech=True)

async def unzip_leech(client, message):
    _mirror_leech(client, message, extract=True, isLeech=True)

async def zip_leech(client, message):
    _mirror_leech(client, message, True, isLeech=True)

async def qb_leech(client, message):
    _mirror_leech(client, message, isQbit=True, isLeech=True)

async def qb_unzip_leech(client, message):
    _mirror_leech(client, message, extract=True, isQbit=True, isLeech=True)

async def qb_zip_leech(client, message):
    _mirror_leech(client, message, True, isQbit=True, isLeech=True)

async def cloneNode(client, message):
    _mirror_leech(client, message, isClone=True)

bot.add_handler(MessageHandler(mirror, filters=command(BotCommands.MirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(unzip_mirror, filters=command(BotCommands.UnzipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(zip_mirror, filters=command(BotCommands.ZipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_mirror, filters=command(BotCommands.QbMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_unzip_mirror, filters=command(BotCommands.QbUnzipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_zip_mirror, filters=command(BotCommands.QbZipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(leech, filters=command(BotCommands.LeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(unzip_leech, filters=command(BotCommands.UnzipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(zip_leech, filters=command(BotCommands.ZipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_leech, filters=command(BotCommands.QbLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_unzip_leech, filters=command(BotCommands.QbUnzipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_zip_leech, filters=command(BotCommands.QbZipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(cloneNode, filters=command(BotCommands.CloneCommand) & CustomFilters.authorized))