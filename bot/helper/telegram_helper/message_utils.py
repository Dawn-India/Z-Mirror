from io import BytesIO
from time import sleep, time

from pyrogram.errors import FloodWait
from telegram.error import RetryAfter, Unauthorized

from bot import (LOGGER, Interval, bot, btn_listener, categories, config_dict,
                 rss_session, status_reply_dict, status_reply_dict_lock)
from bot.helper.ext_utils.bot_utils import get_readable_message, setInterval
from bot.helper.telegram_helper.button_build import ButtonMaker


def sendMessage(text, bot, message, reply_markup=None):
    try:
        return bot.sendMessage(message.chat_id, reply_to_message_id=message.message_id,
                               text=text, reply_markup=reply_markup)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return sendMessage(text, bot, message, reply_markup)
    except Exception as e:
        LOGGER.error(str(e))
        return

def sendPhoto(text, bot, message, photo):
    try:
        return bot.sendPhoto(message.chat_id, photo, text, reply_to_message_id=message.message_id)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return sendPhoto(text, bot, message, photo)
    except Exception as e:
        LOGGER.error(str(e))
        return

def editMessage(text, message, reply_markup=None):
    try:
        bot.editMessageText(text=text, message_id=message.message_id, chat_id=message.chat_id, reply_markup=reply_markup)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return editMessage(text, message, reply_markup)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)

def sendRss(text, bot):
    if not rss_session:
        try:
            return bot.sendMessage(config_dict['RSS_CHAT_ID'], text)
        except RetryAfter as r:
            LOGGER.warning(str(r))
            sleep(r.retry_after * 1.5)
            return sendRss(text, bot)
        except Exception as e:
            LOGGER.error(str(e))
            return
    else:
        try:
            with rss_session:
                return rss_session.send_message(config_dict['RSS_CHAT_ID'], text, disable_web_page_preview=True)
        except FloodWait as e:
            LOGGER.warning(str(e))
            sleep(e.value * 1.5)
            return sendRss(text, bot)
        except Exception as e:
            LOGGER.error(str(e))
            return

def deleteMessage(bot, message):
    try:
        bot.deleteMessage(chat_id=message.chat_id, message_id=message.message_id)
    except:
        pass

def sendLogFile(bot, message):
    with open('log.txt', 'rb') as f:
        bot.sendDocument(document=f, filename=f.name,
                          reply_to_message_id=message.message_id,
                          chat_id=message.chat_id)

def sendFile(bot, message, txt, fileName, caption=""):
    try:
        with BytesIO(str.encode(txt)) as document:
            document.name = fileName
            return bot.sendDocument(document=document, reply_to_message_id=message.message_id,
                                    caption=caption, chat_id=message.chat_id)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return sendFile(bot, message, txt, fileName, caption)
    except Exception as e:
        LOGGER.error(str(e))
        return

def auto_delete_message(bot, cmd_message=None, bot_message=None):
    if config_dict['AUTO_DELETE_MESSAGE_DURATION'] != -1:
        sleep(config_dict['AUTO_DELETE_MESSAGE_DURATION'])
        if cmd_message:
            deleteMessage(bot, cmd_message)
        if bot_message:
            deleteMessage(bot, bot_message)

def delete_all_messages():
    with status_reply_dict_lock:
        for data in list(status_reply_dict.values()):
            try:
                deleteMessage(bot, data[0])
                del status_reply_dict[data[0].chat_id]
            except Exception as e:
                LOGGER.error(str(e))

def update_all_messages(force=False):
    with status_reply_dict_lock:
        if not status_reply_dict or not Interval or (not force and time() - list(status_reply_dict.values())[0][1] < 3):
            return
        for chat_id in status_reply_dict:
            status_reply_dict[chat_id][1] = time()

    msg, buttons = get_readable_message()
    if not msg:
        return
    with status_reply_dict_lock:
        for chat_id in status_reply_dict:
            if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id][0].text:
                rmsg = editMessage(msg, status_reply_dict[chat_id][0], buttons)
                if rmsg == "Message to edit not found":
                    del status_reply_dict[chat_id]
                    return
                status_reply_dict[chat_id][0].text = msg
                status_reply_dict[chat_id][1] = time()

def sendStatusMessage(msg, bot):
    progress, buttons = get_readable_message()
    if not progress:
        return
    with status_reply_dict_lock:
        if msg.chat_id in status_reply_dict:
            message = status_reply_dict[msg.chat_id][0]
            deleteMessage(bot, message)
            del status_reply_dict[msg.chat_id]
        message = sendMessage(progress, bot, msg, buttons)
        status_reply_dict[msg.chat_id] = [message, time()]
        if not Interval:
            Interval.append(setInterval(config_dict['DOWNLOAD_STATUS_UPDATE_INTERVAL'], update_all_messages))

def sendDmMessage(bot, message, dmMode, isLeech=False):
    if dmMode == 'mirror' and isLeech or dmMode == 'leech' and not isLeech:
        return
    try:
        return bot.sendMessage(message.from_user.id, disable_notification=True, text=message.link)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return sendDmMessage(bot, message, isLeech)
    except Unauthorized:
        delete_links(bot, message)
        buttons = ButtonMaker()
        buttons.buildbutton("Start", f"{bot.link}?start=start")
        tag = message.from_user.mention_html(message.from_user.username)
        sendMessage(f"<b>Hey @{tag}!\nYou didn't START the me in DM.\nI'll send all files in DM.\n\nStart and try again.</b>", bot, message, buttons.build_menu(1))
        return 'BotNotStarted'
    except Exception as e:
        LOGGER.error(str(e))
        return

def sendLogMessage(bot, message, link, tag):
    if not (log_chat := config_dict['LOG_CHAT']):
        return
    try:
        
        if (reply_to := message.reply_to_message) or "https://api.telegram.org/file/" in link:
            if reply_to.document or reply_to.video or reply_to.audio or reply_to.photo:
                __forwarded = reply_to.forward(log_chat)
                __forwarded.delete()
                __temp = reply_to.copy(
                    log_chat,
                    caption=f'<b><a href="{message.link}">Source</a></b> | <b>#cc</b>: {tag} (<code>{message.from_user.id}</code>)'
                )
                __forwarded.message_id = __temp['message_id']
                return __forwarded
        msg = f'<b><a href="{message.link}">Source</a></b>: <code>{link}</code>\n\n<b>#cc</b>: {tag} (<code>{message.from_user.id}</code>)'
        return bot.sendMessage(log_chat, disable_notification=True, text=msg)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return sendLogMessage(bot, message, link, tag)
    except Exception as e:
        LOGGER.error(str(e))
        return

def isAdmin(message, user_id=None):
    if message.chat.type != message.chat.PRIVATE:
        if user_id:
            member = message.chat.get_member(user_id)
        else:
            member = message.chat.get_member(message.from_user.id)
        return member.status in [member.ADMINISTRATOR, member.CREATOR] or member.is_anonymous

def forcesub(bot, message, tag):
    if not (FSUB_IDS := config_dict['FSUB_IDS']):
        return
    join_button = {}
    for channel_id in FSUB_IDS.split():
        if not str(channel_id).startswith('-100'):
            continue
        chat = bot.get_chat(channel_id)
        member = chat.get_member(message.from_user.id)
        if member.status in [member.LEFT, member.KICKED]:
            delete_links(bot, message)
            join_button[chat.title] = chat.link or chat.invite_link
    if join_button:
        btn = ButtonMaker()
        for key, value in join_button.items():
            btn.buildbutton(key, value)
        return sendMessage(f'Hey {tag}!\nPlease join our channel to use me!\nJoin And Try Again!\nThank You.', bot, message, btn.build_menu(2))

def message_filter(bot, message, tag):
    if not config_dict['ENABLE_MESSAGE_FILTER']:
        return
    _msg = ''
    if message.reply_to_message:
        if message.reply_to_message.forward_date:
            message.reply_to_message.delete()
            _msg = "You can't mirror or leech forward messages to this bot.\n\nRemove it and try again"
        elif message.reply_to_message.caption:
            message.reply_to_message.delete()
            _msg = "You can't mirror or leech with captions text to this bot.\n\nRemove it and try again"
    elif message.forward_date:
        message.delete()
        _msg = "You can't mirror or leech forward messages to this bot.\n\nRemove it and try again"
    if _msg:
        message.message_id = None
        return sendMessage(f"{tag} {_msg}", bot, message)


def delete_links(bot, message):
    if config_dict['DELETE_LINKS']:
        if reply_to := message.reply_to_message:
            deleteMessage(bot, reply_to)
        deleteMessage(bot, message)

def anno_checker(message):
    user_id = message.from_user.id
    msg_id = message.message_id
    buttons = ButtonMaker()
    if user_id == 1087968824:
        _msg = "Group Anonymous Admin"
        buttons.sbutton('Verify Anonymous', f'verify admin {msg_id}')
    elif user_id == 136817688:
        _msg = "Channel"
        buttons.sbutton('Verify Channel', f'verify channel {msg_id}')
    buttons.sbutton('Cancel', f'verify no {msg_id}')
    sendMessage(f'{_msg} Verification\nIf you hit Verify! Your username and id will expose in bot logs!', message.bot, message, buttons.build_menu(2))
    user_id = None
    btn_listener[msg_id] = [True, user_id]
    start_time = time()
    while btn_listener[msg_id][0] and time() - start_time <= 7:
        if btn_listener[msg_id][1]:
            user_id = btn_listener[msg_id][1]
            break
    del btn_listener[msg_id]
    return user_id

def open_category_btns(message):
    user_id = message.from_user.id
    msg_id = message.message_id
    buttons = ButtonMaker()
    for _name in categories.keys():
        buttons.sbutton(f'{_name}', f'scat {user_id} {msg_id} {_name}')
    prompt = sendMessage('<b>Select the category where you want to upload</b>', message.bot, message, buttons.build_menu(2))
    drive_id = None
    index_link = None
    btn_listener[msg_id] = [True, drive_id, index_link]
    start_time = time()
    while btn_listener[msg_id][0] and time() - start_time <= 30:
        if btn_listener[msg_id][1]:
            drive_id = btn_listener[msg_id][1]
            index_link = btn_listener[msg_id][2]
            break
    deleteMessage(message.bot, prompt)
    del btn_listener[msg_id]
    return drive_id, index_link
