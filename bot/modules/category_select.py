#!/usr/bin/env python3
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import (bot, cached_dict, categories_dict, download_dict,
                 download_dict_lock)
from bot.helper.ext_utils.bot_utils import (MirrorStatus, arg_parser,
                                            getDownloadByGid, is_gdrive_link,
                                            new_task, sync_to_async)
from bot.helper.ext_utils.help_messages import CAT_SEL_HELP_MESSAGE
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker, delete_links,
                                                      auto_delete_message,
                                                      editMessage, isAdmin,
                                                      open_category_btns,
                                                      request_limiter,
                                                      sendMessage)


async def change_category(client, message):
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        return
    user_id = message.from_user.id
    if not await isAdmin(message, user_id) and await request_limiter(message):
        return

    text = message.text.split('\n')
    input_list = text[0].split(' ')

    arg_base = {
                'link': '', 
                '-id': '', 
                '-index': ''
            }

    args = arg_parser(input_list[1:], arg_base)

    drive_id    = args['-id']
    index_link  = args['-index']

    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    dl = None
    if gid := args['link']:
        dl = await getDownloadByGid(gid)
        if not dl:
            cmsg = await sendMessage(message, f"GID: <code>{gid}</code> Not Found.")
            await delete_links(message)
            await auto_delete_message(message, cmsg)
            return
    if reply_to := message.reply_to_message:
        async with download_dict_lock:
            dl = download_dict.get(reply_to.id, None)
        if not dl:
            cmsg = await sendMessage(message, "This is not an active task!")
            await delete_links(message)
            await auto_delete_message(message, cmsg)
            return
    if not dl:
        cmsg = await sendMessage(message, CAT_SEL_HELP_MESSAGE.format(cmd=BotCommands.CategorySelect, mir=BotCommands.MirrorCommand[0]))
        await delete_links(message)
        await auto_delete_message(message, cmsg)
        return
    if not await CustomFilters.sudo(client, message) and dl.message.from_user.id != user_id:
        cmsg = await sendMessage(message, "This task is not for you!")
        await delete_links(message)
        await auto_delete_message(message, cmsg)
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUEDL]:
        cmsg = await sendMessage(message, f'Task should be on {MirrorStatus.STATUS_DOWNLOADING} or {MirrorStatus.STATUS_PAUSED} or {MirrorStatus.STATUS_QUEUEDL}')
        await delete_links(message)
        await auto_delete_message(message, cmsg)
        return
    listener = dl.listener() if dl and hasattr(dl, 'listener') else None
    if listener and not listener.isLeech:
        if not index_link and not drive_id and categories_dict:
            drive_id, index_link = await open_category_btns(message)
        if not index_link and not drive_id:
            cmsg = await sendMessage(message, "Time out")
            await delete_links(message)
            await auto_delete_message(message, cmsg)
            return
        msg = '<b>Task has been Updated Successfully!</b>'
        if drive_id:
            if not (folder_name := await sync_to_async(GoogleDriveHelper().getFolderData, drive_id)):
                return await sendMessage(message, "Google Drive id validation failed!!")
            if listener.drive_id and listener.drive_id == drive_id:
                msg += f'\n\n<b>Folder name</b> : {folder_name} Already selected'
            else:
                msg += f'\n\n<b>Folder name</b> : {folder_name}'
            listener.drive_id = drive_id
        if index_link:
            listener.index_link = index_link
            msg += f'\n\n<b>Index Link</b> : <code>{index_link}</code>'
        return await sendMessage(message, msg)
    else:
        cmsg = await sendMessage(message, "Can not change Category for this task!")
        await delete_links(message)
        await auto_delete_message(message, cmsg)


@new_task
async def confirm_category(client, query):
    user_id = query.from_user.id
    data = query.data.split(maxsplit=3)
    msg_id = int(data[2])
    if msg_id not in cached_dict:
        cmsg = await editMessage(query.message, '<b>Old Task</b>')
        await auto_delete_message(query.message, cmsg)
    if user_id != int(data[1]) and not await CustomFilters.sudo(client, query):
        return await query.answer(text="This task is not for you!", show_alert=True)
    await query.answer()
    cached_dict[msg_id][0] = categories_dict[data[3]].get('drive_id')
    cached_dict[msg_id][1] = categories_dict[data[3]].get('index_link')


bot.add_handler(MessageHandler(change_category, filters=command(BotCommands.CategorySelect) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(confirm_category, filters=regex("^scat")))
