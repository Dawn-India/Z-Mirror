from threading import Thread
from time import time

from psutil import cpu_percent, disk_usage, virtual_memory
from telegram.ext import CallbackQueryHandler, CommandHandler

from bot import (DOWNLOAD_DIR, Interval, botStartTime, config_dict, dispatcher,
                 download_dict, download_dict_lock, status_reply_dict_lock)
from bot.helper.ext_utils.bot_utils import (get_readable_file_size,
                                            get_readable_time, new_thread,
                                            setInterval, turn)
from bot.helper.ext_utils.rate_limiter import ratelimiter
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (auto_delete_message,
                                                      deleteMessage,
                                                      sendMessage,
                                                      sendStatusMessage,
                                                      update_all_messages)


@ratelimiter
def mirror_status(update, context):
    with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        currentTime = get_readable_time(time() - botStartTime)
        free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
        message = 'No Active Downloads !\n___________________________'
        message += f"\n<b>CPU</b>: {cpu_percent()}% | <b>FREE</b>: {free}" \
                   f"\n<b>RAM</b>: {virtual_memory().percent}% | <b>UPTIME</b>: {currentTime}"
        reply_message = sendMessage(message, context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, reply_message)).start()
    else:
        sendStatusMessage(update.message, context.bot)
        deleteMessage(context.bot, update.message)
        with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(setInterval(config_dict['DOWNLOAD_STATUS_UPDATE_INTERVAL'], update_all_messages))

@new_thread
@ratelimiter
def status_pages(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    data = data.split()
    if data[1] == "ref":
        update_all_messages(True)
        return
    done = turn(data)
    if not done:
        query.message.delete()


mirror_status_handler = CommandHandler(BotCommands.StatusCommand, mirror_status,
                                      filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
status_pages_handler = CallbackQueryHandler(status_pages, pattern="status")

dispatcher.add_handler(mirror_status_handler)
dispatcher.add_handler(status_pages_handler)
