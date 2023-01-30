from time import time

from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (CATEGORY_NAMES, btn_listener, dispatcher, download_dict,
                 download_dict_lock)
from bot.helper.ext_utils.bot_utils import (MirrorStatus, get_category_btns,
                                            getDownloadByGid, new_thread)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      editMessage, sendMessage)


def change_category(update, context):
    message = update.message
    if message.from_user.id in [1087968824, 136817688]:
        message.from_user.id = anno_checker(message)
        if not message.from_user.id:
            return
    user_id = message.from_user.id
    if len(context.args) == 1:
        gid = context.args[0]
        dl = getDownloadByGid(gid)
        if not dl:
            sendMessage(f"GID: <code>{gid}</code> Not Found.", context.bot, message)
            return
    elif message.reply_to_message:
        mirror_message = message.reply_to_message
        with download_dict_lock:
            if mirror_message.message_id in download_dict:
                dl = download_dict[mirror_message.message_id]
            else:
                dl = None
        if not dl:
            sendMessage("This is not an active task!", context.bot, message)
            return
    elif len(context.args) == 0:
        msg = "Reply to an active /{cmd} which was used to start the download or add gid along with {cmd}\n\n" \
            "This command mainly for change category incase you decided to change category from already added download. " \
            "But you can always use /{mir} with to select category before download start."
        sendMessage(msg.format_map({'cmd': BotCommands.CategorySelect,'mir': BotCommands.MirrorCommand[0]}), context.bot, message)
        return

    if not CustomFilters.owner_query(user_id) and dl.message.from_user.id != user_id:
        sendMessage("This task is not for you!", context.bot, message)
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUEDL]:
        sendMessage(f'Task should be on {MirrorStatus.STATUS_DOWNLOADING} or {MirrorStatus.STATUS_PAUSED} or {MirrorStatus.STATUS_QUEUEDL}', context.bot, message)
        return
    listener = dl.listener() if dl and hasattr(dl, 'listener') else None
    if listener:
        listener.selectCategory()
    else:
        sendMessage("Can not change Category for this task!", context.bot, message)

@new_thread
def confirm_category(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message
    data = query.data
    data = data.split()
    msg_id = int(data[2])
    try:
        categoryInfo = btn_listener[msg_id]
    except KeyError:
        return editMessage('<b>Old Task</b>', message)
    listener = categoryInfo[2]
    if user_id != listener.message.from_user.id and not CustomFilters.owner_query(user_id):
        query.answer("This task is not for you!", show_alert=True)
    elif data[1] == 'scat':
        c_index = int(data[3])
        if listener.c_index == c_index:
            return query.answer(f"{CATEGORY_NAMES[c_index]} is Selected Already", show_alert=True)
        query.answer()
        listener.c_index = c_index
    elif data[1] == 'cancel':
        query.answer()
        listener.c_index = categoryInfo[3]
        if listener.isClone:
            mode = f'Clone {CATEGORY_NAMES[listener.c_index]}'
        else:
            mode = f'Drive {CATEGORY_NAMES[listener.c_index]}'
        if listener.isZip:
            mode += ' as Zip'
        elif listener.extract:
            mode += ' as Unzip'
        listener.mode = mode
        del btn_listener[msg_id]
        return editMessage("<b>Skipped</b>", message)
    elif data[1] == 'done':
        query.answer()
        del btn_listener[msg_id]
        if listener.isClone:
            mode = f'Clone {CATEGORY_NAMES[listener.c_index]}'
        else:
            mode = f'Drive {CATEGORY_NAMES[listener.c_index]}'
        if listener.isZip:
            mode += ' as Zip'
        elif listener.extract:
            mode += ' as Unzip'
        listener.mode = mode
        message.delete()
        return
    time_out = categoryInfo[0] - (time() - categoryInfo[1])
    text, btns = get_category_btns(time_out, msg_id, listener.c_index)
    editMessage(text, message, btns)

confirm_category_handler = CallbackQueryHandler(confirm_category, pattern="change")

change_category_handler = CommandHandler(BotCommands.CategorySelect, change_category,
                        filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user))
dispatcher.add_handler(confirm_category_handler)
dispatcher.add_handler(change_category_handler)
