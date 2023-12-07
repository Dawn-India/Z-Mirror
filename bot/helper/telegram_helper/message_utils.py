#!/usr/bin/env python3
from asyncio import sleep, create_task
from datetime import datetime, timedelta, timezone
from time import time
from re import match as re_match

from pyrogram.errors import (FloodWait, PeerIdInvalid, RPCError, UserNotParticipant)
from pyrogram.types import ChatPermissions

from bot import (LOGGER, Interval, bot, bot_name, cached_dict, categories_dict,
                 config_dict, download_dict_lock, status_reply_dict,
                 status_reply_dict_lock, user)
from bot.helper.ext_utils.bot_utils import get_readable_message, setInterval, sync_to_async
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.exceptions import TgLinkException


async def sendMessage(message, text, buttons=None):
    try:
        return await message.reply(text=text, quote=True, disable_web_page_preview=True,
                                   disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendMessage(message, text, buttons)
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))


async def editMessage(message, text, buttons=None):
    try:
        await message.edit(text=text, disable_web_page_preview=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await editMessage(message, text, buttons)
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendFile(message, file, caption=None):
    try:
        return await message.reply_document(document=file, quote=True, caption=caption, disable_notification=True)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendFile(message, file, caption)
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendRss(text):
    try:
        if user:
            return await user.send_message(chat_id=config_dict['RSS_CHAT_ID'], text=text, disable_web_page_preview=True,
                                           disable_notification=True)
        else:
            return await bot.send_message(chat_id=config_dict['RSS_CHAT_ID'], text=text, disable_web_page_preview=True,
                                          disable_notification=True)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendRss(text)
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))


async def deleteMessage(message):
    try:
        await message.delete()
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))


async def auto_delete_message(cmd_message=None, bot_message=None):
    if config_dict['DELETE_LINKS'] and int(config_dict['AUTO_DELETE_MESSAGE_DURATION']) > 0:
        async def delete_delay():
            await sleep(config_dict['AUTO_DELETE_MESSAGE_DURATION'])
            if cmd_message is not None:
                await deleteMessage(cmd_message)
            if bot_message is not None:
                await deleteMessage(bot_message)
        create_task(delete_delay())


async def delete_all_messages():
    async with status_reply_dict_lock:
        for key, data in list(status_reply_dict.items()):
            try:
                del status_reply_dict[key]
                await deleteMessage(data[0])
            except Exception as e:
                LOGGER.error(str(e))


async def delete_links(message):
    if config_dict['DELETE_LINKS']:
        if reply_to := message.reply_to_message:
            await deleteMessage(reply_to)
        await deleteMessage(message)


async def get_tg_link_content(link):
    message = None
    if link.startswith('https://t.me/'):
        private = False
        msg = re_match(r"https:\/\/t\.me\/(?:c\/)?([^\/]+)(?:\/[^\/]+)?\/([0-9]+)", link)
    else:
        private = True
        msg = re_match(
            r"tg:\/\/openmessage\?user_id=([0-9]+)&message_id=([0-9]+)", link)
        if not user:
            raise TgLinkException('USER_SESSION_STRING required for this private link!')

    chat = msg.group(1)
    msg_id = int(msg.group(2))
    if chat.isdigit():
        chat = int(chat) if private else int(f'-100{chat}')

    if not private:
        try:
            message = await bot.get_messages(chat_id=chat, message_ids=msg_id)
            if message.empty:
                private = True
        except Exception as e:
            private = True
            if not user:
                raise e

    if private and user:
        try:
            user_message = await user.get_messages(chat_id=chat, message_ids=msg_id)
        except Exception as e:
            raise TgLinkException(f"I don't have access to that chat!\nAdd me there first. ERROR: {e}") from e
        if not user_message.empty:
            return user_message, 'user'
        else:
            raise TgLinkException("Private: Please report!")
    elif not private:
        return message, 'bot'
    else:
        raise TgLinkException("Bot can't download from GROUPS without joining!")


async def update_all_messages(force=False):
    async with status_reply_dict_lock:
        if not status_reply_dict or not Interval or (not force and time() - list(status_reply_dict.values())[0][1] < 3):
            return
        for chat_id in list(status_reply_dict.keys()):
            status_reply_dict[chat_id][1] = time()
    async with download_dict_lock:
        msg, buttons = await sync_to_async(get_readable_message)
    if msg is None:
        return
    async with status_reply_dict_lock:
        for chat_id in list(status_reply_dict.keys()):
            if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id][0].text:
                rmsg = await editMessage(status_reply_dict[chat_id][0], msg, buttons)
                if isinstance(rmsg, str) and rmsg.startswith('Telegram says: [400'):
                    del status_reply_dict[chat_id]
                    continue
                status_reply_dict[chat_id][0].text = msg
                status_reply_dict[chat_id][1] = time()


async def sendStatusMessage(msg):
    async with download_dict_lock:
        progress, buttons = await sync_to_async(get_readable_message)
    if progress is None:
        return
    async with status_reply_dict_lock:
        chat_id = msg.chat.id
        if chat_id in list(status_reply_dict.keys()):
            message = status_reply_dict[chat_id][0]
            await deleteMessage(message)
            del status_reply_dict[chat_id]
        message = await sendMessage(msg, progress, buttons)
        message.text = progress
        status_reply_dict[chat_id] = [message, time()]
        if not Interval:
            Interval.append(setInterval(config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))


async def user_info(client, userId):
    return await client.get_users(userId)


async def isBot_canDm(message, dmMode, isLeech=False, button=None):
    if dmMode not in ['leech', 'mirror', 'all']:
        return None, button
    if dmMode == 'mirror' and isLeech:
        return None, button
    if dmMode == 'leech' and not isLeech:
        return None, button
    user = await user_info(message._client, message.from_user.id)
    try:
        dm_check = await message._client.send_message(message.from_user.id, "Your task added to download.")
        await dm_check.delete()
    except Exception as e:
        if button is None:
            button = ButtonMaker()
        _msg = "You need to <b>Start</b> me in <b>DM</b>."
        button.ubutton("Start Me", f"https://t.me/{bot_name}?start=start", 'header')
        return _msg, button
    return 'BotStarted', button


async def send_to_chat(client, chatId, text, buttons=None):
    try:
        return await client.send_message(chatId, text=text, disable_web_page_preview=True,
                                         disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.error(f"{f.NAME}: {f.MESSAGE}")
        await sleep(f.value * 1.2)
        return await send_to_chat(client, chatId, text, buttons)
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))


async def sendLogMessage(message, link, tag):
    if not (log_chat := config_dict['LOG_CHAT_ID']):
        return
    try:
        isSuperGroup = message.chat.type in [
            message.chat.type.SUPERGROUP, message.chat.type.CHANNEL]
        if reply_to := message.reply_to_message:
            if not reply_to.text:
                caption = ''
                if isSuperGroup:
                    caption+=f'<b><a href="{message.link}">Source</a></b> | '
                caption+=f'<b>Added by</b>: {tag}\n<b>User ID</b>: <code>{message.from_user.id}</code>'
                return await reply_to.copy(log_chat, caption=caption)
        msg = ''
        if isSuperGroup:
            msg+=f'\n\n<b><a href="{message.link}">Source Link</a></b>: '
        msg += f'<code>{link}</code>\n\n<b>Added by</b>: {tag}\n'
        msg += f'<b>User ID</b>: <code>{message.from_user.id}</code>'
        return await message._client.send_message(log_chat, msg, disable_web_page_preview=True)
    except FloodWait as r:
        LOGGER.warning(str(r))
        await sleep(r.value * 1.2)
        return await sendLogMessage(message, link, tag)
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
    return member.status in [member.status.ADMINISTRATOR, member.status.OWNER]


async def forcesub(message, ids, button=None):
    join_button = {}
    _msg = ''
    for channel_id in ids.split():
        if channel_id.startswith('-100'):
            channel_id = int(channel_id)
        elif channel_id.startswith('@'):
            channel_id = channel_id.replace('@', '')
        else:
            continue
        try:
            chat = await message._client.get_chat(channel_id)
        except PeerIdInvalid as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
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
            LOGGER.error(f'{e} for {channel_id}')
    if join_button:
        if button is None:
            button = ButtonMaker()
        _msg = f"You need to join our channel to use me."
        for key, value in join_button.items():
            button.ubutton(f'{key}', value, 'footer')
    return _msg, button


async def message_filter(message):
    if not config_dict['ENABLE_MESSAGE_FILTER']:
        return
    _msg = ''
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


async def anno_checker(message):
    msg_id = message.id
    buttons = ButtonMaker()
    buttons.ibutton('Verify', f'verify admin {msg_id}')
    buttons.ibutton('Cancel', f'verify no {msg_id}')
    user = None
    cached_dict[msg_id] = user
    await sendMessage(message, f'{message.sender_chat.type.name} Verification\nIf you hit Verify! Your username and id will expose in bot logs!', buttons.build_menu(2))
    start_time = time()
    while time() - start_time <= 7:
        await sleep(0.5)
        if cached_dict[msg_id]:
            break
    user = cached_dict[msg_id]
    del cached_dict[msg_id]
    return user


async def open_category_btns(message):
    user_id = message.from_user.id
    msg_id = message.id
    buttons = ButtonMaker()
    for _name in categories_dict.keys():
        buttons.ibutton(f'{_name}', f'scat {user_id} {msg_id} {_name}')
    msg = f'<b>Select where you want to upload</b>\n\nUser: {message.from_user.mention}'
    prompt = await sendMessage(message, msg, buttons.build_menu(2))
    cached_dict[msg_id] = [None, None]
    start_time = time()
    while time() - start_time <= 30:
        await sleep(0.5)
        if cached_dict[msg_id][0]:
            break
    drive_id = cached_dict[msg_id][0]
    index_link = cached_dict[msg_id][1]
    await deleteMessage(prompt)
    del cached_dict[msg_id]
    return drive_id, index_link


async def mute_member(message, userid, until=60):
    try:
        await message.chat.restrict_member(
            userid,
            ChatPermissions(),
            datetime.now(timezone.utc) + timedelta(seconds=until))
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(f'Exception while muting member {e}')

warned_users = {}


async def request_limiter(message=None, query=None):
    if not (LIMITS := config_dict['REQUEST_LIMITS']):
        return
    if not message:
        if not query:
            return
        message = query.message
    if message.chat.type == message.chat.type.PRIVATE:
        return
    userid = query.from_user.id if query else message.from_user.id
    current_time = time()
    if userid in warned_users:
        time_between = current_time - warned_users[userid]['time']
        if time_between > 69:
            warned_users[userid]['warn'] = 0
        elif time_between < 3:
            warned_users[userid]['warn'] += 1
    else:
        warned_users[userid] = {'warn': 0}
    warned_users[userid]['time'] = current_time
    if warned_users[userid]['warn'] >= LIMITS+1:
        return True
    if warned_users[userid]['warn'] >= LIMITS:
        await mute_member(message, userid)
        return True
    if warned_users[userid]['warn'] >= LIMITS-1:
        if query:
            await query.answer("Oops, Spam detected! I will mute you for 69 seconds.", show_alert=True)
        else:
            await sendMessage(message, "Oops, Spam detected! I will mute you for 69 seconds.")
