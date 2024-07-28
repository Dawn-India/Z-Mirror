from asyncio import sleep
from re import search as re_search
from pyrogram.filters import (
    command,
    regex
)
from pyrogram.handlers import (
    MessageHandler,
    CallbackQueryHandler
)

from bot import (
    bot,
    bot_name,
    multi_tags,
    OWNER_ID,
    task_dict,
    task_dict_lock,
    user_data,
)
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import (
    getTaskByGid,
    getAllTasks,
    MirrorStatus
)
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    anno_checker,
    delete_links,
    sendMessage,
    auto_delete_message,
    deleteMessage,
    editMessage,
)


async def cancel_task(_, message):
    if not message.from_user:
        message.from_user = await anno_checker(message)
    user_id = message.from_user.id
    msg = re_search(
        rf"/(?:{BotCommands.CancelTaskCommand[0]}|{BotCommands.CancelTaskCommand[1]})(?:@{bot_name})?[_ ]([a-zA-Z0-9_-]+)(?:@{bot_name})?",
        message.text
    )
    try:
        gid = msg.group(1) # type: ignore
    except AttributeError:
        gid = None
    if gid is not None:
        if len(gid) == 4:
            multi_tags.discard(gid)
            return
        else:
            task = await getTaskByGid(gid)
            if task is None:
                tmsg = await sendMessage(
                    message,
                    f"GID: <code>{gid}</code> Not Found."
                )
                await auto_delete_message(
                    message,
                    tmsg
                )
                return
    elif reply_to_id := message.reply_to_message_id:
        async with task_dict_lock:
            task = task_dict.get(reply_to_id)
        if task is None:
            tmsg = await sendMessage(
                message,
                "This is not an active task!"
            )
            await auto_delete_message(
                message,
                tmsg
            )
            return
    elif gid == None:
        msg = (
            "Reply to an active Command message which was used to start the download"
            f" or send <code>/{BotCommands.CancelTaskCommand[0]} GID</code> to cancel it!"
        )
        tmsg = await sendMessage(
            message,
            msg
        )
        await auto_delete_message(
            message,
            tmsg
        )
        return
    if (
        OWNER_ID != user_id
        and task.listener.userId != user_id
        and (
            user_id not in user_data
            or not user_data[user_id].get("is_sudo")
        )
    ):
        tmsg = await sendMessage(
            message,
            "This task is not for you!"
        )
        await auto_delete_message(
            message,
            tmsg
        )
        return
    obj = task.task()
    await obj.cancel_task()
    await delete_links(message)


async def cancel_multi(_, query):
    data = query.data.split()
    user_id = query.from_user.id
    if (
        user_id != int(data[1])
        and not await CustomFilters.sudo(
            "", # type: ignore
            query
        )
    ):
        await query.answer(
            "Not Yours!",
            show_alert=True
        )
        return
    tag = int(data[2])
    if tag in multi_tags:
        multi_tags.discard(int(data[2]))
        msg = "Stopped!"
    else:
        msg = "Already Stopped/Finished!"
    await query.answer(
        msg,
        show_alert=True
    )
    await deleteMessage(query.message)


async def cancel_all(status, userId):
    matches = await getAllTasks(
        status.strip(),
        userId
    )
    if not matches:
        return False
    for task in matches:
        obj = task.task()
        await obj.cancel_task()
        await sleep(2)
    return True


def create_cancel_buttons(isSudo, userId=""):
    buttons = button_build.ButtonMaker()
    buttons.ibutton(
        "Downloading",
        f"canall ms {(MirrorStatus.STATUS_DOWNLOADING).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "Uploading",
        f"canall ms {(MirrorStatus.STATUS_UPLOADING).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "Seeding",
        f"canall ms {(MirrorStatus.STATUS_SEEDING).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "Spltting",
        f"canall ms {(MirrorStatus.STATUS_SPLITTING).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "Cloning",
        f"canall ms {(MirrorStatus.STATUS_CLONING).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "Extracting",
        f"canall ms {(MirrorStatus.STATUS_EXTRACTING).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "Archiving",
        f"canall ms {(MirrorStatus.STATUS_ARCHIVING).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "QueuedDl",
        f"canall ms {(MirrorStatus.STATUS_QUEUEDL).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "QueuedUp",
        f"canall ms {(MirrorStatus.STATUS_QUEUEUP).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "SampleVideo",
        f"canall ms {(MirrorStatus.STATUS_SAMVID).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "ConvertMedia",
        f"canall ms {(MirrorStatus.STATUS_CONVERTING).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "Paused",
        f"canall ms {(MirrorStatus.STATUS_PAUSED).split(' ')[0]} {userId}"
    )
    buttons.ibutton(
        "All",
        f"canall ms All {userId}"
    )
    if isSudo:
        if userId:
            buttons.ibutton(
                "All Added Tasks",
                f"canall bot ms {userId}"
            )
        else:
            buttons.ibutton(
                "My Tasks",
                f"canall user ms {userId}"
            )
    buttons.ibutton(
        "Close",
        f"canall close ms {userId}"
    )
    return buttons.build_menu(2)


async def cancell_all_buttons(_, message):
    async with task_dict_lock:
        count = len(task_dict)
    if count == 0:
        tmsg = await sendMessage(
            message,
            "No active tasks!"
        )
        await delete_links(message)
        await auto_delete_message(
            message,
            tmsg
        )
        return
    isSudo = await CustomFilters.sudo(
        "", # type: ignore
        message
    )
    msg_txt = message.text.split()
    uid = message.from_user.id
    if len(msg_txt) > 1:
        uid = msg_txt[1]
    button = create_cancel_buttons(
        isSudo,
        uid
    )
    can_msg = await sendMessage(
        message,
        "Choose tasks to cancel!",
        button
    )
    await delete_links(message)
    await auto_delete_message(
        message,
        can_msg
    )


@new_task
async def cancel_all_update(_, query):
    data = query.data.split()
    message = query.message
    reply_to = message.reply_to_message
    userId = (
        int(data[3])
        if len(data) > 3
        else ""
    )
    isSudo = await CustomFilters.sudo(
        "", # type: ignore
        query
    )
    if (
        not isSudo
        and userId
        and userId != query.from_user.id
    ):
        await query.answer(
            "Not Yours!",
            show_alert=True
        )
    else:
        await query.answer()
    if data[1] == "close":
        await deleteMessage(reply_to)
        await deleteMessage(message)
    elif data[1] == "back":
        button = create_cancel_buttons(
            isSudo,
            userId # type: ignore
        )
        await editMessage(
            message,
            "Choose tasks to cancel!",
            button
        )
    elif data[1] == "bot":
        button = create_cancel_buttons(
            isSudo,
            ""
        )
        await editMessage(
            message,
            "Choose tasks to cancel!",
            button
        )
    elif data[1] == "user":
        button = create_cancel_buttons(
            isSudo,
            query.from_user.id
        )
        await editMessage(
            message,
            "Choose tasks to cancel!",
            button
        )
    elif data[1] == "ms":
        buttons = button_build.ButtonMaker()
        buttons.ibutton(
            "Yes!",
            f"canall {data[2]} confirm {userId}"
        )
        buttons.ibutton(
            "Back",
            f"canall back confirm {userId}"
        )
        buttons.ibutton(
            "Close",
            f"canall close confirm {userId}"
        )
        button = buttons.build_menu(2)
        await editMessage(
            message,
            f"Are you sure you want to cancel all {data[2]} tasks",
            button
        )
    else:
        button = create_cancel_buttons(
            isSudo,
            userId # type: ignore
        )
        await editMessage(
            message,
            "Choose tasks to cancel.",
            button
        )
        res = await cancel_all(
            data[1],
            userId
        )
        if not res:
            tmsg = await sendMessage(
                reply_to,
                f"No matching tasks for {data[1]}!"
            )
            await delete_links(message)
            await auto_delete_message(
                message,
                tmsg
            )


bot.add_handler( # type: ignore
    MessageHandler(
        cancel_task,
        filters=command(
            BotCommands.CancelTaskCommand
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        cancel_task,
        filters=regex(
            rf"^/{BotCommands.CancelTaskCommand[1]}(_\w+)?(?!all)"
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        cancell_all_buttons,
        filters=command(
            BotCommands.CancelAllCommand
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    CallbackQueryHandler(
        cancel_all_update,
        filters=regex("^canall")
    )
)
bot.add_handler( # type: ignore
    CallbackQueryHandler(
        cancel_multi,
        filters=regex("^stopm")
    )
)
