from time import time
from uuid import uuid4

from bot import (
    bot,
    bot_name,
    config_dict,
    user_data,
)
from .bot_utils import new_task
from .db_handler import database
from .status_utils import get_readable_time
from .shortener import short_url
from ..telegram_helper.bot_commands import BotCommands
from ..telegram_helper.button_build import ButtonMaker
from ..telegram_helper.filters import CustomFilters
from ..telegram_helper.message_utils import (
    send_message,
    send_log_message
)

from nekozee.filters import command
from nekozee.handlers import MessageHandler


async def checking_access(user_id, button=None):
    if not config_dict["TOKEN_TIMEOUT"]:
        return (
            None,
            button
        )
    user_data.setdefault(
        user_id,
        {}
    )
    data = user_data[user_id]
    if config_dict["DATABASE_URL"]:
        data["time"] = await database.get_token_expire_time(user_id)
    expire = data.get("time")
    isExpired = (
        expire is None
        or expire is not None
        and (time() - expire) > config_dict["TOKEN_TIMEOUT"]
    )
    if isExpired:
        token = (
            data["token"]
            if expire is None
            and "token" in data
            else str(uuid4())
        )
        inittime = time()
        if expire is not None:
            del data["time"]
        data["token"] = token
        data["inittime"] = inittime
        if config_dict["DATABASE_URL"]:
            await database.update_user_token(
                user_id,
                token,
                inittime
            )
        user_data[user_id].update(data)
        if button is None:
            button = ButtonMaker()
        button.url_button(
            "ɢᴇɴᴇʀᴀᴛᴇ\nɴᴇᴡ ᴛᴏᴋᴇɴ",
            short_url(f"https://redirect.z-mirror.eu.org/{bot_name}/{token}")
        )
        tmsg = (
            "You need to generate a new <b>Token</b>."
            f"\n➜ <b>Validity</b>: {get_readable_time(config_dict["TOKEN_TIMEOUT"])}"
        )
        return (
            tmsg,
            button
        )
    return (
        None,
        button
    )


@new_task
async def start(client, message):
    tag = message.from_user.mention
    if (
        len(message.command) > 1
        and len(message.command[1]) == 36
    ):
        userid = message.from_user.id
        input_token = message.command[1]
        if config_dict["DATABASE_URL"]:
            stored_token = await database.get_user_token(userid)
            if stored_token is None:
                return await send_message(
                    message,
                    "This token is not associated with your account.\n\nPlease generate your own token."
                )
            if input_token != stored_token:
                return await send_message(
                    message,
                    "Invalid token.\n\nPlease generate a new one."
                )
            inittime = await database.get_token_init_time(userid)
            duration = time() - inittime # type: ignore
            if (
                config_dict["MINIMUM_DURATOIN"]
                and (
                    duration < config_dict["MINIMUM_DURATOIN"]
                )
            ):
                await database.update_user_tdata(
                    userid,
                    0,
                    0
                )
                await send_log_message(
                    message,
                    f"#BYPASS\n\nShortener bypass detected.",
                    tag
                )
                return await send_message(
                    message,
                    (
                        "Shortener bypass detected.\nPlease generate a new token.\n\n"
                        "<b>Don't try to bypass it, else next time BAN.</b>\n\n"
                        "Don't use any <b>Adblocker</b> or <b>VPN</b> or <b>Proxy</b>\n"
                        "or <b>Incognito</b> or <b>DNS</b> or <b>Extensions</b>\n"
                        "or <b>Any other Bypass methods</b>.\n\nFor your safety and my "
                        "profit, use google chrome browser without any extensions."
                    )
                )
        if userid not in user_data:
            return await send_message(
                message,
                "This token is not yours!\n\nKindly generate your own."
            )
        data = user_data[userid]
        if (
            "token" not in data
            or data["token"] != input_token
        ):
            return await send_message(
                message,
                "Token already used!\n\nKindly generate a new one."
            )
        duration = time() - data["inittime"]
        if (
            config_dict["MINIMUM_DURATOIN"]
            and (
                duration < config_dict["MINIMUM_DURATOIN"]
            )
        ):
            del data["token"]
            await send_log_message(
                message,
                f"#BYPASS\n\nShortener bypass detected.",
                tag
            )
            return await send_message(
                message,
                (
                    "Shortener bypass detected.\nPlease generate a new token.\n\n"
                    "<b>Don't try to bypass it, else next time BAN.</b>\n\n"
                    "Don't use any <b>Adblocker</b> or <b>VPN</b> or <b>Proxy</b>\n"
                    "or <b>Incognito</b> or <b>DNS</b> or <b>Extensions</b>\n"
                    "or <b>Any other Bypass methods</b>.\n\nFor your safety and my"
                    "profit, use telegram's inbuilt browser or chrome without any extensions."
                )
            )
        token = str(uuid4())
        ttime = time()
        data["token"] = token
        data["time"] = ttime
        user_data[userid].update(data)
        if config_dict["DATABASE_URL"]:
            await database.update_user_tdata(
                userid,
                token,
                ttime
            )
        msg = (
            "<b>Your token refreshed successfully!</b>\n"
            f"➜ Validity: {get_readable_time(int(config_dict["TOKEN_TIMEOUT"]))}\n\n"
            "<b>Your Limites:</b>\n"
            f"➜ {config_dict["USER_MAX_TASKS"]} parallal tasks.\n"
        )
        await send_message(
            message,
            msg
        )
        await send_log_message(
            message,
            f"#TOKEN\n\nToken refreshed successfully.",
            tag
        )
        return
    elif (
        config_dict["DM_MODE"]
        and message.chat.type != message.chat.type.SUPERGROUP
    ):
        start_string = "Bot Started.\n" \
                       "Now I will send all of your stuffs here.\n" \
                       "Use me at: @Z_Mirror"
    elif (
        not config_dict["DM_MODE"]
        and message.chat.type != message.chat.type.SUPERGROUP
        and not await CustomFilters.authorized(
            client,
            message
        )
    ):
        start_string = "Sorry, you cannot use me in private!"
    elif (
        not config_dict["DM_MODE"]
        and message.chat.type != message.chat.type.SUPERGROUP
        and await CustomFilters.authorized(
            client,
            message
        )
    ):
        start_string = "There's nothing to Start here.\n" \
                       "Try something else or read HELP"
    else:
        start_string = "Start me in DM, not in the group.\n" \
                       f"cc: {tag}"
    await send_message(
        message,
        start_string
    )


bot.add_handler( # type: ignore
    MessageHandler(
        start,
        filters=command(
            BotCommands.StartCommand
        )
    )
)
