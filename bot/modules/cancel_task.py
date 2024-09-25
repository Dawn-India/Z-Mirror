from asyncio import sleep
from re import search as re_search

from nekozee.filters import (
    command,
    regex
)
from nekozee.handlers import (
    MessageHandler,
    CallbackQueryHandler
)

from bot import (
    OWNER_ID,
    bot,
    bot_name,
    multi_tags,
    task_dict,
    task_dict_lock,
    user_data
)
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.status_utils import (
    get_task_by_gid,
    get_all_tasks,
    MirrorStatus
)
from ..helper.telegram_helper import button_build
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    anno_checker,
    delete_links,
    send_message,
    auto_delete_message,
    delete_message,
    edit_message
)


@new_task
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
            task = await get_task_by_gid(gid)
            if task is None:
                tmsg = await send_message(
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
            tmsg = await send_message(
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
        tmsg = await send_message(
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
        and task.listener.user_id != user_id
        and (
            user_id not in user_data
            or not user_data[user_id].get("is_sudo")
        )
    ):
        tmsg = await send_message(
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


@new_task
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
    await delete_message(query.message)


async def cancel_all(status, user_id):
    matches = await get_all_tasks(
        status.strip(),
        user_id
    )
    if not matches:
        return False
    for task in matches:
        obj = task.task()
        await obj.cancel_task()
        await sleep(2)
    return True


def create_cancel_buttons(isSudo, user_id=""):
    buttons = button_build.ButtonMaker()
    buttons.data_button(
        "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ",
        f"canall ms {(MirrorStatus.STATUS_DOWNLOADING).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ᴜᴘʟᴏᴀᴅɪɴɢ",
        f"canall ms {(MirrorStatus.STATUS_UPLOADING).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ꜱᴇᴇᴅɪɴɢ",
        f"canall ms {(MirrorStatus.STATUS_SEEDING).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ꜱᴘʟᴛᴛɪɴɢ",
        f"canall ms {(MirrorStatus.STATUS_SPLITTING).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ᴄʟᴏɴɪɴɢ",
        f"canall ms {(MirrorStatus.STATUS_CLONING).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ᴇxᴛʀᴀᴄᴛɪɴɢ",
        f"canall ms {(MirrorStatus.STATUS_EXTRACTING).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ᴀʀᴄʜɪᴠɪɴɢ",
        f"canall ms {(MirrorStatus.STATUS_ARCHIVING).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "Qᴜᴇᴜᴇᴅᴅʟ",
        f"canall ms {(MirrorStatus.STATUS_QUEUEDL).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "Qᴜᴇᴜᴇᴅᴜᴘ",
        f"canall ms {(MirrorStatus.STATUS_QUEUEUP).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ꜱᴀᴍᴘʟᴇᴠɪᴅᴇᴏ",
        f"canall ms {(MirrorStatus.STATUS_SAMVID).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ᴄᴏɴᴠᴇʀᴛᴍᴇᴅɪᴀ",
        f"canall ms {(MirrorStatus.STATUS_CONVERTING).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ᴘᴀᴜꜱᴇᴅ",
        f"canall ms {(MirrorStatus.STATUS_PAUSED).split(' ')[0]} {user_id}"
    )
    buttons.data_button(
        "ᴀʟʟ",
        f"canall ms All {user_id}"
    )
    if isSudo:
        if user_id:
            buttons.data_button(
                "ᴀʟʟ ᴀᴅᴅᴇᴅ ᴛᴀꜱᴋꜱ",
                f"canall bot ms {user_id}"
            )
        else:
            buttons.data_button(
                "ᴍʏ ᴛᴀꜱᴋꜱ",
                f"canall user ms {user_id}"
            )
    buttons.data_button(
        "ᴄʟᴏꜱᴇ",
        f"canall close ms {user_id}"
    )
    return buttons.build_menu(2)


@new_task
async def cancell_all_buttons(_, message):
    async with task_dict_lock:
        count = len(task_dict)
    if count == 0:
        tmsg = await send_message(
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
    can_msg = await send_message(
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
    user_id = (
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
        and user_id
        and user_id != query.from_user.id
    ):
        await query.answer(
            "Not Yours!",
            show_alert=True
        )
    else:
        await query.answer()
    if data[1] == "close":
        await delete_message(reply_to)
        await delete_message(message)
    elif data[1] == "back":
        button = create_cancel_buttons(
            isSudo,
            user_id # type: ignore
        )
        await edit_message(
            message,
            "Choose tasks to cancel!",
            button
        )
    elif data[1] == "bot":
        button = create_cancel_buttons(
            isSudo,
            ""
        )
        await edit_message(
            message,
            "Choose tasks to cancel!",
            button
        )
    elif data[1] == "user":
        button = create_cancel_buttons(
            isSudo,
            query.from_user.id
        )
        await edit_message(
            message,
            "Choose tasks to cancel!",
            button
        )
    elif data[1] == "ms":
        buttons = button_build.ButtonMaker()
        buttons.data_button(
            "ʏᴇꜱ!",
            f"canall {data[2]} confirm {user_id}"
        )
        buttons.data_button(
            "ʙᴀᴄᴋ",
            f"canall back confirm {user_id}"
        )
        buttons.data_button(
            "ᴄʟᴏꜱᴇ",
            f"canall close confirm {user_id}"
        )
        button = buttons.build_menu(2)
        await edit_message(
            message,
            f"Are you sure you want to cancel all {data[2]} tasks",
            button
        )
    else:
        button = create_cancel_buttons(
            isSudo,
            user_id # type: ignore
        )
        await edit_message(
            message,
            "Choose tasks to cancel.",
            button
        )
        res = await cancel_all(
            data[1],
            user_id
        )
        if not res:
            tmsg = await send_message(
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
            BotCommands.CancelTaskCommand,
            case_sensitive=True
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
            BotCommands.CancelAllCommand,
            case_sensitive=True
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
