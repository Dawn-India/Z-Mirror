from nekozee.filters import command
from nekozee.handlers import MessageHandler

from bot import bot, LOGGER
from ..helper.ext_utils.bot_utils import (
    new_task,
    sync_to_async
)
from ..helper.ext_utils.links_utils import is_gdrive_link
from ..helper.task_utils.gdrive_utils.delete import GoogleDriveDelete
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    anno_checker,
    auto_delete_message,
    send_message
)


@new_task
async def delete_file(_, message):
    args = message.text.split()
    from_user = message.from_user
    if not from_user:
        from_user = await anno_checker(message)
    if len(args) > 1:
        link = args[1]
    elif reply_to := message.reply_to_message:
        link = reply_to.text.split(maxsplit=1)[0].strip()
    else:
        link = ""
    if is_gdrive_link(link):
        LOGGER.info(link)
        msg = await sync_to_async(
            GoogleDriveDelete().delete_file,
            link,
            from_user.id
        )
    else:
        msg = (
            "Send Gdrive link along with command or by replying to the link by command"
        )
    reply_message = await send_message(
        message,
        msg
    )
    await auto_delete_message(
        message,
        reply_message
    )


bot.add_handler( # type: ignore
    MessageHandler(
        delete_file,
        filters=command(
            BotCommands.DeleteCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
