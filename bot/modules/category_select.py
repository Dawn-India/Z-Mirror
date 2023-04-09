from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import (bot, btn_listener, categories, download_dict, download_dict_lock)
from bot.helper.ext_utils.help_messages import CAT_SEL_HELP_MESSAGE
from bot.helper.ext_utils.bot_utils import (MirrorStatus, getDownloadByGid,
                                            is_gdrive_link, is_url, new_task,
                                            sync_to_async)
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker, editMessage,
                                                      open_category_btns, sendMessage)


async def change_category(client, message):
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        return
    user_id = message.from_user.id
    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)
    index = 1
    drive_id = None
    index_link = None
    dl = None
    gid = None
    if len(message_args) > 1:
        args = mesg[0].split(maxsplit=2)
        for x in args:
            x = x.strip()
            if x.startswith('id:'):
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
        message_args = mesg[0].split(maxsplit=index)
        if len(message_args) > index:
            gid = message_args[index].strip()
            dl = await getDownloadByGid(gid)
            if not dl:
                await sendMessage(message, f"GID: <code>{gid}</code> Not Found.")
                return
    if reply_to := message.reply_to_message:
        async with download_dict_lock:
            dl = download_dict.get(reply_to.id, None)
        if not dl:
            await sendMessage(message, "This is not an active task!")
            return
    if not dl:
        await sendMessage(message, CAT_SEL_HELP_MESSAGE.format_map({'cmd': BotCommands.CategorySelect,'mir': BotCommands.MirrorCommand[0]}))
        return
    if not await CustomFilters.sudo(client, message) and dl.message.from_user.id != user_id:
        await sendMessage(message, "This task is not for you!")
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUEDL]:
        await sendMessage(message, f'Task should be on {MirrorStatus.STATUS_DOWNLOADING} or {MirrorStatus.STATUS_PAUSED} or {MirrorStatus.STATUS_QUEUEDL}')
        return
    listener = dl.listener() if dl and hasattr(dl, 'listener') else None
    if listener and not listener.isLeech:
        if not index_link and not drive_id and categories:
            drive_id, index_link = await open_category_btns(message)
        if not index_link and not drive_id:
            return await sendMessage(message, "Time out")
        msg = '<b>Task has been Updated Successfully!</b>'
        if drive_id:
            if not (folder_name:= await sync_to_async(GoogleDriveHelper().getFolderData, drive_id)):
                return await sendMessage(message, "Google Drive id validation failed!!")
            if listener.drive_id and listener.drive_id == drive_id:
                msg +=f'\n\n<b>Folder name</b> : {folder_name} Already selected'
            else:
                msg +=f'\n\n<b>Folder name</b> : {folder_name}'
            listener.drive_id = drive_id
        if index_link:
            listener.index_link = index_link
            msg +=f'\n\n<b>Index Link</b> : <code>{index_link}</code>'
        return await sendMessage(message, msg)
    else:
        await sendMessage(message, "Can not change Category for this task!")

@new_task
async def confirm_category(client, query):
    user_id = query.from_user.id
    data = query.data.split(maxsplit=3)
    msg_id = int(data[2])
    if msg_id not in btn_listener:
        return await editMessage(query.message, '<b>Old Task</b>')
    if user_id != int(data[1]) and not await CustomFilters.sudo(client, query):
        return await query.answer(text="This task is not for you!", show_alert=True)
    await query.answer()
    btn_listener[msg_id][0] = categories[data[3]].get('drive_id')
    btn_listener[msg_id][1] = categories[data[3]].get('index_link')
        

bot.add_handler(MessageHandler(change_category, filters=command(BotCommands.CategorySelect) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(confirm_category, filters=regex("^scat")))
