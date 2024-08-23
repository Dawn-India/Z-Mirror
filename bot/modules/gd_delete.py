from nekozee.filters import command
from nekozee.handlers import MessageHandler

from bot import bot, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.links_utils import is_gdrive_link
from bot.helper.task_utils.gdrive_utils.delete import gdDelete
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    anno_checker,
    auto_delete_message,
    sendMessage
)


async def deletefile(_, message):
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
            gdDelete().deletefile,
            link,
            from_user.id
        )
    else:
        msg = (
            "Send Gdrive link along with command or by replying to the link by command"
        )
    reply_message = await sendMessage(
        message,
        msg
    )
    await auto_delete_message(
        message,
        reply_message
    )


bot.add_handler( # type: ignore
    MessageHandler(
        deletefile,
        filters=command(
            BotCommands.DeleteCommand,
            case_sensitive=True
        ) & CustomFilters.authorized,
    )
)
