from asyncio import (
    sleep,
    create_task,
)
from nekozee.errors import (
    FloodWait,
    PeerIdInvalid,
    RPCError,
    UserNotParticipant,
)
from nekozee.types import ChatPermissions
from nekozee.enums import ChatAction
from re import match as re_match
from time import time
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from bot import (
    bot,
    bot_name,
    cached_dict,
    config_dict,
    Intervals,
    LOGGER,
    status_dict,
    task_dict_lock,
    user,
)
from bot.helper.ext_utils.bot_utils import setInterval
from bot.helper.ext_utils.exceptions import TgLinkException
from bot.helper.ext_utils.status_utils import get_readable_message
from bot.helper.telegram_helper.button_build import ButtonMaker


async def sendMessage(message, text, buttons=None, block=True):
    try:
        return await message.reply(
            text=text,
            quote=True,
            disable_web_page_preview=True,
            disable_notification=True,
            reply_markup=buttons,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        if block:
            await sleep(f.value * 1.2) # type: ignore
            return await sendMessage(
                message,
                text,
                buttons
            )
        return str(f)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def editMessage(message, text, buttons=None, block=True):
    try:
        await message.edit(
            text=text,
            disable_web_page_preview=True,
            reply_markup=buttons
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        if block:
            await sleep(f.value * 1.2) # type: ignore
            return await editMessage(
                message,
                text,
                buttons
            )
        return str(f)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendFile(message, file, caption=""):
    try:
        return await message.reply_document(
            document=file,
            quote=True,
            caption=caption,
            disable_notification=True
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2) # type: ignore
        return await sendFile(
            message,
            file,
            caption
        )
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendRss(text):
    try:
        app = user or bot
        return await app.send_message( # type: ignore
            chat_id=config_dict["RSS_CHAT"],
            text=text,
            disable_web_page_preview=True,
            disable_notification=True,
        )
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2) # type: ignore
        return await sendRss(text)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def deleteMessage(message):
    try:
        await message.delete()
    except Exception as e:
        LOGGER.error(str(e))


async def auto_delete_message(
        cmd_message=None,
        bot_message=None
    ):
    if (config_dict["DELETE_LINKS"]
        and int(config_dict["AUTO_DELETE_MESSAGE_DURATION"])
    ) > 0:
        async def delete_delay():
            await sleep(config_dict["AUTO_DELETE_MESSAGE_DURATION"])
            if cmd_message is not None:
                await deleteMessage(cmd_message)
            if bot_message is not None:
                await deleteMessage(bot_message)
        create_task(delete_delay())


async def delete_links(message):
    if config_dict["DELETE_LINKS"]:
        if reply_to := message.reply_to_message:
            await deleteMessage(reply_to)
        await deleteMessage(message)


async def delete_status():
    async with task_dict_lock:
        for key, data in list(status_dict.items()):
            try:
                await deleteMessage(data["message"])
                del status_dict[key]
            except Exception as e:
                LOGGER.error(str(e))


async def get_tg_link_message(link):
    message = None
    links = []
    if link.startswith("https://t.me/"):
        private = False
        msg = re_match(
            r"https:\/\/t\.me\/(?:c\/)?([^\/]+)(?:\/[^\/]+)?\/([0-9-]+)",
            link
        )
    else:
        private = True
        msg = re_match(
            r"tg:\/\/openmessage\?user_id=([0-9]+)&message_id=([0-9-]+)",
            link
        )
        if not user:
            raise TgLinkException("USER_SESSION_STRING required for this private link!")

    chat = msg[1] # type: ignore
    msg_id = msg[2] # type: ignore
    if "-" in msg_id:
        start_id, end_id = msg_id.split("-")
        msg_id = start_id = int(start_id)
        end_id = int(end_id)
        btw = end_id - start_id
        if private:
            link = link.split("&message_id=")[0]
            links.append(f"{link}&message_id={start_id}")
            for _ in range(btw):
                start_id += 1
                links.append(f"{link}&message_id={start_id}")
        else:
            link = link.rsplit("/", 1)[0]
            links.append(f"{link}/{start_id}")
            for _ in range(btw):
                start_id += 1
                links.append(f"{link}/{start_id}")
    else:
        msg_id = int(msg_id)

    if chat.isdigit():
        chat = (
            int(chat)
            if private
            else int(f"-100{chat}")
        )

    if not private:
        try:
            message = await bot.get_messages( # type: ignore
                chat_id=chat,
                message_ids=msg_id
            )
            if message.empty:
                private = True
        except Exception as e:
            private = True
            if not user:
                raise e

    if not private:
        return (
            (
                links,
                "bot"
            )
            if links
            else (
                message,
                "bot"
            )
        )
    elif user:
        try:
            user_message = await user.get_messages(
                chat_id=chat,
                message_ids=msg_id
            ) # type: ignore
        except Exception as e:
            raise TgLinkException(
                f"I don't have access to this chat!. ERROR: {e}"
            ) from e
        if not user_message.empty:
            return (
                (
                    links,
                    "user"
                )
                if links
                else (
                    user_message,
                    "user"
                )
            )
    else:
        raise TgLinkException("Private: Please report!")


async def update_status_message(sid, force=False):
    if Intervals["stopAll"]:
        return
    async with task_dict_lock:
        if not status_dict.get(sid):
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
            return
        if not force and time() - status_dict[sid]["time"] < 3:
            return
        status_dict[sid]["time"] = time()
        page_no = status_dict[sid]["page_no"]
        status = status_dict[sid]["status"]
        is_user = status_dict[sid]["is_user"]
        page_step = status_dict[sid]["page_step"]
        text, buttons = await get_readable_message(
            sid,
            is_user,
            page_no,
            status,
            page_step
        )
        if text is None:
            del status_dict[sid]
            if obj := Intervals["status"].get(sid):
                obj.cancel()
                del Intervals["status"][sid]
            return
        if text != status_dict[sid]["message"].text:
            message = await editMessage(
                status_dict[sid]["message"],
                text,
                buttons,
                block=False
            ) # type: ignore
            if isinstance(message, str):
                if message.startswith("Telegram says: [400"):
                    del status_dict[sid]
                    if obj := Intervals["status"].get(sid):
                        obj.cancel()
                        del Intervals["status"][sid]
                else:
                    LOGGER.error(
                        f"Status with id: {sid} haven't been updated. Error: {message}"
                    )
                return
            status_dict[sid]["message"].text = text
            status_dict[sid]["time"] = time()


async def sendStatusMessage(msg, user_id=0):
    if Intervals["stopAll"]:
        return
    async with task_dict_lock:
        sid = user_id or msg.chat.id
        is_user = bool(user_id)
        if sid in list(status_dict.keys()):
            page_no = status_dict[sid]["page_no"]
            status = status_dict[sid]["status"]
            page_step = status_dict[sid]["page_step"]
            text, buttons = await get_readable_message(
                sid,
                is_user,
                page_no,
                status,
                page_step
            )
            if text is None:
                del status_dict[sid]
                if obj := Intervals["status"].get(sid):
                    obj.cancel()
                    del Intervals["status"][sid]
                return
            message = status_dict[sid]["message"]
            await deleteMessage(message)
            message = await sendMessage(
                msg,
                text,
                buttons,
                block=False
            )
            if isinstance(message, str):
                LOGGER.error(
                    f"Status with id: {sid} haven't been sent. Error: {message}"
                )
                return
            message.text = text
            status_dict[sid].update({
                "message": message,
                "time": time()
            })
        else:
            (
                text,
                buttons
            ) = await get_readable_message(
                sid,
                is_user
            )
            if text is None:
                return
            message = await sendMessage(
                msg,
                text,
                buttons,
                block=False
            )
            if isinstance(message, str):
                LOGGER.error(
                    f"Status with id: {sid} haven't been sent. Error: {message}"
                )
                return
            message.text = text
            status_dict[sid] = {
                "message": message,
                "time": time(),
                "page_no": 1,
                "page_step": 1,
                "status": "All",
                "is_user": is_user,
            }
    if (
        not Intervals["status"].get(sid)
        and not is_user
    ):
        Intervals["status"][sid] = setInterval(
            config_dict["STATUS_UPDATE_INTERVAL"],
            update_status_message,
            sid
        )

async def user_info(client, userId):
    return await client.get_users(userId)


async def isBot_canDm(message, dmMode, button=None):
    if not dmMode:
        return None, button
    await user_info(
        message._client,
        message.from_user.id
    )
    try:
        await message._client.send_chat_action(
            message.from_user.id,
            ChatAction.TYPING
        )
    except Exception:
        if button is None:
            button = ButtonMaker()
        _msg = "You need to <b>Start</b> me in <b>DM</b>."
        button.ubutton(
            "ꜱᴛᴀʀᴛ\nᴍᴇ",
            f"https://t.me/{bot_name}?start=start",
            "header"
        )
        return (
            _msg,
            button
        )
    return (
        "BotStarted",
        button
    )


async def send_to_chat(client, chatId, text, buttons=None):
    try:
        return await client.send_message(
            chatId,
            text=text,
            disable_web_page_preview=True,
            disable_notification=True,
            reply_markup=buttons
        )
    except FloodWait as f:
        LOGGER.error(f"{f.NAME}: {f.MESSAGE}")
        await sleep(f.value * 1.2) # type: ignore
        return await send_to_chat(
            client,
            chatId,
            text,
            buttons
        )
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))


async def sendLogMessage(message, link, tag):
    if not (log_chat := config_dict["LOG_CHAT_ID"]):
        return
    try:
        isSuperGroup = message.chat.type in [
            message.chat.type.SUPERGROUP,
            message.chat.type.CHANNEL
        ]
        if reply_to := message.reply_to_message:
            if not reply_to.text:
                caption = ""
                if isSuperGroup and not config_dict["DELETE_LINKS"]:
                    caption+=f"<b><a href='{message.link}'>Source</a></b> | "
                caption+=f"<b>Added by</b>: {tag}\n<b>User ID</b>: <code>{message.from_user.id}</code>"
                return await reply_to.copy(
                    log_chat,
                    caption=caption
                )
        msg = ""
        if isSuperGroup and not config_dict["DELETE_LINKS"]:
            msg+=f"\n\n<b><a href='{message.link}'>Source Link</a></b>: "
        msg += f"<code>{link}</code>\n\n<b>Added by</b>: {tag}\n"
        msg += f"<b>User ID</b>: <code>{message.from_user.id}</code>"
        return await message._client.send_message(
            log_chat,
            msg,
            disable_web_page_preview=True
        )
    except FloodWait as r:
        LOGGER.warning(str(r))
        await sleep(r.value * 1.2) # type: ignore
        return await sendLogMessage(
            message,
            link,
            tag
        )
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))


async def isAdmin(message, user_id=None):
    if message.chat.type == message.chat.type.PRIVATE:
        return
    if user_id:
        member = await message.chat.get_member(user_id)
    else:
        member = await message.chat.get_member(message.from_user.id)
    return member.status in [
        member.status.ADMINISTRATOR,
        member.status.OWNER
    ]


async def forcesub(message, ids, button=None):
    join_button = {}
    _msg = ""
    for channel_id in ids.split():
        if channel_id.startswith("-100"):
            channel_id = int(channel_id)
        elif channel_id.startswith("@"):
            channel_id = channel_id.replace("@", "")
        else:
            continue
        try:
            chat = await message._client.get_chat(channel_id)
        except (PeerIdInvalid, RPCError) as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}. Mostly I'm not added in the channel as admin.")
            continue
        try:
            await chat.get_member(message.from_user.id)
        except UserNotParticipant:
            if username := chat.username:
                invite_link = f"https://t.me/{username}"
            else:
                invite_link = chat.invite_link
            join_button[chat.title] = invite_link
        except RPCError as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        except Exception as e:
            LOGGER.error(f"{e} for {channel_id}")
    if join_button:
        if button is None:
            button = ButtonMaker()
        _msg = f"You need to join our channel to use me."
        for (
            key,
            value
        ) in join_button.items():
            button.ubutton(
                f"{key}",
                value,
                "footer"
            )
    return (
        _msg,
        button
    )


async def message_filter(message):
    if not config_dict["ENABLE_MESSAGE_FILTER"]:
        return
    _msg = ""
    if reply_to := message.reply_to_message:
        if reply_to.forward_date:
            await deleteMessage(reply_to)
            _msg = "You can't mirror or leech forward messages."
        elif reply_to.reply_markup:
            await deleteMessage(reply_to)
            _msg = "You can't mirror or leech messages with buttons."
        elif reply_to.caption:
            await deleteMessage(reply_to)
            _msg = "You can't mirror or leech with captions text."
    elif message.reply_markup:
        await deleteMessage(message)
        _msg = "You can't mirror or leech messages with buttons."
    elif message.forward_date:
        await deleteMessage(message)
        _msg = "You can't mirror or leech forward messages."
    if _msg:
        message.id = None
        return _msg


async def anno_checker(message, pmsg=None):
    msg_id = message.id
    buttons = ButtonMaker()
    buttons.ibutton(
        "ᴠᴇʀɪꜰʏ",
        f"verify admin {msg_id}"
    )
    buttons.ibutton(
        "ᴄᴀɴᴄᴇʟ",
        f"verify no {msg_id}"
    )
    user = None
    cached_dict[msg_id] = user
    if pmsg is not None:
        await editMessage(
            pmsg,
            f"{message.sender_chat.type.name} Anon Verification",
            buttons.build_menu(2)
        )
    else:
        await sendMessage(
            message,
            f"{message.sender_chat.type.name} Anon Verification",
            buttons.build_menu(2)
        )
    start_time = time()
    while time() - start_time <= 7:
        await sleep(0.5)
        if cached_dict[msg_id]:
            break
    user = cached_dict[msg_id]
    del cached_dict[msg_id]
    return user


async def mute_member(message, userid, until=60):
    try:
        await message.chat.restrict_member(
            userid,
            ChatPermissions(),
            datetime.now(timezone.utc) + timedelta(seconds=until)
        )
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(f"Exception while muting member {e}")


warned_users = {}
async def request_limiter(message=None, query=None):
    if not (LIMITS := config_dict["REQUEST_LIMITS"]):
        return
    if not message:
        if not query:
            return
        message = query.message
    if message.chat.type == message.chat.type.PRIVATE:
        return
    userid = (
        query.from_user.id
        if query
        else message.from_user.id
    )
    current_time = time()
    if userid in warned_users:
        time_between = current_time - warned_users[userid]["time"]
        if time_between > 69:
            warned_users[userid]["warn"] = 0
        elif time_between < 3:
            warned_users[userid]["warn"] += 1
    else:
        warned_users[userid] = {"warn": 0}
    warned_users[userid]["time"] = current_time
    if warned_users[userid]["warn"] >= LIMITS+1:
        return True
    if warned_users[userid]["warn"] >= LIMITS:
        await mute_member(message, userid)
        return True
    if warned_users[userid]["warn"] >= LIMITS-1:
        if query:
            await query.answer(
                "Oops, Spam detected! I will mute you for 69 seconds.",
                show_alert=True
            )
        else:
            m69 = await sendMessage(
                message,
                "Oops, Spam detected! I will mute you for 69 seconds."
            )
            await auto_delete_message(
                message,
                m69
            )
