from nekozee.filters import regex
from nekozee.handlers import CallbackQueryHandler

from bot import (
    bot,
    cached_dict
)
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    is_admin
)


async def verify_annon(_, query):
    message = query.message
    data = query.data.split()
    msg_id = int(data[2])
    if msg_id not in cached_dict:
        return await edit_message(
            message,
            "<b>Old Verification Message</b>"
        )
    user = query.from_user
    if_admin = await is_admin(
        message,
        user.id
    )
    if (
        data[1] == "admin"
        and if_admin
    ):
        await query.answer(f"Username: {user.username}\nYour userid : {user.id}")
        cached_dict[msg_id] = user
        await delete_message(message)
    elif data[1] == "admin":
        await query.answer("You are not an admin")
    else:
        await query.answer()
        await edit_message(
            message,
            "<b>Cancel Verification</b>"
        )

bot.add_handler( # type: ignore
    CallbackQueryHandler(
        verify_annon,
        filters=regex(
            "^verify"
        )
    )
)
