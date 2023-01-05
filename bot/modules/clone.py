from threading import Thread
from time import sleep, time
from random import SystemRandom
from string import ascii_letters, digits
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.z_utils import extract_link
from bot.helper.telegram_helper.filters import CustomFilters
from telegram.ext import CallbackQueryHandler, CommandHandler
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot import (CATEGORY_NAMES, DATABASE_URL, LOGGER, Interval, btn_listener, config_dict, dispatcher, download_dict, download_dict_lock)
from bot.helper.ext_utils.bot_utils import (check_buttons, check_user_tasks, extra_btns, get_readable_file_size, get_readable_time, is_gdrive_link, new_thread)
from bot.helper.telegram_helper.message_utils import (anno_checker, chat_restrict, delete_all_messages, delete_links, deleteMessage, editMessage, forcesub,
                                                     isAdmin, message_filter, sendDmMessage, sendLogMessage, sendMessage, sendStatusMessage, update_all_messages)

def _get_category_btns(time_out, msg_id, c_index):
    text = '<b>Select the category where you want to upload</b>'
    text += f'\n<b>Upload</b>: to Drive in {CATEGORY_NAMES[c_index]} folder'
    text += f'<u>\n\nYou have {get_readable_time(time_out)} to select the mode</u>'
    button = ButtonMaker()
    for i, _name in enumerate(CATEGORY_NAMES):
        button.sbutton(f'{_name}{" ✅" if _name == CATEGORY_NAMES[c_index] else ""}', f'clone scat {msg_id} {i}')
    button.sbutton('Cancel', f"clone cancel {msg_id}", 'footer')
    button.sbutton(f'Start ({get_readable_time(time_out)})', f'clone start {msg_id}', 'footer')
    return text, button.build_menu(3)

def _clone(message, bot):
    args = message.text.split()
    reply_to = message.reply_to_message
    link = ''
    multi = 0
    msg_id = message.message_id
    c_index = 0
    raw_url = None
    if len(args) > 1:
        link = args[1].strip()
        if link.strip().isdigit():
            multi = int(link)
            link = ''
        elif message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
    if reply_to:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    if not is_gdrive_link(link) or (link.strip().isdigit() and multi == 0):
        msg_ = "Send Gdrive link along with command or by replying to the link by command\n"
        msg_ += "\n<b>Multi links only by replying to first link:</b>\n<code>/cmd</code> 10(number of links)"
        return sendMessage(msg_, bot, message)
    if message.from_user.id in [1087968824, 136817688]:
        message.from_user.id = anno_checker(message)
        if not message.from_user.id:
            return
    if not isAdmin(message):
        if message_filter(bot, message, tag):
            return
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS']:
            raw_url = extract_link(link)
            if exist := DbManger().check_download(raw_url):
                _msg = f'<b>Download is already added by {exist["tag"]}</b>\n\nCheck the download status in @{exist["botname"]}\n\n<b>Link</b>: <code>{exist["_id"]}</code>'
                delete_links(bot, message)
                return sendMessage(_msg, bot, message)
        if forcesub(bot, message, tag):
            return
        if (maxtask:= config_dict['USER_MAX_TASKS']) and check_user_tasks(message.from_user.id, maxtask):
            return sendMessage(f"Your tasks limit exceeded for {maxtask} tasks", bot, message)
    time_out = 30
    listner = [bot, message, c_index, time_out, time(), tag, link, raw_url]
    if len(CATEGORY_NAMES) > 1:
        if checked:= check_buttons():
            return sendMessage(checked, bot, message)
        text, btns = _get_category_btns(time_out, msg_id, c_index)
        btn_listener[msg_id] = listner
        chat_restrict(message)
        engine = sendMessage(text, bot, message, btns)
        _auto_start_dl(engine, msg_id, time_out)
    else:
        chat_restrict(message)
        start_clone(listner)
    if multi > 1:
        sleep(4)
        nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
        cmsg = message.text.split()
        cmsg[1] = f"{multi - 1}"
        nextmsg = sendMessage(" ".join(cmsg), bot, nextmsg)
        nextmsg.from_user.id = message.from_user.id
        sleep(4)
        Thread(target=_clone, args=(nextmsg, bot)).start()

@new_thread
def _auto_start_dl(msg, msg_id, time_out):
    sleep(time_out)
    if msg_id not in btn_listener:
        return
    info = btn_listener[msg_id]
    del btn_listener[msg_id]
    editMessage("Timed out! Task has been started.", msg)
    start_clone(info)

@new_thread
def start_clone(listner):
    bot = listner[0]
    message = listner[1]
    c_index = listner[2]
    tag = listner[5]
    link = listner[6]
    raw_url = listner[7]
    if config_dict['ENABLE_DM'] and message.chat.type == message.chat.SUPERGROUP:
        dmMessage = sendDmMessage(bot, message)
        if not dmMessage:
            return
    else:
        dmMessage = None
    logMessage = sendLogMessage(bot, message)
    gd = GoogleDriveHelper(user_id=message.from_user.id)
    res, size, name, files = gd.helper(link)
    if res != "":
        delete_links(bot, message)
        return sendMessage(res, bot, message)
    if config_dict['STOP_DUPLICATE']:
        LOGGER.info('Checking File/Folder if already in Drive...')
        smsg, button = gd.drive_list(name, True, True)
        if smsg:
            msg = "File/Folder is already available in Drive.\nHere are the search results:"
            delete_links(bot, message)
            return sendMessage(msg, bot, message, button)
    if CLONE_LIMIT := config_dict['CLONE_LIMIT']:
        limit = CLONE_LIMIT * 1024**3
        if size > limit:
            msg2 = f'Failed, Clone limit is {get_readable_file_size(limit)}.\nYour File/Folder size is {get_readable_file_size(size)}.'
            delete_links(bot, message)
            return sendMessage(msg2, bot, message)
    mode = f'Clone {CATEGORY_NAMES[c_index]}'
    delete_links(bot, message)
    if files <= 20:
        msg = sendMessage(f"Cloning: <code>{link}</code>", bot, message)
        result, links_dict = gd.clone(link, c_index)
        deleteMessage(bot, msg)
    else:
        drive = GoogleDriveHelper(name, user_id=message.from_user.id)
        gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
        clone_status = CloneStatus(drive, size, message, gid, mode)
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and raw_url:
            DbManger().add_download_url(raw_url, tag)
        with download_dict_lock:
            download_dict[message.message_id] = clone_status
        sendStatusMessage(message, bot)
        result, links_dict = drive.clone(link, c_index)
        with download_dict_lock:
            del download_dict[message.message_id]
            count = len(download_dict)
        try:
            if count == 0:
                Interval[0].cancel()
                del Interval[0]
                delete_all_messages()
            else:
                update_all_messages()
        except IndexError:
            pass
    cc = f'\n\n<b>#cc</b>: {tag} | <b>Elapsed</b>: {get_readable_time(time() - message.date.timestamp())}\n\n<b>Upload</b>: {mode}'
    if links_dict in ["cancelled", ""]:
        delete_links(bot, message)
        sendMessage(f"{tag} {result}", bot, message)
    else:
        buttons = ButtonMaker()
        if not config_dict['DISABLE_DRIVE_LINK']:
            buttons.buildbutton("🔐 Drive Link", links_dict['durl'])
        if index:= links_dict.get('index'):
            buttons.buildbutton("🚀 Index Link", index)
        if view:= links_dict.get('view'):
            buttons.buildbutton('💻 View Link', view)
        __btns = extra_btns(buttons)
        if dmMessage:
            sendMessage(f"{result + cc}", bot, dmMessage, __btns.build_menu(2))
            sendMessage(f"{result + cc}\n\n<b>Links has been sent in your DM.</b>", bot, message)
        else:
            if message.chat.type != 'private':
                __btns.sbutton("Save This Message", 'save', 'footer')
            sendMessage(f"{result + cc}", bot, message, __btns.build_menu(2))
        if logMessage:
            if config_dict['DISABLE_DRIVE_LINK']:
                buttons.buildbutton("🔐 Drive Link", links_dict['durl'], 'header')
            sendMessage(f"{result + cc}", bot, logMessage, buttons.build_menu(2))
        delete_links(bot, message)
        if DATABASE_URL and config_dict['STOP_DUPLICATE_TASKS'] and raw_url:
            DbManger().remove_download(raw_url)
        LOGGER.info(f"Cloning Done: {name}")

@new_thread
def clone_confirm(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    message = query.message
    data = query.data
    data = data.split()
    msg_id = int(data[2])
    if msg_id not in btn_listener:
        return editMessage('<b>Download has been cancelled or started already</b>', message)
    listnerInfo = btn_listener[msg_id]
    if user_id != listnerInfo[1].from_user.id:
        return query.answer("You are not the owner of this download", show_alert=True)
    elif data[1] == 'scat':
        c_index = int(data[3])
        if listnerInfo[2] == c_index:
            return query.answer(f"{CATEGORY_NAMES[c_index]} is Selected Already", show_alert=True)
        query.answer()
        listnerInfo[2] = c_index
    elif data[1] == 'cancel':
        query.answer()
        del btn_listener[msg_id]
        return editMessage('<b>Download has been cancelled</b>', message)
    elif data[1] == 'start':
        query.answer()
        del btn_listener[msg_id]
        message.delete()
        return start_clone(listnerInfo)
    time_out = listnerInfo[3] - (time() - listnerInfo[4])
    text, btns = _get_category_btns(time_out, msg_id, listnerInfo[2])
    editMessage(text, message, btns)

@new_thread
def cloneNode(update, context):
    _clone(update.message, context.bot)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode,
                               filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
clone_confirm_handler = CallbackQueryHandler(clone_confirm, pattern="clone")
dispatcher.add_handler(clone_confirm_handler)
dispatcher.add_handler(clone_handler)
