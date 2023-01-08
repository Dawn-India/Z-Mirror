from threading import Thread
from time import sleep

from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import dispatcher, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import (MirrorStatus, getAllDownload,
                                            getDownloadByGid)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker,
                                                      editMessage, sendMessage)


def cancel_mirror(update, context):
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
    elif mirror_message:= message.reply_to_message:
        with download_dict_lock:
            dl = download_dict.get(mirror_message.message_id)
        if not dl:
            return sendMessage("This is not an active task!", context.bot, message)
    elif len(context.args) == 0:
        msg = f"Reply to an active Command message which was used to start the download" \
              f" or send <code>/{BotCommands.CancelMirror} GID</code> to cancel it!"
        return sendMessage(msg, context.bot, message)

    if not CustomFilters.owner_query(user_id) and dl.message.from_user.id != user_id:
        sendMessage("This task is not for you!", context.bot, message)
        return

    if dl.status() == MirrorStatus.STATUS_CONVERTING:
        sendMessage("Converting... Can't cancel this task!", context.bot, message)
        return

    dl.download().cancel_download()

cancel_listener = {}

def cancel_all(status, info):
    user_id = info[0]
    msg = info[1]
    umsg = info[2]
    editMessage(f"Canceling tasks for {user_id or 'All'} in {status}", msg)
    if dls:= getAllDownload(status, user_id, False):
        canceled = 0
        cant_cancel = 0
        for dl in dls:
            try:
                if dl.status() == MirrorStatus.STATUS_CONVERTING:
                    cant_cancel += 1
                    continue
                dl.download().cancel_download()
                canceled += 1
                sleep(1)
            except:
                cant_cancel += 1
                continue
            editMessage(f"Canceling tasks for {user_id or 'All'} in {status} canceled {canceled}/{len(dls)}", msg)
        sleep(1)
        if umsg.from_user.username:
            tag = f"@{umsg.from_user.username}"
        else:
            tag = umsg.from_user.mention_html()
        _msg = "Canceling task Done\n"
        _msg += f"<b>Success</b>: {canceled}\n"
        _msg += f"<b>Faild</b>: {cant_cancel}\n"
        _msg += f"<b>Total</b>: {len(dls)}\n"
        _msg += f"<b>#cancel_all</b> : {tag}"
        editMessage(_msg, msg)
    else:
        editMessage(f"{user_id} Don't have any active task!", msg)

def cancell_all_buttons(update, context):
    message = update.message
    with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        return sendMessage("No active tasks!", context.bot, message)
    if message.from_user.id in [1087968824, 136817688]:
        message.from_user.id = anno_checker(message)
        if not message.from_user.id:
            return
    user_id = message.from_user.id
    if CustomFilters.owner_query(user_id):
        if reply_to:= message.reply_to_message:
            user_id = reply_to.from_user.id
        elif context.args and context.args[0].lower() == 'all':
            user_id = None
        elif  context.args and context.args[0].isdigit():
            try:
                user_id = int(context.args[0])
            except:
                return sendMessage("Invalid Argument! Send Userid or reply", context.bot, message)
    if user_id and not getAllDownload('all', user_id):
        return sendMessage(f"{user_id} Don't have any active task!", context.bot, message)
    msg_id = message.message_id
    buttons = ButtonMaker()
    buttons.sbutton("Downloading", f"cnall {MirrorStatus.STATUS_DOWNLOADING} {msg_id}")
    buttons.sbutton("Uploading", f"cnall {MirrorStatus.STATUS_UPLOADING} {msg_id}")
    buttons.sbutton("Seeding", f"cnall {MirrorStatus.STATUS_SEEDING} {msg_id}")
    buttons.sbutton("Cloning", f"cnall {MirrorStatus.STATUS_CLONING} {msg_id}")
    buttons.sbutton("Extracting", f"cnall {MirrorStatus.STATUS_EXTRACTING} {msg_id}")
    buttons.sbutton("Archiving", f"cnall {MirrorStatus.STATUS_ARCHIVING} {msg_id}")
    buttons.sbutton("QueuedDl", f"canall {MirrorStatus.STATUS_QUEUEDL}")
    buttons.sbutton("QueuedUp", f"canall {MirrorStatus.STATUS_QUEUEUP}")
    buttons.sbutton("Splitting", f"cnall {MirrorStatus.STATUS_SPLITTING} {msg_id}")
    buttons.sbutton("All", f"cnall all {msg_id}")
    buttons.sbutton("Close", f"cnall close {msg_id}")
    bmgs = sendMessage('Choose tasks to cancel. You have 30 Secounds only', context.bot, message, buttons.build_menu(2))
    cancel_listener[msg_id] = [user_id, bmgs, message]
    Thread(target=_auto_cancel, args=(bmgs, msg_id)).start()

def cancel_all_update(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    message = query.message
    msg_id = int(data[2])
    try:
        info = cancel_listener[msg_id]
    except:
        return editMessage("This is an old message", message)
    if info[0] and info[2].from_user.id != user_id:
        return query.answer(text="You are not allowed to do this!", show_alert=True)
    elif data[1] == 'close':
        query.answer()
        del cancel_listener[msg_id]
        return editMessage("Cancellation Listener Closed.", message)
    if info[0] and not getAllDownload(data[1], info[0]):
        return query.answer(text=f"You don't have any active task in {data[1]}", show_alert=True)
    query.answer()
    del cancel_listener[msg_id]
    Thread(target=cancel_all, args=(data[1], info)).start()

def _auto_cancel(msg, msg_id):
    sleep(30)
    try:
        if cancel_listener.get(msg_id):
            del cancel_listener[msg_id]
            editMessage('Timed out!', msg)
    except:
        pass


cancel_mirror_handler = CommandHandler(BotCommands.CancelMirror, cancel_mirror,
                                   filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user))

cancel_all_handler = CommandHandler(BotCommands.CancelAllCommand, cancell_all_buttons,
                                    filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)

cancel_all_buttons_handler = CallbackQueryHandler(cancel_all_update, pattern="cnall")

dispatcher.add_handler(cancel_all_handler)
dispatcher.add_handler(cancel_mirror_handler)
dispatcher.add_handler(cancel_all_buttons_handler)
