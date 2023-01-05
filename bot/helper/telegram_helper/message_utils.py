from time import sleep, time
from telegram.error import RetryAfter, Unauthorized
from pyrogram.errors import FloodWait
from os import remove
from bot import (LOGGER, Interval, bot, btn_listener, config_dict, rss_session, status_reply_dict, status_reply_dict_lock)
from bot.helper.ext_utils.bot_utils import get_readable_message, setInterval
from bot.helper.telegram_helper.button_build import ButtonMaker
from telegram import ChatPermissions

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

def sendFile(bot, message, name, caption=""):
    try:
        with open(name, 'rb') as f:
            bot.sendDocument(document=f, filename=f.name, reply_to_message_id=message.message_id,
                             caption=caption, chat_id=message.chat_id)
        remove(name)
        return
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return sendFile(bot, message, name, caption)
    except Exception as e:
        LOGGER.error(str(e))
        return

def auto_delete_message(bot, cmd_message=None, bot_message=None):
    if config_dict['AUTO_DELETE_MESSAGE_DURATION'] != -1:
        sleep(config_dict['AUTO_DELETE_MESSAGE_DURATION'])
        if cmd_message is not None:
            deleteMessage(bot, cmd_message)
        if bot_message is not None:
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
    if msg is None:
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
    if progress is None:
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

def sendDmMessage(bot, message):
    try:
        return bot.sendMessage(message.from_user.id, disable_notification=True, text=message.link)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return sendDmMessage(bot, message)
    except Unauthorized:
        buttons = ButtonMaker()
        buttons.buildbutton("Start", f"{bot.link}?start=start")
        sendMessage("<b>You didn't START the bot in DM</b>", bot, message, buttons.build_menu(1))
        return
    except Exception as e:
        LOGGER.error(str(e))
        return

def sendLogMessage(bot, message):
    if not (log_chat := config_dict['LOG_CHAT']):
        return
    try:
        return bot.sendMessage(log_chat, disable_notification=True, text=message.link or message.text)
    except RetryAfter as r:
        LOGGER.warning(str(r))
        sleep(r.retry_after * 1.5)
        return sendLogMessage(bot, message)
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
        if member.status in [member.LEFT, member.KICKED] :
            join_button[chat.title] = chat.link or chat.invite_link
    if join_button:
        btn = ButtonMaker()
        for key, value in join_button.items():
            btn.buildbutton(key, value)
        return sendMessage(f'Dear {tag},\nPlease join our channel to use me!\n🔻 Join And Try Again!', bot, message, btn.build_menu(2))

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

def chat_restrict(message):
    if not config_dict['ENABLE_CHAT_RESTRICT']:
        return
    if not isAdmin(message):
        message.chat.restrict_member(message.from_user.id, ChatPermissions(), int(time() + 60))

def delete_links(bot, message):
    if config_dict['DELETE_LINKS']:
        if message.reply_to_message:
            deleteMessage(bot, message.reply_to_message)
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
    btn_listener[msg_id] = [True, None]
    buttons.sbutton('Cancel', f'verify no {msg_id}')
    sendMessage(f'{_msg} Verification\nIf you hit Verify! Your username and id will expose in bot logs!', message.bot, message, buttons.build_menu(2))
    user_id = None
    start_time = time()
    while btn_listener[msg_id][0] and time() - start_time <= 7:
        if btn_listener[msg_id][1]:
            user_id = btn_listener[msg_id][1]
            break
    del btn_listener[msg_id]
    return user_id
