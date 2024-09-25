from nekozee.filters import command
from nekozee.handlers import MessageHandler

from bot import (
    bot,
    config_dict
)
from ..helper.ext_utils.links_utils import (
    is_magnet,
    is_url
)
from ..helper.ext_utils.db_handler import database
from ..helper.z_utils import extract_link
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import send_message


async def remove_all_tokens(_, message):
    if config_dict["DATABASE_URL"]:
        await database.delete_all_access_tokens()
        msg = "All access tokens have been removed from the database."
    else:
        msg = "Database URL not added."
    return await send_message(
        message,
        msg
    )


async def remove_specific_task(_, message):
    if (
        config_dict["DATABASE_URL"]
        and not config_dict["STOP_DUPLICATE_TASKS"]
    ):
        return await send_message(
            message,
            "STOP_DUPLICATE_TASKS feature is not enabled"
        )
    mesg = message.text.split("\n")
    message_args = mesg[0].split(
        " ",
        maxsplit=1
    )
    file = None
    should_delete = False
    try:
        link = message_args[1]
    except IndexError:
        link = ""
    if reply_to := message.reply_to_message:
        media_array = [
            reply_to.document,
            reply_to.photo,
            reply_to.video,
            reply_to.audio,
            reply_to.voice,
            reply_to.video_note,
            reply_to.sticker,
            reply_to.animation
        ]
        file = next(
            (
                i
                for i
                in media_array
                if i
            ),
            None
        )
        if (
            not is_url(link)
            and not is_magnet(link)
            and not link
        ):
            if not file:
                if (
                    is_url(reply_to.text) or
                    is_magnet(reply_to.text)
                ):
                    link = reply_to.text.strip()
                else:
                    mesg = message.text.split("\n")
                    message_args = mesg[0].split(
                        " ",
                        maxsplit=1
                    )
                    try:
                        link = message_args[1]
                    except IndexError:
                        pass
            elif file.mime_type == "application/x-bittorrent":
                link = await reply_to.download()
                should_delete = True
            else:
                link = file.file_unique_id
    if not link:
        msg = "Something went wrong!!"
        return await send_message(
            message,
            msg
        )
    raw_url = await extract_link(
        link,
        should_delete
    )
    if exist := await database.check_download(raw_url):
        await database.remove_download(exist["_id"])
        msg = "Download is removed from database successfully"
        msg += f"\n{exist["tag"]} Your download is removed."
    else:
        msg = "This download is not exists in database"
    return await send_message(
        message,
        msg
    )


if config_dict["DATABASE_URL"]:
    bot.add_handler( # type: ignore
        MessageHandler(
            remove_specific_task,
            filters=command(
                BotCommands.RmdbCommand,
                case_sensitive=True
            ) & CustomFilters.sudo
        )
    )
    bot.add_handler( # type: ignore
        MessageHandler(
            remove_all_tokens,
            filters=command(
                BotCommands.RmalltokensCommand,
                case_sensitive=True
            ) & CustomFilters.sudo
        )
    )
