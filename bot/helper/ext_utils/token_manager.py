from time import time
from uuid import uuid4

from bot import (
    bot,
    bot_name,
    config_dict,
    DATABASE_URL,
    user_data,
)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.ext_utils.shortener import short_url
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage

from pyrogram.filters import command
from pyrogram.handlers import MessageHandler


async def checking_access(user_id, button=None):
    if not config_dict["TOKEN_TIMEOUT"]:
        return None, button
    user_data.setdefault(user_id, {})
    data = user_data[user_id]
    if DATABASE_URL:
        data["time"] = await DbManager().get_token_expire_time(user_id)
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
        if expire is not None:
            del data["time"]
        data["token"] = token
        if DATABASE_URL:
            await DbManager().update_user_token(
                user_id,
                token
            )
        user_data[user_id].update(data)
        if button is None:
            button = ButtonMaker()
        button.ubutton(
            "Get New Token",
            short_url(f"https://telegram.me/{bot_name}?start={token}")
        )
        tmsg = "Your <b>Token</b> is expired. Get a new one."
        tmsg += f"\n<b>Token Validity</b>: {get_readable_time(config_dict["TOKEN_TIMEOUT"])}"
        return (
            tmsg,
            button
        )
    return (
        None,
        button
    )


async def start(client, message):
    if (
        len(message.command) > 1
        and len(message.command[1]) == 36
    ):
        userid = message.from_user.id
        input_token = message.command[1]
        if DATABASE_URL:
            stored_token = await DbManager().get_user_token(userid)
            if stored_token is None:
                return await sendMessage(
                    message,
                    "This token is not associated with your account.\n\nPlease generate your own token."
                )
            if input_token != stored_token:
                return await sendMessage(
                    message,
                    "Invalid token.\n\nPlease generate a new one."
                )
        if userid not in user_data:
            return await sendMessage(
                message,
                "This token is not yours!\n\nKindly generate your own."
            )
        data = user_data[userid]
        if (
            "token" not in data
            or data["token"] != input_token
        ):
            return await sendMessage(
                message,
                "Token already used!\n\nKindly generate a new one."
            )
        token = str(uuid4())
        ttime = time()
        data["token"] = token
        data["time"] = ttime
        user_data[userid].update(data)
        if DATABASE_URL:
            await DbManager().update_user_tdata(
                userid,
                token,
                ttime
            )
        msg = "Token refreshed successfully!\n\n"
        msg += f"Validity: {get_readable_time(int(config_dict["TOKEN_TIMEOUT"]))}"
        return await sendMessage(
            message,
            msg
        )
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
        and not await CustomFilters.authorized(client, message)
    ):
        start_string = "Sorry, you cannot use me here!\n" \
                       "Join: @Z_Mirror to use me.\n" \
                       "Thank You!"
    elif (
        not config_dict["DM_MODE"]
        and message.chat.type != message.chat.type.SUPERGROUP
        and await CustomFilters.authorized(client, message)
    ):
        start_string = "There's nothing to Start here.\n" \
                       "Try something else or read HELP"
    else:
        tag = message.from_user.mention
        start_string = "Start me in DM, not in the group.\n" \
                       f"cc: {tag}"
    await sendMessage(
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
