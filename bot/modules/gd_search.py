from asyncio import sleep
from time import time
from nekozee.filters import (
    command,
    regex
)
from nekozee.handlers import (
    MessageHandler,
    CallbackQueryHandler
)

from bot import (
    LOGGER,
    bot,
    user_data
)
from ..helper.ext_utils.bot_utils import (
    new_task,
    sync_to_async,
    get_telegraph_list
)
from ..helper.ext_utils.status_utils import get_readable_time
from ..helper.ext_utils.token_manager import checking_access
from ..helper.task_utils.gdrive_utils.search import GoogleDriveSearch
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    anno_checker,
    auto_delete_message,
    is_admin,
    send_message,
    edit_message
)


async def list_buttons(user_id, is_recursive=True, user_token=False):
    buttons = ButtonMaker()
    buttons.data_button(
        "ꜰᴏʟᴅᴇʀꜱ",
        f"list_types {user_id} folders {is_recursive} {user_token}"
    )
    buttons.data_button(
        "ꜰɪʟᴇꜱ",
        f"list_types {user_id} files {is_recursive} {user_token}")
    buttons.data_button(
        "ʙᴏᴛʜ",
        f"list_types {user_id} both {is_recursive} {user_token}")
    buttons.data_button(
        f"ʀᴇᴄᴜʀꜱɪᴠᴇ: {is_recursive}",
        f"list_types {user_id} rec {is_recursive} {user_token}",
    )
    buttons.data_button(
        f"ᴜꜱᴇʀ\nᴛᴏᴋᴇɴ: {user_token}",
        f"list_types {user_id} ut {is_recursive} {user_token}",
    )
    buttons.data_button(
        "ᴄᴀɴᴄᴇʟ",
        f"list_types {user_id} cancel")
    return buttons.build_menu(2)


async def _list_drive(
        key,
        message,
        item_type,
        is_recursive,
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
        GoogleDriveSearch(
            is_recursive=is_recursive,
            item_type=item_type
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
            await edit_message(
                message,
                emsg
            )
            return
        emsg = f"<b>Found {contents_no} result for <i>{key}</i></b>\n"
        emsg += f"<b>Type</b>: {item_type}\n<b>Recursive list</b>: {is_recursive}\n"
        emsg += f"<b>Elapsed</b>: {elapsed}\n\ncc: {tag}"
        await edit_message(
            message,
            emsg,
            button
        )
    else:
        emsg = f"No result found for <i>{key}</i>\n"
        emsg += f"<b>Type</b>: {item_type}\n<b>Recursive list</b>: {is_recursive}\n"
        emsg += f"<b>Elapsed</b>: {elapsed}\n\ncc: {tag}"
        await edit_message(
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
        is_recursive = not bool(eval(data[3]))
        buttons = await list_buttons(
            user_id,
            is_recursive,
            eval(data[4])
        )
        emsg = "Choose list options:"
        await edit_message(
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
        await edit_message(
            message,
            emsg,
            buttons
        )
        return
    elif data[2] == "cancel":
        await query.answer()
        emsg = "list has been canceled!"
        await edit_message(
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
    is_recursive = eval(data[3])
    user_token = eval(data[4])
    await edit_message(
        message,
        f"<b>Searching for <i>{key}</i></b>"
    )
    await _list_drive(
        key,
        message,
        item_type,
        is_recursive,
        user_token,
        user_id
    )


@new_task
async def gdrive_search(_, message):
    from_user = message.from_user
    if not from_user:
        from_user = await anno_checker(message)
    if len(message.text.split()) == 1:
        gmsg = await send_message(
            message,
            "Send a search key along with command"
        )
        await auto_delete_message(
            message,
            gmsg
        )
        return
    user_id = from_user.id
    if not await is_admin(message, user_id):
        msg, btn = await checking_access(user_id)
        if msg is not None:
            msg += f"\n\n<b>cc</b>: {message.from_user.mention}"
            msg += f"\n<b>Thank You</b>"
            gdmsg = await send_message(message, msg, btn.build_menu(1))
            await auto_delete_message(message, gdmsg)
            return
    buttons = await list_buttons(user_id)
    gmsg = await send_message(
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
            BotCommands.ListCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    CallbackQueryHandler(
        select_type,
        filters=regex("^list_types")
    )
)
