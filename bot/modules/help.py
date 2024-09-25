from nekozee.filters import regex
from nekozee.handlers import CallbackQueryHandler

from bot import bot
from ..helper.ext_utils.bot_utils import (
    COMMAND_USAGE,
    new_task
)
from ..helper.ext_utils.help_messages import (
    YT_HELP_DICT,
    MIRROR_HELP_DICT,
    CLONE_HELP_DICT,
)
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    edit_message,
    delete_message,
    delete_links
)


@new_task
async def arg_usage(_, query):
    data = query.data.split()
    message = query.message
    if data[1] == "close":
        await delete_links(message)
        await delete_message(message)
    elif data[1] == "back":
        if data[2] == "m":
            await edit_message(
                message,
                COMMAND_USAGE["mirror"][0],
                COMMAND_USAGE["mirror"][1]
            )
        elif data[2] == "y":
            await edit_message(
                message,
                COMMAND_USAGE["yt"][0],
                COMMAND_USAGE["yt"][1]
            )
        elif data[2] == "c":
            await edit_message(
                message,
                COMMAND_USAGE["clone"][0],
                COMMAND_USAGE["clone"][1]
            )
    elif data[1] == "mirror":
        buttons = ButtonMaker()
        buttons.data_button(
            "ʙᴀᴄᴋ",
            "help back m"
        )
        button = buttons.build_menu()
        await edit_message(
            message,
            MIRROR_HELP_DICT[data[2] + "\n" + data[3]],
            button
        )
    elif data[1] == "yt":
        buttons = ButtonMaker()
        buttons.data_button(
            "ʙᴀᴄᴋ",
            "help back y"
        )
        button = buttons.build_menu()
        await edit_message(
            message,
            YT_HELP_DICT[data[2] + "\n" + data[3]],
            button
        )
    elif data[1] == "clone":
        buttons = ButtonMaker()
        buttons.data_button(
            "ʙᴀᴄᴋ",
            "help back c"
        )
        button = buttons.build_menu()
        await edit_message(
            message,
            CLONE_HELP_DICT[data[2] + "\n" + data[3]],
            button
        )


bot.add_handler( # type: ignore
    CallbackQueryHandler(
        arg_usage,
        filters=regex("^help")
    )
)
