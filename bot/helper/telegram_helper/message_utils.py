from asyncio import sleep
from datetime import datetime, timedelta, timezone
from time import time

from pyrogram.errors import (FloodWait, PeerIdInvalid, RPCError, UserIsBlocked,
                             UserNotParticipant)
from pyrogram.types import ChatPermissions

from bot import (LOGGER, Interval, bot, btn_listener, categories, config_dict,
                 download_dict_lock, status_reply_dict, status_reply_dict_lock,
                 user)
from bot.helper.ext_utils.bot_utils import (get_readable_message, setInterval,
                                            get_readable_file_size, sync_to_async)
from bot.helper.telegram_helper.button_build import ButtonMaker


async def sendMessage(message, text, buttons=None):
    try:
        return await message.reply(text=text, quote=True, disable_web_page_preview=True,
                                   disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.5)
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
        await sleep(f.value * 1.5)
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
        await sleep(f.value * 1.5)
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
        await sleep(f.value * 1.5)
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
    except:
        pass

async def auto_delete_message(cmd_message=None, bot_message=None):
    if config_dict['AUTO_DELETE_MESSAGE_DURATION'] != -1:
        await sleep(config_dict['AUTO_DELETE_MESSAGE_DURATION'])
        if cmd_message is not None:
            await deleteMessage(cmd_message)
        if bot_message is not None:
            await deleteMessage(bot_message)

async def delete_all_messages():
    async with status_reply_dict_lock:
        for key, data in list(status_reply_dict.items()):
            try:
                del status_reply_dict[key]
                await deleteMessage(data[0])
            except Exception as e:
                LOGGER.error(str(e))

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

async def sendDmMessage(message, dmMode, isLeech=False):
    if dmMode not in ['leech', 'mirror', 'all']:
        return
    if dmMode == 'mirror' and isLeech:
        return
    if dmMode == 'leech' and not isLeech:
        return
    try:
        return await message._client.send_message(message.from_user.id, disable_notification=True, text=message.link)
    except FloodWait as r:
        LOGGER.warning(str(r))
        await sleep(r.value * 1.5)
        return sendDmMessage(message, dmMode, isLeech)
    except (UserIsBlocked, PeerIdInvalid) as e:
        buttons = ButtonMaker()
        buttons.ubutton("Start", f"https://t.me/{message._client.me.username}?start=start")
        user = message.from_user.username if message.from_user.username is not None else message.from_user.first_name
        await sendMessage(message, f"Dear <b><i><a href='https://t.me/{user}'>{user}</a>!</i></b>\nYou need to START me in DM. \
\nSo I can send all files there.\n\n<b>Start and try again!</b>\nThank You.", buttons.build_menu(1))
        await delete_links(message)
        return 'BotNotStarted'
    except RPCError as e:
        LOGGER.error(f"{e.NAME}: {e.MESSAGE}")
    except Exception as e:
        LOGGER.error(str(e))

async def sendLogMessage(message, link, tag):
    if not (log_chat := config_dict['LOG_CHAT']):
        return
    try:
        isSuperGroup = message.chat.type in [message.chat.type.SUPERGROUP, message.chat.type.CHANNEL]
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
        msg += f'<code>{link}</code>\n\n<b>Added by</b>: {tag} \
\n<b>User ID</b>: <code>{message.from_user.id}</code>'
        return await message._client.send_message(log_chat, msg, disable_web_page_preview=True)
    except FloodWait as r:
        LOGGER.warning(str(r))
        await sleep(r.value * 1.5)
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

async def forcesub( message, tag):
    if not (FSUB_IDS := config_dict['FSUB_IDS']):
        return
    join_button = {}
    for channel_id in FSUB_IDS.split():
        if channel_id.startswith('-100'):
            channel_id = int(channel_id)
        elif channel_id.startswith('@'):
            channel_id = channel_id.replace('@', '')
        try:
            chat = await message._client.get_chat(channel_id)
        except PeerIdInvalid as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
            continue
        try:
            await chat.get_member(message.from_user.id)
        except UserNotParticipant:
            if username:= chat.username:
                invite_link = f"https://t.me/{username}"
            else:
                invite_link = chat.invite_link
            join_button[chat.title] = invite_link
        except RPCError as e:
            LOGGER.error(f"{e.NAME}: {e.MESSAGE} for {channel_id}")
        except Exception as e:
            LOGGER.error(f'{e} for {channel_id}')
    if join_button:
        await delete_links(message)
        btn = ButtonMaker()
        for key, value in join_button.items():
            btn.ubutton(key, value)
        return await sendMessage(message, f'Dear {tag}!\nPlease join our channel to use me! \
\n\n<b>Join And Try Again!</b>\nThank You.', btn.build_menu(2))

async def message_filter(message, tag):
    if not config_dict['ENABLE_MESSAGE_FILTER']:
        return
    _msg = ''
    if message.reply_to_message:
        if message.reply_to_message.forward_date:
            await deleteMessage(message.reply_to_message)
            _msg = "You can't mirror or leech forward messages to this bot. \
\n\nRemove it and try again\nThank you."
        elif message.reply_to_message.caption:
            await deleteMessage(message.reply_to_message)
            _msg = "You can't mirror or leech with captions text to this bot. \
\n\nRemove it and try again\nThank you."
    elif message.forward_date:
        await deleteMessage(message)
        _msg = "You can't mirror or leech forward messages to this bot. \
\n\nRemove it and try again\nThank you."
    if _msg:
        message.id = None
        return await sendMessage(message, f"{tag} {_msg}")

async def delete_links(message):
    if config_dict['DELETE_LINKS']:
        if reply_to := message.reply_to_message:
            await deleteMessage(reply_to)
        await deleteMessage(message)

async def anno_checker(message):
    msg_id = message.id
    buttons = ButtonMaker()
    buttons.ibutton('Verify', f'verify admin {msg_id}')
    buttons.ibutton('Cancel', f'verify no {msg_id}')
    user = None
    btn_listener[msg_id] = user
    await sendMessage(message, f'{message.sender_chat.type.name} Verification \
\nIf you hit Verify! Your username and id will expose in bot logs!', buttons.build_menu(2))
    start_time = time()
    while time() - start_time <= 7:
        await sleep(0.5)
        if btn_listener[msg_id]:
            break
    user = btn_listener[msg_id]
    del btn_listener[msg_id]
    return user

async def open_category_btns(message):
    user_id = message.from_user.id
    msg_id = message.id
    buttons = ButtonMaker()
    for _name in categories.keys():
        buttons.ibutton(f'{_name}', f'scat {user_id} {msg_id} {_name}')
    prompt = await sendMessage(message,'<b>Select the category \
where you want to upload</b>', buttons.build_menu(2))
    btn_listener[msg_id] = [None, None]
    start_time = time()
    while time() - start_time <= 30:
        await sleep(0.5)
        if btn_listener[msg_id][0]:
            break
    drive_id = btn_listener[msg_id][0]
    index_link = btn_listener[msg_id][1]
    await deleteMessage(prompt)
    del btn_listener[msg_id]
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
    if not (LIMITS :=config_dict['REQUEST_LIMITS']):
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
        warned_users[userid] = {'warn':0}
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
