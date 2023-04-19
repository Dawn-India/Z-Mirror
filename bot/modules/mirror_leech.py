from asyncio import sleep
from base64 import b64encode
from re import match as re_match, split as re_split

from aiofiles.os import path as aiopath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import IS_PREMIUM_USER, LOGGER, bot, categories, config_dict
from bot.helper.ext_utils.bot_utils import (get_content_type, is_gdrive_link,
                                            is_magnet, is_mega_link,
                                            is_rclone_path, is_url, new_task,
                                            sync_to_async)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.help_messages import MIRROR_HELP_MESSAGE, CLONE_HELP_MESSAGE
from bot.helper.z_utils import none_admin_utils, stop_duplicate_tasks
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.download_utils.gd_download import add_gd_download
from bot.helper.mirror_utils.download_utils.mega_download import add_mega_download
from bot.helper.mirror_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.mirror_utils.download_utils.rclone_download import add_rclone_download
from bot.helper.mirror_utils.download_utils.telegram_download import TelegramDownloadHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      delete_links,
                                                      editMessage, isAdmin,
                                                      open_category_btns,
                                                      sendDmMessage,
                                                      sendLogMessage,
                                                      sendMessage)


@new_task
async def _mirror_leech(client, message, isZip=False, extract=False, isQbit=False, isLeech=False, sameDir={}):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)
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
        index = 1
        args = mesg[0].split(maxsplit=5)
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
            else:
                break
        if multi == 0:
            message_args = mesg[0].split(maxsplit=index)
            if len(message_args) > index:
                x = message_args[index].strip()
                if not x.startswith(('n:', 'pswd:', 'up:', 'rcf:', 'id:', 'index:')):
                    link = re_split(r' pswd: | n: | up: | rcf: | id: | index: ', x)[0].strip()

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
        if message.sender_chat:
            nextmsg.sender_chat = message.sender_chat
        await sleep(4)
        _mirror_leech(client, nextmsg, isZip, extract,
                      isQbit, isLeech, sameDir)

    path = f'{config_dict["DOWNLOAD_DIR"]}{message.id}{folder_name}'

    name = mesg[0].split(' n: ', 1)
    name = re_split(' pswd: | rcf: | up: | id: | index: ', name[1])[
        0].strip() if len(name) > 1 else ''

    pswd = mesg[0].split(' pswd: ', 1)
    pswd = re_split(' n: | rcf: | up: | id: | index: ', pswd[1])[
        0] if len(pswd) > 1 else None

    rcf = mesg[0].split(' rcf: ', 1)
    rcf = re_split(' n: | pswd: | up: | id: | index: ', rcf[1])[
        0].strip() if len(rcf) > 1 else None

    up = mesg[0].split(' up: ', 1)
    up = re_split(' n: | pswd: | rcf: | id: | index: ', up[1])[
        0].strip() if len(up) > 1 else None

    drive_id = mesg[0].split(' id: ', 1)
    drive_id = re_split(' rcf: | index: | up: | n: | pswd: ', drive_id[1])[
        0].strip() if len(drive_id) > 1 else None
    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    index_link = mesg[0].split(' index: ', 1)
    index_link = re_split(' rcf: | id: | up: | n: | pswd: ', index_link[1])[
        0].strip() if len(index_link) > 1 else None
    if index_link and not index_link.startswith(('http://', 'https://')):
        index_link = None
    if index_link and not index_link.endswith('/'):
        index_link += '/'

    if len(mesg) > 1 and mesg[1].startswith('Tag: '):
        tag, id_ = mesg[1].split('Tag: ')[1].split()
        message.from_user = await client.get_users(id_)
        try:
            await message.unpin()
        except:
            pass
    elif sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    file_ = None
    if reply_to := message.reply_to_message:
        file_ = reply_to.document or reply_to.photo or reply_to.video or reply_to.audio or \
            reply_to.voice or reply_to.video_note or reply_to.sticker or reply_to.animation or None
        if sender_chat := reply_to.sender_chat:
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
                file_ = None

    if not is_url(link) and not is_magnet(link) and not await aiopath.exists(link) and not is_rclone_path(link) and file_ is None:
        await sendMessage(message, MIRROR_HELP_MESSAGE.format_map({'cmd': message.command[0]}))
        await delete_links(message)
        return
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        await delete_links(message)
        return
    if not await isAdmin(message):
        raw_url = await stop_duplicate_tasks(message, link, file_)
        if raw_url == 'duplicate_tasks':
            await delete_links(message)
            return
        if await none_admin_utils(message, tag, isLeech):
            return
    if (dmMode := config_dict['DM_MODE']) and message.chat.type == message.chat.type.SUPERGROUP:
        if isLeech and IS_PREMIUM_USER and not config_dict['DUMP_CHAT']:
            await delete_links(message)
            return await sendMessage(message, 'DM_MODE and User Session need DUMP_CHAT')
        dmMessage = await sendDmMessage(message, dmMode, isLeech)
        if dmMessage == 'BotNotStarted':
            await delete_links(message)
            return
    else:
        dmMessage = None
    logMessage = await sendLogMessage(message, link, tag)

    if link:
        LOGGER.info(link)

    if not is_mega_link(link) and not isQbit and not is_magnet(link) and not is_rclone_path(link) \
       and not is_gdrive_link(link) and not link.endswith('.torrent') and file_ is None:
        content_type = await sync_to_async(get_content_type, link)
        if content_type is None or re_match(r'text/html|text/plain', content_type):
            process_msg = await sendMessage(message, f"Processing: <code>{link}</code>")
            try:
                link = await sync_to_async(direct_link_generator, link)
                LOGGER.info(f"Generated link: {link}")
                await editMessage(process_msg, f"Generated link: <code>{link}</code>")
            except DirectDownloadLinkException as e:
                LOGGER.info(str(e))
                await delete_links(message)
                if str(e).startswith('ERROR:'):
                    await editMessage(process_msg, str(e))
                    __run_multi()
                    return
            await process_msg.delete()
    __run_multi()

    if not isLeech:
        if config_dict['DEFAULT_UPLOAD'] == 'rc' and up is None or up == 'rc':
            up = config_dict['RCLONE_PATH']
        if up is None and config_dict['DEFAULT_UPLOAD'] == 'gd':
            up = 'gd'
            if not drive_id and len(categories) > 1:
                drive_id, index_link = await open_category_btns(message)
            if drive_id and not await sync_to_async(GoogleDriveHelper().getFolderData, drive_id):
                return await sendMessage(message, "Google Drive id validation failed!!")
        if up == 'gd' and not config_dict['GDRIVE_ID'] and not drive_id:
            await sendMessage(message, 'GDRIVE_ID not Provided!')
            return
        elif not up:
            await sendMessage(message, 'No Rclone Destination!')
            return
        elif up not in ['rcl', 'gd']:
            if up.startswith('mrcc:'):
                config_path = f'rclone/{message.from_user.id}.conf'
            else:
                config_path = 'rclone.conf'
            if not await aiopath.exists(config_path):
                await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
                return

    if link == 'rcl':
        link = await RcloneList(client, message).get_rclone_path('rcd')
        if not is_rclone_path(link):
            await sendMessage(message, link)
            return
    if up == 'rcl' and not isLeech:
        up = await RcloneList(client, message).get_rclone_path('rcu')
        if not is_rclone_path(up):
            await sendMessage(message, up)
            return

    listener = MirrorLeechListener(message, isZip, extract, isQbit,
                                   isLeech, pswd, tag, select,
                                   seed, sameDir, rcf, up, False, raw_url,
                                   drive_id, index_link, dmMessage, logMessage)

    if file_ is not None:
        await TelegramDownloadHelper(listener).add_download(reply_to, f'{path}/', name)
    elif is_rclone_path(link):
        if link.startswith('mrcc:'):
            link = link.split('mrcc:', 1)[1]
            config_path = f'rclone/{message.from_user.id}.conf'
        else:
            config_path = 'rclone.conf'
        if not await aiopath.exists(config_path):
            await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
            return
        await add_rclone_download(link, config_path, f'{path}/', name, listener)
    elif is_gdrive_link(link):
        if not any([isZip, extract, isLeech]):
            gmsg = f"Use /{BotCommands.CloneCommand} to clone Google Drive file/folder\n\n"
            gmsg += f"Use /{BotCommands.ZipMirrorCommand[0]} to make zip of Google Drive folder\n\n"
            gmsg += f"Use /{BotCommands.UnzipMirrorCommand[0]} to extracts Google Drive archive folder/file"
            await delete_links(message)
            await sendMessage(message, gmsg)
        else:
            await add_gd_download(link, path, listener, name)
    elif is_mega_link(link):
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


bot.add_handler(MessageHandler(mirror, filters=command(
    BotCommands.MirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(unzip_mirror, filters=command(
    BotCommands.UnzipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(zip_mirror, filters=command(
    BotCommands.ZipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_mirror, filters=command(
    BotCommands.QbMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_unzip_mirror, filters=command(
    BotCommands.QbUnzipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_zip_mirror, filters=command(
    BotCommands.QbZipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(leech, filters=command(
    BotCommands.LeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(unzip_leech, filters=command(
    BotCommands.UnzipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(zip_leech, filters=command(
    BotCommands.ZipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_leech, filters=command(
    BotCommands.QbLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_unzip_leech, filters=command(
    BotCommands.QbUnzipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_zip_leech, filters=command(
    BotCommands.QbZipLeechCommand) & CustomFilters.authorized))
