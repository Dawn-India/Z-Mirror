from asyncio import gather, sleep
from json import loads
from random import SystemRandom
from re import split as re_split
from string import ascii_letters, digits

from aiofiles.os import path as aiopath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import (LOGGER, bot, categories, config_dict, download_dict,
                 download_dict_lock)
from bot.helper.ext_utils.bot_utils import (cmd_exec, get_telegraph_list,
                                            is_gdrive_link, is_rclone_path,
                                            is_share_link, new_task,
                                            sync_to_async)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.help_messages import CLONE_HELP_MESSAGE
from bot.helper.ext_utils.task_manager import limit_checker
from bot.helper.z_utils import none_admin_utils, stop_duplicate_tasks
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      delete_links,
                                                      deleteMessage,
                                                      editMessage, isAdmin,
                                                      open_category_btns,
                                                      sendDmMessage,
                                                      sendLogMessage,
                                                      sendMessage,
                                                      sendStatusMessage)


async def rcloneNode(client, message, rcf, listener):
    if link == 'rcl':
        link = await RcloneList(client, message).get_rclone_path('rcd')
        if not is_rclone_path(link):
            await sendMessage(message, link)
            await delete_links(message)
            return

    if link.startswith('mrcc:'):
        link = link.split('mrcc:', 1)[1]
        config_path = f'rclone/{message.from_user.id}.conf'
    else:
        config_path = 'rclone.conf'

    if not await aiopath.exists(config_path):
        await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
        await delete_links(message)
        return

    if dst_path == 'rcl' or config_dict['RCLONE_PATH'] == 'rcl':
        dst_path = await RcloneList(client, message).get_rclone_path('rcu', config_path)
        if not is_rclone_path(dst_path):
            await sendMessage(message, dst_path)
            await delete_links(message)
            return

    dst_path = (dst_path or config_dict['RCLONE_PATH']).strip('/')
    if dst_path.startswith('mrcc:'):
        if config_path != f'rclone/{message.from_user.id}.conf':
            await sendMessage(message, 'You should use same rclone.conf to clone between pathies!')
            await delete_links(message)
            return
    elif config_path != 'rclone.conf':
        await sendMessage(message, 'You should use same rclone.conf to clone between pathies!')
        await delete_links(message)
        return

    remote, src_path = link.split(':', 1)
    src_path = src_path .strip('/')

    cmd = ['rclone', 'lsjson', '--fast-list', '--stat',
           '--no-modtime', '--config', config_path, f'{remote}:{src_path}']
    res = await cmd_exec(cmd)
    if res[2] != 0:
        if res[2] != -9:
            msg = f'Error: While getting rclone stat. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}'
            await sendMessage(message, msg)
        await delete_links(message)
        return
    rstat = loads(res[0])
    if rstat['IsDir']:
        name = src_path.rsplit('/', 1)[-1] if src_path else remote
        dst_path += name if dst_path.endswith(':') else f'/{name}'
        mime_type = 'Folder'
    else:
        name = src_path.rsplit('/', 1)[-1]
        mime_type = rstat['MimeType']

    await listener.onDownloadStart()

    RCTransfer = RcloneTransferHelper(listener, name)
    LOGGER.info(
        f'Clone Started: Name: {name} - Source: {link} - Destination: {dst_path}')
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    async with download_dict_lock:
        download_dict[message.id] = RcloneStatus(
            RCTransfer, message, gid, 'cl', listener.extra_details)
    await sendStatusMessage(message)
    link, destination = await RCTransfer.clone(config_path, remote, src_path, dst_path, rcf, mime_type)
    if not link:
        await delete_links(message)
        return
    LOGGER.info(f'Cloning Done: {name}')
    cmd1 = ['rclone', 'lsf', '--fast-list', '-R',
            '--files-only', '--config', config_path, destination]
    cmd2 = ['rclone', 'lsf', '--fast-list', '-R',
            '--dirs-only', '--config', config_path, destination]
    cmd3 = ['rclone', 'size', '--fast-list', '--json',
            '--config', config_path, destination]
    res1, res2, res3 = await gather(cmd_exec(cmd1), cmd_exec(cmd2), cmd_exec(cmd3))
    if res1[2] != res2[2] != res3[2] != 0:
        if res1[2] == -9:
            return
        files = None
        folders = None
        size = 0
        LOGGER.error(
            f'Error: While getting rclone stat. Path: {destination}. Stderr: {res1[1][:4000]}')
    else:
        files = len(res1[0].split("\n"))
        folders = len(res2[0].split("\n"))
        rsize = loads(res3[0])
        size = rsize['bytes']
    await listener.onUploadComplete(link, size, files, folders, mime_type, name, destination)


async def gdcloneNode(message, link, listener):
    if not is_gdrive_link(link) and is_share_link(link):
        process_msg = await sendMessage(message, f"Processing: <code>{link}</code>")
        try:
            link = await sync_to_async(direct_link_generator, link)
            LOGGER.info(f"Generated link: {link}")
            await editMessage(process_msg, f"Generated link: <code>{link}</code>")
        except DirectDownloadLinkException as e:
            LOGGER.error(str(e))
            if str(e).startswith('ERROR:'):
                await editMessage(process_msg, str(e))
                await delete_links(message)
                return
        await deleteMessage(process_msg)

    if is_gdrive_link(link):
        gd = GoogleDriveHelper()
        name, mime_type, size, files, _ = await sync_to_async(gd.count, link)
        if mime_type is None:
            await sendMessage(message, name)
            await delete_links(message)
            return
        if config_dict['STOP_DUPLICATE']:
            LOGGER.info('Checking File/Folder if already in Drive...')
            telegraph_content, contents_no = await sync_to_async(gd.drive_list, name, True)
            if telegraph_content:
                LOGGER.info('File/Folder is already available in Drive.')
                msg = f"File/Folder is already available in Drive.\nHere are {contents_no} list results:"
                button = await get_telegraph_list(telegraph_content)
                await sendMessage(message, msg, button)
                await delete_links(message)
                return

        if limit_exceeded := await limit_checker(size, listener):
            await sendMessage(listener.message, limit_exceeded)
            await delete_links(listener.message)
            return
        await listener.onDownloadStart()
        LOGGER.info(f'Clone Started: Name: {name} - Source: {link}')
        drive = GoogleDriveHelper(name, listener=listener)
        if files <= 20:
            msg = await sendMessage(message, f"Cloning: <code>{link}</code>")
            link, size, mime_type, files, folders, dir_id = await sync_to_async(drive.clone, link, listener.drive_id or config_dict['GDRIVE_ID'])
            await deleteMessage(msg)
        else:
            gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
            async with download_dict_lock:
                download_dict[message.id] = GdriveStatus(
                    drive, size, message, gid, 'cl', listener.extra_details)
            await sendStatusMessage(message)
            link, size, mime_type, files, folders, dir_id = await sync_to_async(drive.clone, link, listener.drive_id or config_dict['GDRIVE_ID'])
        if not link:
            await delete_links(message)
            return
        LOGGER.info(f'Cloning Done: {name}')
        await listener.onUploadComplete(link, size, files, folders, mime_type, name, drive_id=dir_id)
    else:
        await sendMessage(message, CLONE_HELP_MESSAGE.format_map({'cmd': message.command[0]}))


@new_task
async def clone(client, message):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)
    link = ''
    select = False
    multi = 0
    raw_url = None
    if len(message_args) > 1:
        index = 1
        args = mesg[0].split(maxsplit=2)
        args.pop(0)
        for x in args:
            x = x.strip()
            if x == 's':
                select = True
                index += 1
            elif x.isdigit():
                multi = int(x)
                mi = index
            else:
                break
        if multi == 0:
            message_args = mesg[0].split(maxsplit=index)
            if len(message_args) > index:
                x = message_args[index].strip()
                if not x.startswith(('up:', 'rcf:', 'id:', 'index:')):
                    link = re_split(r' up: | rcf: | id: | index: ', x)[0].strip()

    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention
    if reply_to := message.reply_to_message:
        if len(link) == 0:
            link = reply_to.text.split('\n', 1)[0].strip()
        if sender_chat := reply_to.sender_chat:
            tag = sender_chat.title
        elif not reply_to.from_user.is_bot:
            if username := reply_to.from_user.username:
                tag = f"@{username}"
            else:
                tag = reply_to.from_user.mention

    rcf = mesg[0].split(' rcf: ', 1)
    rcf = re_split(' up: | id: | index: ', rcf[1])[
        0].strip() if len(rcf) > 1 else None

    dst_path = mesg[0].split(' up: ', 1)
    dst_path = re_split(' rcf: | id: | index: ', dst_path[1])[
        0].strip() if len(dst_path) > 1 else None

    drive_id = mesg[0].split(' id: ', 1)
    drive_id = re_split(' rcf: | up: | index: ', drive_id[1])[
        0].strip() if len(drive_id) > 1 else None
    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    index_link = mesg[0].split(' index: ', 1)
    index_link = re_split(' rcf: | up: | id: ', index_link[1])[
        0].strip() if len(index_link) > 1 else None
    if index_link and not index_link.startswith(('http://', 'https://')):
        index_link = None
    if index_link and not index_link.endswith('/'):
        index_link += '/'

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
        if message.sender_chat:
            nextmsg.sender_chat = message.sender_chat
        nextmsg.from_user = message.from_user
        await sleep(4)
        await clone(client, nextmsg)

    __run_multi()

    if not link:
        await sendMessage(message, CLONE_HELP_MESSAGE.format_map({'cmd': message.command[0]}))
        await delete_links(message)
        return

    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        await delete_links(message)
        return
    if not await isAdmin(message):
        raw_url = await stop_duplicate_tasks(message, link)
        if raw_url == 'duplicate_tasks':
            await delete_links(message)
            return
        if await none_admin_utils(message, tag, False):
            return
    if (dmMode := config_dict['DM_MODE']) and message.chat.type == message.chat.type.SUPERGROUP:
        dmMessage = await sendDmMessage(message, dmMode, False)
        if dmMessage == 'BotNotStarted':
            await delete_links(message)
            return
    else:
        dmMessage = None

    logMessage = await sendLogMessage(message, link, tag)
    if is_rclone_path(link):
        if not await aiopath.exists('rclone.conf') and not await aiopath.exists(f'rclone/{message.from_user.id}.conf'):
            await sendMessage(message, 'Rclone Config Not exists!')
            await delete_links(message)
            return
        if not config_dict['RCLONE_PATH'] and not dst_path:
            await sendMessage(message, 'Destinantion not specified!')
            await delete_links(message)
            return
        listener = MirrorLeechListener(message, tag=tag, select=select, isClone=True, drive_id=drive_id,
                                       index_link=index_link, dmMessage=dmMessage, logMessage=logMessage, raw_url=raw_url)
        await rcloneNode(client, message, link, listener)
    else:
        if not drive_id and len(categories) > 1:
            drive_id, index_link = await open_category_btns(message)
        if drive_id and not await sync_to_async(GoogleDriveHelper().getFolderData, drive_id):
            await sendMessage(message, "Google Drive id validation failed!!")
            await delete_links(message)
            return
        if not config_dict['GDRIVE_ID'] and not drive_id:
            await sendMessage(message, 'GDRIVE_ID not Provided!')
            await delete_links(message)
            return
        listener = MirrorLeechListener(message, tag=tag, select=select, isClone=True, drive_id=drive_id,
                                       index_link=index_link, dmMessage=dmMessage, logMessage=logMessage, raw_url=raw_url)
        await gdcloneNode(message, link, listener)


bot.add_handler(MessageHandler(clone, filters=command(
    BotCommands.CloneCommand) & CustomFilters.authorized))
