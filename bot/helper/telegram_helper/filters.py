from nekozee.filters import create

from bot import (
    config_dict,
    user_data
)


class CustomFilters:
    async def ownerFilter(self, _, update):
        user = (
            update.from_user or
            update.sender_chat
        )
        uid = user.id
        return uid == config_dict["OWNER_ID"]

    owner = create(ownerFilter)

    async def authorizedUser(self, _, update):
        user = (
            update.from_user or
            update.sender_chat
        )
        uid = user.id
        chat_id = update.chat.id
        return bool(
            uid == config_dict["OWNER_ID"]
            or (
                uid in user_data
                and (
                    user_data[uid].get(
                        "is_auth",
                        False
                    )
                    or user_data[uid].get(
                        "is_sudo",
                        False
                    )
                )
            )
            or (
                chat_id in user_data
                and user_data[chat_id].get(
                    "is_auth",
                    False
                )
            )
        )

    authorized = create(authorizedUser)

    async def sudoUser(self, _, update):
        user = (
            update.from_user or
            update.sender_chat
        )
        uid = user.id
        return bool(
            uid == config_dict["OWNER_ID"]
            or uid in user_data
            and user_data[uid].get("is_sudo")
        )

    sudo = create(sudoUser)
