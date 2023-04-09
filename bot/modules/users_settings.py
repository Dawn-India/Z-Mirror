from asyncio import sleep
from functools import partial
from html import escape
from io import BytesIO
from math import ceil
from os import getcwd
from os import path as ospath
from re import sub as re_sub
from time import time

from aiofiles.os import mkdir
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from PIL import Image
from pyrogram.filters import command, create, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from bot import (DATABASE_URL, IS_PREMIUM_USER, MAX_SPLIT_SIZE, bot,
                 config_dict, user_data)
from bot.helper.ext_utils.bot_utils import (get_readable_file_size, new_thread,
                                            sync_to_async, update_user_ldata)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (editMessage, sendFile,
                                                      sendMessage)

handler_dict = {}


async def get_user_settings(from_user):
    user_id = from_user.id
    name = from_user.mention
    buttons = ButtonMaker()
    thumbpath = f"Thumbnails/{user_id}.jpg"
    rclone_path = f'rclone/{user_id}.conf'
    user_dict = user_data.get(user_id, {})
    if user_dict.get('as_doc', False) or 'as_doc' not in user_dict and config_dict['AS_DOCUMENT']:
        ltype = "DOCUMENT"
        buttons.ibutton("Send As Media", f"userset {user_id} doc")
    else:
        ltype = "MEDIA"
        buttons.ibutton("Send As Document", f"userset {user_id} doc")

    buttons.ibutton("Leech Splits", f"userset {user_id} lss")
    split_size = user_dict.get(
        'split_size', False) or config_dict['LEECH_SPLIT_SIZE']
    split_size = get_readable_file_size(split_size)

    if user_dict.get('equal_splits', False) or 'equal_splits' not in user_dict and config_dict['EQUAL_SPLITS']:
        equal_splits = 'Enabled'
    else:
        equal_splits = 'Disabled'

    if user_dict.get('media_group', False) or 'media_group' not in user_dict and config_dict['MEDIA_GROUP']:
        media_group = 'Enabled'
    else:
        media_group = 'Disabled'

    buttons.ibutton("YT-DLP Quality", f"userset {user_id} ytq")
    YQ = config_dict['YT_DLP_QUALITY']
    if user_dict.get('yt_ql', False):
        ytq = user_dict['yt_ql']
    elif 'yt_ql' not in user_dict and YQ:
        ytq = YQ
    else:
        ytq = 'None'

    buttons.ibutton("Thumbnail", f"userset {user_id} sthumb")
    thumbmsg = "Exists" if await aiopath.exists(thumbpath) else "Not Exists"

    buttons.ibutton("Rclone", f"userset {user_id} rcc")
    rccmsg = "Exists" if await aiopath.exists(rclone_path) else "Not Exists"

    LP = config_dict['LEECH_FILENAME_PREFIX']
    if user_dict.get('lprefix', False):
        lprefix = user_dict['lprefix']
    elif 'lprefix' not in user_dict and LP:
        lprefix = LP
    else:
        lprefix = 'None'
    buttons.ibutton("Leech Prefix", f"userset {user_id} lprefix")

    if user_dict:
        buttons.ibutton("Reset Setting", f"userset {user_id} reset_all")

    buttons.ibutton("Close", f"userset {user_id} close")
    text = f"<u>Settings for {name}</u>\n\n"\
        f"Leech Type is <b>{ltype}</b>\n"\
        f"Custom Thumbnail <b>{thumbmsg}</b>\n"\
        f"Rclone Config <b>{rccmsg}</b>\n"\
        f"Leech Split Size is <b>{split_size}</b>\n"\
        f"Equal Splits is <b>{equal_splits}</b>\n"\
        f"Media Group is <b>{media_group}</b>\n"\
        f"YT-DLP Quality is <code>{escape(ytq)}</code>\n"\
        f"Leech Prefix is <code>{escape(lprefix)}</code>"
    return text, buttons.build_menu(1)


async def update_user_settings(query):
    msg, button = await get_user_settings(query.from_user)
    await editMessage(query.message, msg, button)


async def user_settings(client, message):
    msg, button = await get_user_settings(message.from_user)
    await sendMessage(message, msg, button)


async def set_yt_quality(client, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    update_user_ldata(user_id, 'yt_ql', value)
    await message.delete()
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)


async def set_prefix(client, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    if len(re_sub('<.*?>', '', value)) <= 15:
        update_user_ldata(user_id, 'lprefix', value)
        await message.delete()
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    await update_user_settings(pre_event)


async def set_thumb(client, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    path = "Thumbnails/"
    if not await aiopath.isdir(path):
        await mkdir(path)
    photo_dir = await message.download()
    des_dir = ospath.join(path, f'{user_id}.jpg')
    await sync_to_async(Image.open(photo_dir).convert("RGB").save, des_dir, "JPEG")
    await aioremove(photo_dir)
    update_user_ldata(user_id, 'thumb', des_dir)
    await message.delete()
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManger().update_user_doc(user_id, 'thumb', des_dir)


async def add_rclone(client, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    path = f'{getcwd()}/rclone/'
    if not await aiopath.isdir(path):
        await mkdir(path)
    des_dir = ospath.join(path, f'{user_id}.conf')
    await message.download(file_name=des_dir)
    update_user_ldata(user_id, 'rclone', f'rclone/{user_id}.conf')
    await message.delete()
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManger().update_user_doc(user_id, 'rclone', des_dir)


async def leech_split_size(client, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = min(ceil(float(message.text) * 1024 ** 3), MAX_SPLIT_SIZE)
    update_user_ldata(user_id, 'split_size', value)
    await message.delete()
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)


async def event_handler(client, query, pfunc, photo=False, document=False):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        if photo:
            mtype = event.photo
        elif document:
            mtype = event.document
        else:
            mtype = event.text
        user = event.from_user or event.sender_chat
        return bool(user.id == user_id and event.chat.id == query.message.chat.id and mtype)
    handler = client.add_handler(MessageHandler(
        pfunc, filters=create(event_filter)), group=-1)
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await update_user_settings(query)
    client.remove_handler(*handler)


@new_thread
async def edit_user_settings(client, query):
    from_user = query.from_user
    user_id = from_user.id
    message = query.message
    data = query.data.split()
    thumb_path = f'Thumbnails/{user_id}.jpg'
    rclone_path = f'rclone/{user_id}.conf'
    user_dict = user_data.get(user_id, {})
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "doc":
        update_user_ldata(user_id, 'as_doc',
                          not user_dict.get('as_doc', False))
        await query.answer()
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'vthumb':
        handler_dict[user_id] = False
        await query.answer()
        await sendFile(message, thumb_path, from_user.mention)
        await update_user_settings(query)
    elif data[2] == "dthumb":
        handler_dict[user_id] = False
        if await aiopath.exists(thumb_path):
            await query.answer()
            await aioremove(thumb_path)
            update_user_ldata(user_id, 'thumb', '')
            await update_user_settings(query)
            if DATABASE_URL:
                await DbManger().update_user_doc(user_id, 'thumb')
        else:
            await query.answer("Old Settings", show_alert=True)
            await update_user_settings(query)
    elif data[2] == "sthumb":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(thumb_path):
            buttons.ibutton("View Thumbnail", f"userset {user_id} vthumb")
            buttons.ibutton("Delete Thumbnail", f"userset {user_id} dthumb")
        buttons.ibutton("Back", f"userset {user_id} back")
        buttons.ibutton("Close", f"userset {user_id} close")
        await editMessage(message, 'Send a photo to save it as custom thumbnail. Timeout: 60 sec', buttons.build_menu(1))
        pfunc = partial(set_thumb, pre_event=query)
        await event_handler(client, query, pfunc, True)
    elif data[2] == 'ytq':
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton("Back", f"userset {user_id} back")
        if user_dict.get('yt_ql', False) or config_dict['YT_DLP_QUALITY']:
            buttons.ibutton("Remove YT-DLP Quality",
                            f"userset {user_id} rytq", 'header')
        buttons.ibutton("Close", f"userset {user_id} close")
        rmsg = f'''
Send YT-DLP Qaulity. Timeout: 60 sec
Examples:
1. <code>{escape('bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]')}</code> this will give 1080p-mp4.
2. <code>{escape('bv*[height<=720][ext=webm]+ba/b[height<=720]')}</code> this will give 720p-webm.
Check all available qualities options <a href="https://github.com/yt-dlp/yt-dlp#filtering-formats">HERE</a>.
        '''
        await editMessage(message, rmsg, buttons.build_menu(1))
        pfunc = partial(set_yt_quality, pre_event=query)
        await event_handler(client, query, pfunc)
    elif data[2] == 'rytq':
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, 'yt_ql', '')
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'lprefix':
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton("Back", f"userset {user_id} back")
        if user_dict.get('lprefix', False) or config_dict['LEECH_FILENAME_PREFIX']:
            buttons.ibutton("Remove Leech Prefix",
                            f"userset {user_id} rlpre", 'header')
        buttons.ibutton("Close", f"userset {user_id} close")
        rmsg = f'''
Send Leech Prefix. Timeout: 60 sec
Examples:
1. <code>{escape('<b>@MLTB_Official</b>')}</code> 
This will give output of:
<b>@JMDKH_Team</b>  <code>69MB.bin</code>.

2. <code>{escape('<code>@JMDKH_Team</code>')}</code> 
This will give output of:
<code>@JMDKH_Team</code> <code>69MB.bin</code>.

Check all available formatting options <a href="https://core.telegram.org/bots/api#formatting-options">HERE</a>.
        '''
        await editMessage(message, rmsg, buttons.build_menu(1))
        pfunc = partial(set_prefix, pre_event=query)
        await event_handler(client, query, pfunc)
    elif data[2] == 'rlpre':
        handler_dict[user_id] = False
        await query.answer(text="Leech Prefix Removed!", show_alert=True)
        update_user_ldata(user_id, 'lprefix', '')
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'lss':
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get('split_size', False):
            buttons.ibutton("Reset Split Size", f"userset {user_id} rlss")
        if user_dict.get('equal_splits', False) or 'equal_splits' not in user_dict and config_dict['EQUAL_SPLITS']:
            buttons.ibutton("Disable Equal Splits",
                            f"userset {user_id} esplits")
        else:
            buttons.ibutton("Enable Equal Splits",
                            f"userset {user_id} esplits")
        if user_dict.get('media_group', False) or 'media_group' not in user_dict and config_dict['MEDIA_GROUP']:
            buttons.ibutton("Disable Media Group", f"userset {user_id} mgroup")
        else:
            buttons.ibutton("Enable Media Group", f"userset {user_id} mgroup")
        buttons.ibutton("Back", f"userset {user_id} back")
        buttons.ibutton("Close", f"userset {user_id} close")
        __msg = "Send Leech split size don't add unit, the default unit is <b>GB</b>\n"
        __msg += f"\nExamples:\n1 for 1GB\n0.5 for 512mb\n\nIS_PREMIUM_USER: {IS_PREMIUM_USER}. Timeout: 60 sec"
        await editMessage(message, __msg, buttons.build_menu(1))
        pfunc = partial(leech_split_size, pre_event=query)
        await event_handler(client, query, pfunc)
    elif data[2] == 'rlss':
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, 'split_size', '')
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'esplits':
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, 'equal_splits',
                          not user_dict.get('equal_splits', False))
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'mgroup':
        handler_dict[user_id] = False
        await query.answer()
        update_user_ldata(user_id, 'media_group',
                          not user_dict.get('media_group', False))
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
    elif data[2] == 'rcc':
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(rclone_path):
            buttons.ibutton("Delete rclone.conf", f"userset {user_id} drcc")
        buttons.ibutton("Back", f"userset {user_id} back")
        buttons.ibutton("Close", f"userset {user_id} close")
        await editMessage(message, 'Send rclone.conf. Timeout: 60 sec', buttons.build_menu(1))
        pfunc = partial(add_rclone, pre_event=query)
        await event_handler(client, query, pfunc, document=True)
    elif data[2] == 'drcc':
        handler_dict[user_id] = False
        if await aiopath.exists(rclone_path):
            await query.answer()
            await aioremove(rclone_path)
            update_user_ldata(user_id, 'rclone', '')
            await update_user_settings(query)
            if DATABASE_URL:
                await DbManger().update_user_doc(user_id, 'rclone')
        else:
            await query.answer("Old Settings", show_alert=True)
            await update_user_settings(query)
    elif data[2] == 'back':
        handler_dict[user_id] = False
        await query.answer()
        await update_user_settings(query)
    elif data[2] == 'reset_all':
        handler_dict[user_id] = False
        if await aiopath.exists(thumb_path):
            await aioremove(thumb_path)
        if await aiopath.exists(rclone_path):
            await aioremove(rclone_path)
        await query.answer()
        update_user_ldata(user_id, None, None)
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_doc(user_id)
    elif data[2] == 'user_del':
        user_id = int(data[3])
        await query.answer()
        thumb_path = f'Thumbnails/{user_id}.jpg'
        rclone_path = f'rclone/{user_id}.conf'
        if await aiopath.exists(thumb_path):
            await aioremove(thumb_path)
        if await aiopath.exists(rclone_path):
            await aioremove(rclone_path)
        update_user_ldata(user_id, None, None)
        if DATABASE_URL:
            await DbManger().update_user_doc(user_id)
        await editMessage(message, f'Data reset for {user_id}')
    else:
        if data[2] == 'close':
            handler_dict[user_id] = False
        await query.answer()
        await message.reply_to_message.delete()
        await message.delete()


async def send_users_settings(client, message):
    text = message.text.split(maxsplit=1)
    userid = text[1] if len(text) > 1 else None
    if userid and not userid.isdigit():
        userid = None
    elif (reply_to := message.reply_to_message) and reply_to.from_user and not reply_to.from_user.is_bot:
        userid = reply_to.from_user.id
    if not userid:
        msg = f'{len(user_data)} users save there setting'
        for user, data in user_data.items():
            msg += f'\n\n<code>{user}</code>:'
            if data:
                for key, value in data.items():
                    msg += f'\n<b>{key}</b>: <code>{escape(str(value))}</code>'
            else:
                msg += '\nThis user is not saved anythings.'
        if len(msg.encode()) > 4000:
            with BytesIO(str.encode(msg)) as ofile:
                ofile.name = 'users_settings.txt'
                await sendFile(message, ofile)
        else:
            await sendMessage(message, msg)
    elif userid in user_data:
        msg = f'<b>{userid}</b>:'
        if data := user_data[userid]:
            buttons = ButtonMaker()
            buttons.ibutton(
                "Delete Data", f"userset {message.from_user.id} user_del {userid}")
            buttons.ibutton("Close", f"userset {message.from_user.id} x")
            button = buttons.build_menu(1)
            for key, value in data.items():
                msg += f'\n<b>{key}</b>: <code>{escape(str(value))}</code>'
        else:
            msg += '\nThis user is not saved anythings.'
            button = None
        await sendMessage(message, msg, button)
    else:
        await sendMessage(message, f'{userid} have not saved anything..')

bot.add_handler(MessageHandler(send_users_settings, filters=command(
    BotCommands.UsersCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(user_settings, filters=command(
    BotCommands.UserSetCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(
    edit_user_settings, filters=regex("^userset")))
