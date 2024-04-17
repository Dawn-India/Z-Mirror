#!/usr/bin/env python3
from time import time
from asyncio import gather, sleep
from json import loads
from secrets import token_urlsafe
from aiofiles.os import path as aiopath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import (LOGGER, bot, categories_dict, config_dict, download_dict,
                 download_dict_lock)
from bot.helper.ext_utils.bot_utils import (arg_parser, cmd_exec, get_readable_time,
                                            get_telegraph_list, is_gdrive_link,
                                            is_rclone_path, is_share_link,
                                            new_task, sync_to_async)
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
from bot.helper.mirror_utils.gdrive_utils.helper import GoogleDriveHelper
from bot.helper.mirror_utils.gdrive_utils.clone import gdClone
from bot.helper.mirror_utils.gdrive_utils.count import gdCount
from bot.helper.mirror_utils.gdrive_utils.search import gdSearch
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      delete_links,
                                                      deleteMessage,
                                                      auto_delete_message,
                                                      editMessage, isAdmin,
                                                      isBot_canDm,
                                                      open_category_btns,
                                                      request_limiter,
                                                      sendLogMessage,
                                                      sendMessage,
                                                      sendStatusMessage)


async def rcloneNode(client, message, link, dst_path, rcf, listener):
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
        rcmsg = await sendMessage(message, f"Rclone Config: {config_path} not Exists!")
        await auto_delete_message(message, rcmsg)
        await delete_links(message)
        return

    if dst_path == 'rcl' or config_dict['RCLONE_PATH'] == 'rcl':
        dst_path = await RcloneList(client, message).get_rclone_path('rcu', config_path)
        if not is_rclone_path(dst_path):
            await sendMessage(message, dst_path)
            await delete_links(message)
            return

    dst_path = (dst_path or config_dict['RCLONE_PATH']).strip('/')
    if not is_rclone_path(dst_path):
        rcmsg = await sendMessage(message, 'Wrong Rclone Clone Destination!')
        await auto_delete_message(message, rcmsg)
        await delete_links(message)
        return
    if dst_path.startswith('mrcc:'):
        if config_path != f'rclone/{message.from_user.id}.conf':
            rcmsg = await sendMessage(message, 'You should use same rclone.conf to clone between paths!')
            await auto_delete_message(message, rcmsg)
            await delete_links(message)
            return
        dst_path = dst_path.lstrip('mrcc:')
    elif config_path != 'rclone.conf':
        rcmsg = await sendMessage(message, 'You should use same rclone.conf to clone between paths!')
        await auto_delete_message(message, rcmsg)
        await delete_links(message)
        return

    remote, src_path = link.split(':', 1)
    src_path = src_path.strip('/')

    cmd = ['rclone', 'lsjson', '--fast-list', '--stat',
           '--no-modtime', '--config', config_path, f'{remote}:{src_path}']
    res = await cmd_exec(cmd)
    if res[2] != 0:
        if res[2] != -9:
            msg = f'Error: While getting rclone stat. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}'
            rcmsg = await sendMessage(message, msg)
            await auto_delete_message(message, rcmsg)
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
    LOGGER.info(f'Clone Started: Name: {name} - Source: {link} - Destination: {dst_path}')
    gid = token_urlsafe(6)
    gid = gid.replace('-', '')
    async with download_dict_lock:
        download_dict[message.id] = RcloneStatus(RCTransfer, message, gid, 'cl', listener.extra_details)
    await sendStatusMessage(message)
    link, destination = await RCTransfer.clone(config_path, remote, src_path, dst_path, rcf, mime_type)
    if not link:
        await delete_links(message)
        return
    LOGGER.info(f'Cloning Done: {name}')
    cmd1 = ['rclone', 'lsf', '--fast-list', '-R', '--files-only', '--config', config_path, destination]
    cmd2 = ['rclone', 'lsf', '--fast-list', '-R', '--dirs-only', '--config', config_path, destination]
    cmd3 = ['rclone', 'size', '--fast-list', '--json', '--config', config_path, destination]
    res1, res2, res3 = await gather(cmd_exec(cmd1), cmd_exec(cmd2), cmd_exec(cmd3))
    if res1[2] != res2[2] != res3[2] != 0:
        if res1[2] == -9:
            return
        files = None
        folders = None
        size = 0
        LOGGER.error(f'Error: While getting rclone stat. Path: {destination}. Stderr: {res1[1][:4000]}')
    else:
        files = len(res1[0].split("\n"))
        folders = len(res2[0].split("\n"))
        rsize = loads(res3[0])
        size = rsize['bytes']
    await listener.onUploadComplete(link, size, files, folders, mime_type, name, destination)


async def gdcloneNode(message, link, listener):
    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention
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
        finally:
            await auto_delete_message(process_msg)

    if is_gdrive_link(link):
        LOGGER.info(f'Cloning: {link}')
        start_time = time()
        name, mime_type, size, files, _ = await sync_to_async(gdCount().count, link)
        if mime_type is None:
            elapsed = time() - start_time
            LOGGER.error(f'Error in cloning: {name}')
            msg = f'Sorry {tag}!\nYour clone has been stopped.'
            msg += f'\n\n<code>Reason : </code>{name}'
            msg += f'\n<code>Elapsed: </code>{get_readable_time(elapsed)}'
            cmsg = await sendMessage(message, msg)
            await delete_links(message)
            await auto_delete_message(message, cmsg)
            return
        if config_dict['STOP_DUPLICATE']:
            LOGGER.info('Checking if File/Folder already in Drive...')
            telegraph_content, contents_no = await sync_to_async(gdSearch(stopDup=True, noMulti=True).drive_list, name)
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
        drive = gdClone(name, listener=listener)
        if files <= 10:
            msg = await sendMessage(message, f"Cloning: <code>{link}</code>")
            link, size, mime_type, files, folders, dir_id = await sync_to_async(drive.clone, link, listener.drive_id)
            await deleteMessage(msg)
        else:
            gid = token_urlsafe(6)
            gid = gid.replace('-', '')
            async with download_dict_lock:
                download_dict[message.id] = GdriveStatus(drive, size, message, gid, 'cl', listener.extra_details)
            await sendStatusMessage(message)
            link, size, mime_type, files, folders, dir_id = await sync_to_async(drive.clone, link, listener.drive_id)
        if not link:
            await delete_links(message)
            return
        LOGGER.info(f'Cloning Done: {name}')
        await listener.onUploadComplete(link, size, files, folders, mime_type, name, dir_id=dir_id)
    else:
        cmsg = await sendMessage(message, CLONE_HELP_MESSAGE.format_map({'cmd': message.command[0]}))
        await auto_delete_message(message, cmsg)
        await delete_links(message)


@new_task
async def clone(client, message):
    input_list = message.text.split(' ')

    arg_base = {
                'link'  : '', 
                '-m'    : 0, 
                '-up'   : '',
                '-rcf'  : '', 
                '-s'    : False, 
                '-id'   : '', 
                '-index': ''
            }

    args = arg_parser(input_list[1:], arg_base)

    multi = int(args['-m']) if args['-m'] and args['-m'].isdigit() else 0

    dst_path    = args['-up']
    rcf         = args['-rcf']
    link        = args['link']
    select      = args['-s']
    drive_id    = args['-id']
    index_link  = args['-index']
    raw_url     = None

    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    if not link and (reply_to := message.reply_to_message):
        link = reply_to.text.split('\n', 1)[0].strip()

    @new_task
    async def __run_multi():
        if multi <= 1:
            return
        if config_dict['DISABLE_MULTI']:
            mimsg = await sendMessage(message, 'Multi is disabled!')
            await delete_links(message)
            await auto_delete_message(message, mimsg)
            return
        await sleep(5)
        msg = [s.strip() for s in input_list]
        index = msg.index('-m')
        msg[index+1] = f"{multi - 1}"
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=message.reply_to_message_id + 1)
        nextmsg = await sendMessage(nextmsg, " ".join(msg))
        nextmsg = await client.get_messages(chat_id=message.chat.id, message_ids=nextmsg.id)
        nextmsg.from_user = message.from_user
        await sleep(5)
        await clone(client, nextmsg)

    await __run_multi()

    if not link:
        cmsg = await sendMessage(message, CLONE_HELP_MESSAGE.format_map({'cmd': message.command[0]}))
        await auto_delete_message(message, cmsg)
        await delete_links(message)
        return

    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        await delete_links(message)
        return
    error_msg = []
    error_button = None
    if not await isAdmin(message):
        if await request_limiter(message):
            await delete_links(message)
            return
        raw_url = await stop_duplicate_tasks(message, link)
        if raw_url == 'duplicate_tasks':
            await delete_links(message)
            return
        none_admin_msg, error_button = await none_admin_utils(message)
        if none_admin_msg:
            error_msg.extend(none_admin_msg)
    if (dmMode := config_dict['DM_MODE']) and message.chat.type == message.chat.type.SUPERGROUP:
        dmMessage, error_button = await isBot_canDm(message, dmMode, button=error_button)
        if dmMessage is not None and dmMessage != 'BotStarted':
            error_msg.append(dmMessage)
    else:
        dmMessage = None
    if error_msg:
        final_msg = f'Hey, <b>{tag}</b>,\n'
        for __i, __msg in enumerate(error_msg, 1):
            final_msg += f'\n<b>{__i}</b>: {__msg}\n'
        final_msg += f'\n<b>Thank You</b>'
        if error_button is not None:
            error_button = error_button.build_menu(2)
        await delete_links(message)
        cmsg = await sendMessage(message, final_msg, error_button)
        await auto_delete_message(message, cmsg)
        return

    logMessage = await sendLogMessage(message, link, tag)
    if is_rclone_path(link):
        if not await aiopath.exists('rclone.conf') and not await aiopath.exists(f'rclone/{message.from_user.id}.conf'):
            await sendMessage(message, 'Rclone Config Not exists!')
            await delete_links(message)
            return
        if not config_dict['RCLONE_PATH'] and not dst_path:
            await sendMessage(message, 'Destination not specified!')
            await delete_links(message)
            return
        listener = MirrorLeechListener(message, tag=tag, select=select, isClone=True,
                                       dmMessage=dmMessage, logMessage=logMessage, raw_url=raw_url)
        await rcloneNode(client, message, link, dst_path, rcf, listener)
    else:
        if not drive_id and len(categories_dict) > 1:
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


bot.add_handler(MessageHandler(clone, filters=command(BotCommands.CloneCommand) & CustomFilters.authorized))
