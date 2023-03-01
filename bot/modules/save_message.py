from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler

from bot import bot
from bot.helper.ext_utils.bot_utils import new_task


@new_task
async def save_message(client, query):
    if query.data == "save":
        try:
            del query.message.reply_markup.inline_keyboard[-1]
            await query.message.copy(query.from_user.id, reply_markup=query.message.reply_markup)
            await query.answer('Message Saved Successfully', show_alert=True)
        except:
            await query.answer('Start the bot in private and try again', show_alert=True)


bot.add_handler(CallbackQueryHandler(save_message, filters=regex("^save")))
