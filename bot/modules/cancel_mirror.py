from asyncio import sleep

from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import bot, bot_name, bot_loop, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import (MirrorStatus, getAllDownload,
                                            getDownloadByGid, new_task)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (anno_checker, auto_delete_message,
                                                      editMessage, sendMessage)


async def cancel_mirror(client, message):
    if not message.from_user:
        message.from_user = await anno_checker(message)
    if not message.from_user:
        return
    user_id = message.from_user.id
    msg = message.text.split('_', maxsplit=1)
    if len(msg) > 1:
        cmd_data = msg[1].split('@', maxsplit=1)
        if len(cmd_data) > 1 and cmd_data[1].strip() != bot_name:
            return
        gid = cmd_data[0]
        dl = await getDownloadByGid(gid)
        if not dl:
            tmsg = await sendMessage(message, f"GID: <code>{gid}</code> Not Found.")
            await auto_delete_message(message, tmsg)
            return
    elif reply_to_id := message.reply_to_message_id:
        async with download_dict_lock:
            dl = download_dict.get(reply_to_id, None)
        if not dl:
            tmsg = await sendMessage(message, "This is not an active task!")
            await auto_delete_message(message, tmsg)
            return
    elif len(msg) == 1:
        msg = f"Reply to an active Command message which was used to start the download" \
            f" or send <code>/{BotCommands.CancelMirror}_GID@{bot_name}</code> to cancel it!"
        tmsg = await sendMessage(message, msg)
        await auto_delete_message(message, tmsg)
        return

    if not await CustomFilters.sudo(client, message) and dl.message.from_user.id != user_id:
        tmsg = await sendMessage(message, "This task is not for you!")
        await auto_delete_message(message, tmsg)
        return
    obj = dl.download()
    await obj.cancel_download()

cancel_listener = {}


async def cancel_all(status, info, listOfTasks):
    user_id = info[0]
    msg = info[1]
    tag = info[3]
    success = 0
    failed = 0
    _msg = f"<b>User id</b>: {user_id}\n" if user_id else "<b>Everyone</b>\n"
    _msg += f"<b>Status</b>: {status}\n"
    _msg += f"<b>Total</b>: {len(listOfTasks)}\n"
    for dl in listOfTasks:
        try:
            obj = dl.download()
            await obj.cancel_download()
            success += 1
            await sleep(1)
        except:
            failed += 1
        new_msg = f"<b>Success</b>: {success}\n"
        new_msg += f"<b>Failed</b>: {failed}\n"
        new_msg += f"<b>#cancel_all</b> : {tag}"
        emsg = await editMessage(msg, _msg+new_msg)
        await auto_delete_message(msg, emsg)


async def cancell_all_buttons(client, message):
    async with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        tmsg = await sendMessage(message, "No active tasks!")
        await auto_delete_message(message, tmsg)
        return
    if not message.from_user:
        tag = 'Anonymous'
        message.from_user = await anno_checker(message)
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention
    user_id = message.from_user.id
    if await CustomFilters.sudo(client, message):
        if reply_to := message.reply_to_message:
            user_id = reply_to.from_user.id
        elif len(message.command) == 2 and message.command[1].casefold() == 'all':
            user_id = None
        elif len(message.command) == 2 and message.command[1].isdigit():
            try:
                user_id = int(message.command[1])
            except:
                tmsg = await sendMessage(message, "Invalid Argument! Send Userid or reply")
                await auto_delete_message(message, tmsg)
                return
    if user_id and not await getAllDownload('all', user_id):
        tmsg = await sendMessage(message, f"{user_id} Don't have any active task!")
        await auto_delete_message(message, tmsg)
        return
    msg_id = message.id
    buttons = ButtonMaker()
    buttons.ibutton("Downloading",  f"cnall {MirrorStatus.STATUS_DOWNLOADING} {msg_id}")
    buttons.ibutton("Uploading",    f"cnall {MirrorStatus.STATUS_UPLOADING} {msg_id}")
    buttons.ibutton("Seeding",      f"cnall {MirrorStatus.STATUS_SEEDING} {msg_id}")
    buttons.ibutton("Cloning",      f"cnall {MirrorStatus.STATUS_CLONING} {msg_id}")
    buttons.ibutton("Extracting",   f"cnall {MirrorStatus.STATUS_EXTRACTING} {msg_id}")
    buttons.ibutton("Archiving",    f"cnall {MirrorStatus.STATUS_ARCHIVING} {msg_id}")
    buttons.ibutton("QueuedDl",     f"cnall {MirrorStatus.STATUS_QUEUEDL} {msg_id}")
    buttons.ibutton("QueuedUp",     f"cnall {MirrorStatus.STATUS_QUEUEUP} {msg_id}")
    buttons.ibutton("Splitting",    f"cnall {MirrorStatus.STATUS_SPLITTING} {msg_id}")
    buttons.ibutton("Paused",       f"cnall {MirrorStatus.STATUS_PAUSED} {msg_id}")
    buttons.ibutton("All",          f"cnall all {msg_id}")
    buttons.ibutton("Close",        f"cnall close {msg_id}")
    button = buttons.build_menu(2)
    can_msg = await sendMessage(message, 'Choose tasks to cancel. You have 30 Secounds only', button)
    cancel_listener[msg_id] = [user_id, can_msg, message.from_user.id, tag]
    bot_loop.create_task(_auto_cancel(can_msg, msg_id))


@new_task
async def cancel_all_update(_, query):
    data = query.data.split()
    user_id = query.from_user.id
    data = query.data.split()
    message = query.message
    msg_id = int(data[2])
    if not (info := cancel_listener.get(msg_id)):
        return await editMessage(message, "This is an old message")
    if info[0] and info[2] != user_id:
        return await query.answer(text="You are not allowed to do this!", show_alert=True)
    elif data[1] == 'close':
        await query.answer()
        del cancel_listener[msg_id]
        return await editMessage(message, "Cancellation Listener Closed.", message)
    if not (listOfTasks := await getAllDownload(data[1], info[0])):
        return await query.answer(text=f"You don't have any active task in {data[1]}", show_alert=True)
    await query.answer(f"{len(listOfTasks)} will be cancelled in {data[1]}", show_alert=True)
    del cancel_listener[msg_id]
    await cancel_all(data[1], info, listOfTasks)


async def _auto_cancel(msg, msg_id):
    await sleep(30)
    if cancel_listener.get(msg_id):
        del cancel_listener[msg_id]
        await editMessage(msg, 'Timed out!')

bot.add_handler(MessageHandler(cancel_mirror, filters=regex(
    f"^/{BotCommands.CancelMirror}(_\w+)?(?!all)") & CustomFilters.authorized))
bot.add_handler(MessageHandler(cancell_all_buttons, filters=command(
    BotCommands.CancelAllCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(cancel_all_update, filters=regex("^cnall")))
