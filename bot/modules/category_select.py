
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (btn_listener, categories, dispatcher, download_dict,
                 download_dict_lock)
from bot.helper.ext_utils.bot_utils import (MirrorStatus, getDownloadByGid,
                                            is_gdrive_link, is_url)
from bot.helper.ext_utils.rate_limiter import ratelimiter
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      editMessage,
                                                      open_category_btns,
                                                      sendMessage)


@ratelimiter
def change_category(update, context):
    message = update.message
    if message.from_user.id in [1087968824, 136817688]:
        message.from_user.id = anno_checker(message)
        if not message.from_user.id:
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
            dl = getDownloadByGid(gid)
            if not dl:
                sendMessage(f"GID: <code>{gid}</code> Not Found.", context.bot, message)
                return
    if reply_to := message.reply_to_message:
        with download_dict_lock:
            dl = download_dict.get(reply_to.message_id, None)
        if not dl:
            sendMessage("This is not an active task!", context.bot, message)
            return
    if not dl:
        msg = """
Reply to an active /{cmd} which was used to start the download or add gid along with {cmd}
This command mainly for change category incase you decided to change category from already added download.
But you can always use /{mir} with to select category before download start.

<b>Upload Custom Drive</b>
<code>/{cmd}</code> <b>id:</b><code>drive_folder_link</code> or <code>drive_id</code> <b>index:</b><code>https://anything.in/0:</code> gid or by replying to active download
drive_id must be folder id and index must be url else it will not accept
""".format_map({'cmd': BotCommands.CategorySelect,'mir': BotCommands.MirrorCommand[0]})
        sendMessage(msg, context.bot, message)
        return
    if not CustomFilters.owner_query(user_id) and dl.message.from_user.id != user_id:
        sendMessage("This task is not for you!", context.bot, message)
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUEDL]:
        sendMessage(f'Task should be on {MirrorStatus.STATUS_DOWNLOADING} or {MirrorStatus.STATUS_PAUSED} or {MirrorStatus.STATUS_QUEUEDL}', context.bot, message)
        return
    listener = dl.listener() if dl and hasattr(dl, 'listener') else None
    if listener and not listener.isLeech:
        if not index_link and not drive_id and categories:
            drive_id, index_link = open_category_btns(message)
        if not index_link and not drive_id:
            return sendMessage("Time out", context.bot, message)
        msg = '<b>Task has been Updated Successfully!</b>'
        if drive_id:
            if not (folder_name:= GoogleDriveHelper().getFolderData(drive_id)):
                return sendMessage("Google Drive id validation failed!!", context.bot, message)
            if listener.drive_id and listener.drive_id == drive_id:
                msg +=f'\n\n<b>Folder name</b> : {folder_name} Already selected'
            else:
                msg +=f'\n\n<b>Folder name</b> : {folder_name}'
            listener.drive_id = drive_id
        if index_link:
            listener.index_link = index_link
            msg +=f'\n\n<b>Index Link</b> : <code>{index_link}</code>'
        return sendMessage(msg, context.bot, message)
    else:
        sendMessage("Can not change Category for this task!", context.bot, message)

@ratelimiter
def confirm_category(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split(maxsplit=3)
    msg_id = int(data[2])
    if msg_id not in btn_listener:
        return editMessage('<b>Old Task</b>', query.message)
    if user_id != int(data[1]) and not CustomFilters.owner_query(user_id):
        return query.answer(text="This task is not for you!", show_alert=True)
    query.answer()
    btn_listener[msg_id][1] = categories[data[3]].get('drive_id')
    btn_listener[msg_id][2] = categories[data[3]].get('index_link')
    btn_listener[msg_id][0] = False
        

confirm_category_handler = CallbackQueryHandler(confirm_category, pattern="scat")
change_category_handler = CommandHandler(BotCommands.CategorySelect, change_category,
                        filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user))
dispatcher.add_handler(confirm_category_handler)
dispatcher.add_handler(change_category_handler)
