from time import time

from psutil import cpu_percent, disk_usage, virtual_memory
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import (DOWNLOAD_DIR, Interval, bot, botStartTime, config_dict,
                 download_dict, download_dict_lock, status_reply_dict_lock)
from bot.helper.ext_utils.bot_utils import (get_readable_file_size,
                                            get_readable_time, new_task,
                                            setInterval, turn_page)
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (auto_delete_message,
                                                      deleteMessage, isAdmin,
                                                      request_limiter, sendMessage,
                                                      sendStatusMessage,
                                                      update_all_messages)


@new_task
async def mirror_status(client, message):
    async with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        currentTime = get_readable_time(time() - botStartTime)
        free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
        msg = '<b>Uninstall Telegram and enjoy your life!</b>'
        msg += '\n\nNo Active Tasks!\n___________________________'
        msg += f"\n<b>CPU</b>: {cpu_percent()}% | <b>FREE</b>: {free}" \
               f"\n<b>RAM</b>: {virtual_memory().percent}% | <b>UPTIME</b>: {currentTime}"
        reply_message = await sendMessage(message, msg)
        await auto_delete_message(message, reply_message)
    else:
        await sendStatusMessage(message)
        await deleteMessage(message)
        async with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(setInterval(config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))

@new_task
async def status_pages(client, query):
    if not await isAdmin(query.message, query.from_user.id) and await request_limiter(query=query):
        return
    await query.answer()
    data = query.data.split()
    if data[1] == "ref":
        await update_all_messages(True)
    else:
        await turn_page(data)


bot.add_handler(MessageHandler(mirror_status, filters=command(BotCommands.StatusCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(status_pages, filters=regex("^status")))