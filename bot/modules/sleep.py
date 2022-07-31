from telegram.ext import CommandHandler
from bot import dispatcher, BASE_URL, alive
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands

def sleep(update, context):
    if BASE_URL is None:
        sendMessage(f'<code>BASE_URL_OF_BOT</code> not added in config !\nUnable to use Sleep feature.', context.bot, update.message)
    elif alive.returncode is None:
        alive.kill()
        msg = f"Okey, I'm going to sleep within 30 minutes.\n\n"
        msg += f"In case you've changed your mind and want to use me again before I sleep then restart the bot. /{BotCommands.RestartCommand}\n\n"
        msg += f'Open this link when you want to wake up the bot {BASE_URL}.'
        sendMessage(msg, context.bot, update.message)
    else:
        sendMessage(f"<b>Ping service have been stopped already !</b>\n\nI'll fall asleep in 30 minutes or less.\n\nGood Night 💤", context.bot, update.message)

sleep_handler = CommandHandler(command=BotCommands.SleepCommand, callback=sleep, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
dispatcher.add_handler(sleep_handler)