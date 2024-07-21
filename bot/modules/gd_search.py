from asyncio import sleep
from time import time
from pyrogram.filters import (
    command,
    regex
)
from pyrogram.handlers import (
    MessageHandler,
    CallbackQueryHandler
)

from bot import (
    LOGGER,
    bot,
    user_data
)
from bot.helper.ext_utils.bot_utils import (
    sync_to_async,
    new_task,
    get_telegraph_list
)
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.task_utils.gdrive_utils.search import gdSearch
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    anno_checker,
    auto_delete_message,
    sendMessage,
    editMessage
)


async def list_buttons(user_id, isRecursive=True, user_token=False):
    buttons = ButtonMaker()
    buttons.ibutton(
        "Folders",
        f"list_types {user_id} folders {isRecursive} {user_token}"
    )
    buttons.ibutton(
        "Files",
        f"list_types {user_id} files {isRecursive} {user_token}")
    buttons.ibutton(
        "Both",
        f"list_types {user_id} both {isRecursive} {user_token}")
    buttons.ibutton(
        f"Recursive: {isRecursive}",
        f"list_types {user_id} rec {isRecursive} {user_token}",
    )
    buttons.ibutton(
        f"User Token: {user_token}",
        f"list_types {user_id} ut {isRecursive} {user_token}",
    )
    buttons.ibutton(
        "Cancel",
        f"list_types {user_id} cancel")
    return buttons.build_menu(2)


async def _list_drive(
        key,
        message,
        item_type,
        isRecursive,
        user_token,
        user_id
    ):
    start_time = time()
    LOGGER.info(f"Listing: {key}")
    emsg = None
    from_user = message.reply_to_message.from_user
    if not from_user:
        from_user = await anno_checker(message.reply_to_message)
    if username := from_user.username:
        tag = f"@{username}"
    else:
        tag = from_user.mention
    if user_token:
        user_dict = user_data.get(
            user_id,
            {}
        )
        target_id = user_dict.get(
            "gdrive_id",
            ""
        ) or ""
        LOGGER.info(target_id)
    else:
        target_id = ""
    (
        telegraph_content,
        contents_no
    ) = await sync_to_async(
        gdSearch(
            isRecursive=isRecursive,
            itemType=item_type
        ).drive_list,
        key,
        target_id,
        user_id,
    )
    await sleep(1)
    elapsed = get_readable_time(time() - start_time) # type: ignore
    if telegraph_content:
        try:
            button = await get_telegraph_list(telegraph_content)
        except Exception as e:
            emsg = f"{e}"
            await editMessage(
                message,
                emsg
            )
            return
        emsg = f"<b>Found {contents_no} result for <i>{key}</i></b>\n"
        emsg += f"<b>Type</b>: {item_type}\n<b>Recursive list</b>: {isRecursive}\n"
        emsg += f"<b>Elapsed</b>: {elapsed}\n\ncc: {tag}"
        await editMessage(
            message,
            emsg,
            button
        )
    else:
        emsg = f"No result found for <i>{key}</i>\n"
        emsg += f"<b>Type</b>: {item_type}\n<b>Recursive list</b>: {isRecursive}\n"
        emsg += f"<b>Elapsed</b>: {elapsed}\n\ncc: {tag}"
        await editMessage(
            message,
            emsg
        )
    if emsg is not None:
        await auto_delete_message(
            message.reply_to_message,
            message
        )


@new_task
async def select_type(_, query):
    user_id = query.from_user.id
    message = query.message
    key = message.reply_to_message.text.split(maxsplit=1)[1].strip()
    data = query.data.split()
    emsg = None
    if user_id != int(data[1]):
        return await query.answer(
            text="Not Yours!",
            show_alert=True
        )
    elif data[2] == "rec":
        await query.answer()
        isRecursive = not bool(eval(data[3]))
        buttons = await list_buttons(
            user_id,
            isRecursive,
            eval(data[4])
        )
        emsg = "Choose list options:"
        await editMessage(
            message,
            emsg,
            buttons
        )
        return
    elif data[2] == "ut":
        await query.answer()
        user_token = not bool(eval(data[4]))
        buttons = await list_buttons(
            user_id,
            eval(data[3]),
            user_token
        )
        emsg = "Choose list options:"
        await editMessage(
            message,
            emsg,
            buttons
        )
        return
    elif data[2] == "cancel":
        await query.answer()
        emsg = "list has been canceled!"
        await editMessage(
            message,
            emsg,
        )
        return
    if emsg is not None:
        await auto_delete_message(
            message.reply_to_message,
            message
        )
    await query.answer()
    item_type = data[2]
    isRecursive = eval(data[3])
    user_token = eval(data[4])
    await editMessage(
        message,
        f"<b>Searching for <i>{key}</i></b>"
    )
    await _list_drive(
        key,
        message,
        item_type,
        isRecursive,
        user_token,
        user_id
    )


async def gdrive_search(_, message):
    from_user = message.from_user
    if not from_user:
        from_user = await anno_checker(message)
    if len(message.text.split()) == 1:
        gmsg = await sendMessage(
            message,
            "Send a search key along with command"
        )
        await auto_delete_message(
            message,
            gmsg
        )
        return
    user_id = from_user.id
    buttons = await list_buttons(user_id)
    gmsg = await sendMessage(
        message,
        "Choose list options:",
        buttons
    )
    await auto_delete_message(
        message,
        gmsg
    )


bot.add_handler( # type: ignore
    MessageHandler(
        gdrive_search,
        filters=command(
            BotCommands.ListCommand
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    CallbackQueryHandler(
        select_type,
        filters=regex("^list_types")
    )
)
