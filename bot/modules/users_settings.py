from aiofiles.os import (
    remove,
    path as aiopath,
    makedirs
)
from asyncio import sleep
from functools import partial
from html import escape
from io import BytesIO
from math import ceil
from os import getcwd, path as os_path
from pyrogram.filters import (
    command,
    regex,
    create
)
from pyrogram.handlers import (
    MessageHandler,
    CallbackQueryHandler
)
from pyrogram.types import InputMediaPhoto
from re import search as re_search
from time import time

from bot import (
    bot,
    user_data,
    config_dict,
    IS_PREMIUM_USER,
    JAVA,
    DATABASE_URL,
    MAX_SPLIT_SIZE,
    GLOBAL_EXTENSION_FILTER,
)
from bot.helper.ext_utils.bot_utils import (
    update_user_ldata,
    new_thread,
)
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.media_utils import createThumb
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    anno_checker,
    auto_delete_message,
    sendMessage,
    editMessage,
    sendFile,
    deleteMessage,
)
from bot.helper.z_utils import def_media

handler_dict = {}


async def get_user_settings(from_user):
    user_id = from_user.id
    name = from_user.mention
    buttons = ButtonMaker()
    thumbpath = f"Thumbnails/{user_id}.jpg"
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    user_dict = user_data.get(user_id, {})

    if (
        user_dict.get(
            "as_doc",
            False
        )
        or "as_doc" not in user_dict
        and config_dict["AS_DOCUMENT"]
    ):
        ltype = "DOCUMENT"
    else:
        ltype = "MEDIA"

    thumbmsg = (
        "Exists"
        if await aiopath.exists(thumbpath)
        else "Not Exists"
    )

    if user_dict.get(
        "split_size",
        False
    ):
        split_size = user_dict["split_size"]
    else:
        split_size = config_dict["LEECH_SPLIT_SIZE"]
    split_size = get_readable_file_size(split_size)

    if (
        user_dict.get(
            "equal_splits",
            False
        )
        or "equal_splits" not in user_dict
        and config_dict["EQUAL_SPLITS"]
    ):
        equal_splits = "Enabled"
    else:
        equal_splits = "Disabled"

    if (
        user_dict.get(
            "media_group",
            False
        )
        or "media_group" not in user_dict
        and config_dict["MEDIA_GROUP"]
    ):
        media_group = "Enabled"
    else:
        media_group = "Disabled"

    if user_dict.get(
        "lprefix",
        False
    ):
        lprefix = "Added"
    elif (
        "lprefix" not in user_dict
        and (LP := config_dict["LEECH_FILENAME_PREFIX"])
    ):
        lprefix = "Added"
    else:
        lprefix = "Not Added"

    if user_dict.get(
        "lsuffix",
        False
    ):
        lsuffix = "Added"
    elif (
        "lsuffix" not in user_dict
        and (LS := config_dict["LEECH_FILENAME_SUFFIX"])
    ):
        lsuffix = "Added"
    else:
        lsuffix = "Not Added"

    if user_dict.get(
        "lcapfont",
        False
    ):
        lcapfont = "Added"
    elif (
        "lcapfont" not in user_dict
        and (LC := config_dict["LEECH_CAPTION_FONT"])
    ):
        lcapfont = "Added"
    else:
        lcapfont = "Not Added"

    if user_dict.get(
        "leech_dest",
        False
    ):
        leech_dest = user_dict["leech_dest"]
    elif (
        "leech_dest" not in user_dict
        and (LD := config_dict["USER_LEECH_DESTINATION"])
    ):
        leech_dest = LD
    else:
        leech_dest = "None"

    if (
        IS_PREMIUM_USER
        and user_dict.get(
            "user_transmission",
            False
        )
        or "user_transmission" not in user_dict
        and config_dict["USER_TRANSMISSION"]
    ):
        leech_method = "user"
    else:
        leech_method = "bot"

    if (
        IS_PREMIUM_USER
        and user_dict.get(
            "mixed_leech",
            False
        )
        or "mixed_leech" not in user_dict
        and config_dict["MIXED_LEECH"]
    ):
        mixed_leech = "Enabled"
    else:
        mixed_leech = "Disabled"

    buttons.ibutton(
        "Leech Settings",
        f"userset {user_id} leech"
    )

    buttons.ibutton(
        "Rclone Tools",
        f"userset {user_id} rclone"
    )
    rccmsg = (
        "Exists"
        if await aiopath.exists(rclone_conf)
        else "Not Exists"
    )
    if user_dict.get(
        "rclone_path",
        False
    ):
        rccpath = "Added"
    elif RP := config_dict["RCLONE_PATH"]:
        rccpath = "Added"
    else:
        rccpath = "Not Added"

    buttons.ibutton(
        "Gdrive Tools",
        f"userset {user_id} gdrive"
    )
    tokenmsg = (
        "Exists"
        if await aiopath.exists(token_pickle)
        else "Not Exists"
    )
    gdrive_id = (
        "Added"
        if user_dict.get(
            "gdrive_id",
            False
        )
        else "Not Added"
    )
    index = (
        "Added"
        if user_dict.get(
            "index_url",
            False
        )
        else "Not Added"
    )
    if (
        user_dict.get(
            "stop_duplicate",
            False
        )
        or "stop_duplicate" not in user_dict
        and config_dict["STOP_DUPLICATE"]
    ):
        sd_msg = "Enabled"
    else:
        sd_msg = "Disabled"

    upload_paths = (
        "Added"
        if user_dict.get(
            "upload_paths",
            False
        )
        else "Not Added"
    )
    buttons.ibutton(
        "Upload Paths",
        f"userset {user_id} upload_paths"
    )

    default_upload = (
        user_dict.get(
            "default_upload",
            ""
        )
        or config_dict["DEFAULT_UPLOAD"]
    )
    du = (
        "Gdrive API"
        if default_upload == "gd"
        else "Rclone"
    )
    dub = (
        "Gdrive API"
        if default_upload != "gd"
        else "Rclone"
    )
    buttons.ibutton(
        f"Upload using {dub}",
        f"userset {user_id} {default_upload}"
    )

    buttons.ibutton(
        "Extension Filter",
        f"userset {user_id} ex_ex"
    )
    ex_ex = (
        "Added"
        if user_dict.get(
            "excluded_extensions",
            False
        )
        else "Not Added"
    )

    ns_msg = (
        "Added"
        if user_dict.get(
            "name_sub",
            False
        )
        else "Not Added"
    )
    buttons.ibutton(
        "Name Substitute",
        f"userset {user_id} name_substitute"
    )

    buttons.ibutton(
        "YT-DLP Options",
        f"userset {user_id} yto"
    )
    if user_dict.get(
        "yt_opt",
        False
    ):
        ytopt = "Added"
    elif (
        "yt_opt" not in user_dict
        and (YTO := config_dict["YT_DLP_OPTIONS"])
    ):
        ytopt = "Added"
    else:
        ytopt = "Not Added"

    if user_dict:
        buttons.ibutton(
            "Reset All",
            f"userset {user_id} reset"
        )

    buttons.ibutton(
        "Close",
        f"userset {user_id} close"
    )

    text = f"""
<u>Settings for {name}</u>

<code>TG Premium Status:</code> <b>{IS_PREMIUM_USER}</b>

<code>Leech Type       :</code> <b>{ltype}</b>
<code>Leech Prefix     :</code> <b>{lprefix}</b>
<code>Leech Suffix     :</code> <b>{lsuffix}</b>
<code>Leech Cap Font   :</code> <b>{lcapfont}</b>
<code>Leech Split Size :</code> <b>{split_size}</b>
<code>Leech Destination:</code> <b>{leech_dest}</b>

<code>Thumbnail        :</code> <b>{thumbmsg}</b>
<code>Equal Splits     :</code> <b>{equal_splits}</b>
<code>Media Group      :</code> <b>{media_group}</b>
<code>Upload Client    :</code> <b>{leech_method} session</b>
<code>Hybrid Upload    :</code> <b>{mixed_leech}</b>

<code>Rclone Config    :</code> <b>{rccmsg}</b>
<code>Rclone Path      :</code> <b>{rccpath}</b>

<code>Gdrive Token     :</code> <b>{tokenmsg}</b>
<code>Gdrive ID        :</code> <b>{gdrive_id}</b>
<code>Index Link       :</code> <b>{index}</b>

<code>Stop Duplicate   :</code> <b>{sd_msg}</b>
<code>Default Upload   :</code> <b>{du}</b>
<code>Upload Paths     :</code> <b>{upload_paths}</b>
<code>Name Substitute  :</code> <b>{ns_msg}</b>
<code>Extension Filter :</code> <b>{ex_ex}</b>
<code>YT-DLP Options   :</code> <b>{escape(ytopt)}</b>
"""

    return (
        text,
        buttons.build_menu(1)
    )


async def update_user_settings(query):
    msg, button = await get_user_settings(query.from_user)
    user_id = query.from_user.id
    media = (
        f"Thumbnails/{user_id}.jpg"
        if os_path.exists(f"Thumbnails/{user_id}.jpg")
        else f"{def_media(JAVA.encode()).decode()}"
    )
    await query.message.edit_media(
        media=InputMediaPhoto(
            media=media,
            caption=msg
        ),
        reply_markup=button
    )


@new_thread
async def user_settings(_, message):
    from_user = message.from_user
    if not from_user:
        from_user = await anno_checker(message)
    user_id = from_user.id
    handler_dict[user_id] = False
    msg, button = await get_user_settings(from_user)
    media = (
        f"Thumbnails/{user_id}.jpg"
        if os_path.exists(f"Thumbnails/{user_id}.jpg")
        else f"{def_media(JAVA.encode()).decode()}"
    )
    usetMsg = await message.reply_photo(
        media,
        caption=msg,
        reply_markup=button
    )
    await auto_delete_message(
        message,
        usetMsg
    )


async def set_thumb(_, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    des_dir = await createThumb(
        message,
        user_id
    )
    update_user_ldata(
        user_id,
        "thumb",
        des_dir
    )
    await deleteMessage(message)
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManager().update_user_doc(
            user_id,
            "thumb",
            des_dir
        )


async def add_rclone(_, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    rpath = f"{getcwd()}/rclone/"
    await makedirs(rpath, exist_ok=True)
    des_dir = f"{rpath}{user_id}.conf"
    await message.download(file_name=des_dir)
    update_user_ldata(
        user_id,
        "rclone_config",
        f"rclone/{user_id}.conf"
    )
    await deleteMessage(message)
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManager().update_user_doc(
            user_id,
            "rclone_config",
            des_dir
        )


async def add_token_pickle(_, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    tpath = f"{getcwd()}/tokens/"
    await makedirs(tpath, exist_ok=True)
    des_dir = f"{tpath}{user_id}.pickle"
    await message.download(file_name=des_dir)
    update_user_ldata(
        user_id,
        "token_pickle",
        f"tokens/{user_id}.pickle"
    )
    await deleteMessage(message)
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManager().update_user_doc(
            user_id,
            "token_pickle",
            des_dir
        )


async def delete_path(_, message, pre_event):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})
    names = message.text.split()
    for name in names:
        if name in user_dict["upload_paths"]:
            del user_dict["upload_paths"][name]
    new_value = user_dict["upload_paths"]
    update_user_ldata(
        user_id,
        "upload_paths",
        new_value
    )
    await deleteMessage(message)
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManager().update_user_doc(
            user_id,
            "upload_paths",
            new_value
        )


async def set_option(_, message, pre_event, option):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    if option == "split_size":
        if re_search(r"[a-zA-Z]", value):
            smsg = await sendMessage(
                message,
                "Invalid format! Send only numbers.\nEx: 4, 2, 0.5, 2.5."
            )
            await auto_delete_message(
                message,
                smsg
            )
            await update_user_settings(pre_event)
            return
        value = min(
            ceil(float(value) * 1024 ** 3),
            MAX_SPLIT_SIZE
        )
    elif option == "leech_dest":
        if value.startswith("-") or value.isdigit():
            value = int(value)
    elif option == "excluded_extensions":
        fx = config_dict["EXTENSION_FILTER"].split()
        fx += value.split()
        value = ["aria2", "!qB"]
        for x in fx:
            x = x.lstrip(".")
            value.append(x.strip().lower())
    elif option == "upload_paths":
        user_dict = user_data.get(user_id, {})
        user_dict.setdefault("upload_paths", {})
        lines = value.split("/n")
        for line in lines:
            data = line.split(maxsplit=1)
            if len(data) != 2:
                smsg = await sendMessage(
                    message,
                    "Wrong format! Add <name> <path>"
                )
                await auto_delete_message(
                    message,
                    smsg
                )
                await update_user_settings(pre_event)
                return
            (
                name,
                path
            ) = data
            user_dict["upload_paths"][name] = path
        value = user_dict["upload_paths"]
    update_user_ldata(
        user_id,
        option,
        value
    )
    await deleteMessage(message)
    await update_user_settings(pre_event)
    if DATABASE_URL:
        await DbManager().update_user_data(user_id)


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
        user = (
            event.from_user or
            event.sender_chat
        )
        return bool(
            user.id == user_id
            and event.chat.id == query.message.chat.id
            and mtype
        )

    handler = client.add_handler(
        MessageHandler(
            pfunc,
            filters=create(event_filter)
        ),
        group=-1
    )

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
    name = from_user.mention
    message = query.message
    data = query.data.split()
    handler_dict[user_id] = False
    thumb_path = f"Thumbnails/{user_id}.jpg"
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    user_dict = user_data.get(user_id, {})
    if user_id != int(data[1]):
        await query.answer(
            "Not Yours!",
            show_alert=True
        )
    elif data[2] in [
        "as_doc",
        "equal_splits",
        "media_group",
        "user_transmission",
        "stop_duplicate",
        "mixed_leech",
    ]:
        update_user_ldata(
            user_id,
            data[2],
            data[3] == "true"
        )
        await query.answer()
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManager().update_user_data(user_id)
    elif data[2] in [
        "thumb",
        "rclone_config",
        "token_pickle"
    ]:
        if data[2] == "thumb":
            fpath = thumb_path
        elif data[2] == "rclone_config":
            fpath = rclone_conf
        else:
            fpath = token_pickle
        if await aiopath.exists(fpath):
            await query.answer()
            await remove(fpath)
            update_user_ldata(
                user_id,
                data[2],
                ""
            )
            await update_user_settings(query)
            if DATABASE_URL:
                await DbManager().update_user_doc(
                    user_id,
                    data[2]
                )
        else:
            await query.answer(
                "Old Settings",
                show_alert=True
            )
            await update_user_settings(query)
    elif data[2] in [
        "yt_opt",
        "lprefix",
        "lsuffix",
        "lcapfont",
        "index_url",
        "excluded_extensions",
        "name_sub",
    ]:
        await query.answer()
        update_user_ldata(
            user_id,
            data[2],
            f"{GLOBAL_EXTENSION_FILTER}"
        )
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManager().update_user_data(user_id)
    elif data[2] in [
        "split_size",
        "leech_dest",
        "rclone_path",
        "gdrive_id"
    ]:
        await query.answer()
        if data[2] in user_data.get(user_id, {}):
            del user_data[user_id][data[2]]
            await update_user_settings(query)
            if DATABASE_URL:
                await DbManager().update_user_data(user_id)
    elif data[2] == "leech":
        await query.answer()
        thumbpath = f"Thumbnails/{user_id}.jpg"
        buttons = ButtonMaker()
        buttons.ibutton(
            "Thumbnail",
            f"userset {user_id} sthumb"
        )
        thumbmsg = (
            "Exists"
            if await aiopath.exists(thumbpath)
            else "Not Exists"
        )
        buttons.ibutton(
            "Leech Split Size",
            f"userset {user_id} lss"
        )
        if user_dict.get(
            "split_size",
            False
        ):
            split_size = user_dict["split_size"]
        else:
            split_size = config_dict["LEECH_SPLIT_SIZE"]
        split_size = get_readable_file_size(split_size)
        buttons.ibutton(
            "Leech Destination",
            f"userset {user_id} ldest"
        )
        if user_dict.get(
            "leech_dest",
            False
        ):
            leech_dest = user_dict["leech_dest"]
        elif (
            "leech_dest" not in user_dict
            and (LD := config_dict["USER_LEECH_DESTINATION"])
        ):
            leech_dest = LD
        else:
            leech_dest = "None"
        buttons.ibutton(
            "Leech Prefix",
            f"userset {user_id} leech_prefix"
        )
        if user_dict.get(
            "lprefix",
            False
        ):
            lprefix = user_dict["lprefix"]
        elif "lprefix" not in user_dict and (
            LP := config_dict["LEECH_FILENAME_PREFIX"]
        ):
            lprefix = LP
        else:
            lprefix = "None"
        buttons.ibutton(
            "Leech Suffix",
            f"userset {user_id} leech_suffix"
        )
        if user_dict.get(
            "lsuffix",
            False
        ):
            lsuffix = user_dict["lsuffix"]
        elif "lsuffix" not in user_dict and (
            LS := config_dict["LEECH_FILENAME_SUFFIX"]
        ):
            lsuffix = LS
        else:
            lsuffix = "None"
        buttons.ibutton(
            "Leech Caption Font",
            f"userset {user_id} leech_cap_font"
        )
        if user_dict.get(
            "lcapfont",
            False
        ):
            lcapfont = user_dict["lcapfont"]
        elif "lcapfont" not in user_dict and (
            LC := config_dict["LEECH_CAPTION_FONT"]
        ):
            lcapfont = LC
        else:
            lcapfont = "None"
        if (
            user_dict.get(
                "as_doc",
                False
            )
            or "as_doc" not in user_dict
            and config_dict["AS_DOCUMENT"]
        ):
            ltype = "DOCUMENT"
            buttons.ibutton(
                "Send As Media",
                f"userset {user_id} as_doc false"
            )
        else:
            ltype = "MEDIA"
            buttons.ibutton(
                "Send As Document",
                f"userset {user_id} as_doc true"
            )
        if (
            user_dict.get(
                "equal_splits",
                False
            )
            or "equal_splits" not in user_dict
            and config_dict["EQUAL_SPLITS"]
        ):
            buttons.ibutton(
                "Disable Equal Splits",
                f"userset {user_id} equal_splits false"
            )
            equal_splits = "Enabled"
        else:
            buttons.ibutton(
                "Enable Equal Splits",
                f"userset {user_id} equal_splits true"
            )
            equal_splits = "Disabled"
        if (
            user_dict.get(
                "media_group",
                False
            )
            or "media_group" not in user_dict
            and config_dict["MEDIA_GROUP"]
        ):
            buttons.ibutton(
                "Disable Media Group",
                f"userset {user_id} media_group false"
            )
            media_group = "Enabled"
        else:
            buttons.ibutton(
                "Enable Media Group",
                f"userset {user_id} media_group true"
            )
            media_group = "Disabled"
        if (
            IS_PREMIUM_USER
            and user_dict.get(
                "user_transmission",
                False
            )
            or "user_transmission" not in user_dict
            and config_dict["USER_TRANSMISSION"]
        ):
            buttons.ibutton(
                "Upload with Bot",
                f"userset {user_id} user_transmission false"
            )
            leech_method = "user"
        elif IS_PREMIUM_USER:
            leech_method = "bot"
            buttons.ibutton(
                "Upload with User",
                f"userset {user_id} user_transmission true"
            )
        else:
            leech_method = "bot"

        if (
            IS_PREMIUM_USER
            and user_dict.get(
                "mixed_leech",
                False
            )
            or "mixed_leech" not in user_dict
            and config_dict["MIXED_LEECH"]
        ):
            mixed_leech = "Enabled"
            buttons.ibutton(
                "Disable Hybrid Upload",
                f"userset {user_id} mixed_leech false"
            )
        elif IS_PREMIUM_USER:
            mixed_leech = "Disabled"
            buttons.ibutton(
                "Enable Hybrid Upload",
                f"userset {user_id} mixed_leech true"
            )
        else:
            mixed_leech = "Disabled"

        buttons.ibutton(
            "Back",
            f"userset {user_id} back"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        text = f"""
<b><u>Leech Settings for {name}</u></b>

<code>Leech Type       :</code> <b>{ltype}</b>
<code>Leech Split Size :</code> <b>{split_size}</b>
<code>Leech Prefix     :</code> <b>{escape(lprefix)}</b>
<code>Leech Suffix     :</code> <b>{escape(lsuffix)}</b>
<code>Leech Cap Font   :</code> <b>{escape(lcapfont)}</b>
<code>Leech Destination:</code> <b>{leech_dest}</b>

<code>Thumbnail        :</code> <b>{thumbmsg}</b>
<code>Equal Splits     :</code> <b>{equal_splits}</b>
<code>Media Group      :</code> <b>{media_group}</b>
<code>Upload Client    :</code> <b>{leech_method} session</b>
<code>Hybrid Upload    :</code> <b>{mixed_leech}</b>
"""
        await editMessage(
            message,
            text,
            buttons.build_menu(1)
        )
    elif data[2] == "rclone":
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton(
            "Rclone Config",
            f"userset {user_id} rcc"
        )
        buttons.ibutton(
            "Default Rclone Path",
            f"userset {user_id} rcp"
        )
        buttons.ibutton(
            "Back",
            f"userset {user_id} back"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        rccmsg = (
            "Exists"
            if await aiopath.exists(rclone_conf)
            else "Not Exists"
        )
        if user_dict.get(
            "rclone_path",
            False
        ):
            rccpath = user_dict["rclone_path"]
        elif RP := config_dict["RCLONE_PATH"]:
            rccpath = RP
        else:
            rccpath = "None"
        text = f"""
<b><u>Rclone Settings for {name}</u></b>

<code>Rclone Config :</code> <b>{rccmsg}</b>
<code>Rclone Path   :</code> <b>{rccpath}</b>
"""
        await editMessage(
            message,
            text,
            buttons.build_menu(1)
        )
    elif data[2] == "gdrive":
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton(
            "token.pickle",
            f"userset {user_id} token"
        )
        buttons.ibutton(
            "Default Gdrive ID",
            f"userset {user_id} gdid"
        )
        buttons.ibutton(
            "Index URL",
            f"userset {user_id} index"
        )
        if (
            user_dict.get(
                "stop_duplicate",
                False
            )
            or "stop_duplicate" not in user_dict
            and config_dict["STOP_DUPLICATE"]
        ):
            buttons.ibutton(
                "Disable Stop Duplicate",
                f"userset {user_id} stop_duplicate false"
            )
            sd_msg = "Enabled"
        else:
            buttons.ibutton(
                "Enable Stop Duplicate",
                f"userset {user_id} stop_duplicate true"
            )
            sd_msg = "Disabled"
        buttons.ibutton(
            "Back",
            f"userset {user_id} back"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        tokenmsg = (
            "Exists"
            if await aiopath.exists(token_pickle)
            else "Not Exists"
        )
        if user_dict.get(
            "gdrive_id",
            False
        ):
            gdrive_id = user_dict["gdrive_id"]
        elif GDID := config_dict["GDRIVE_ID"]:
            gdrive_id = GDID
        else:
            gdrive_id = "None"
        index = (
            user_dict["index_url"]
            if user_dict.get(
                "index_url",
                False
            )
            else "None"
        )
        text = f"""
<b><u>Gdrive Tools Settings for {name}</u></b>

<code>Gdrive Token   :</code> <b>{tokenmsg}</b>

<code>Gdrive ID      :</code> <b>{gdrive_id}</b>
<code>Index Link     :</code> <b>{index}</b>

<code>Stop Duplicate :</code> <b>{sd_msg}</b>
"""
        await editMessage(
            message,
            text,
            buttons.build_menu(1)
        )
    elif data[2] == "sthumb":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(thumb_path):
            buttons.ibutton(
                "Delete Thumbnail",
                f"userset {user_id} thumb"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} leech"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message,
            "Send a photo to save it as custom thumbnail. Timeout: 60 sec",
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_thumb,
            pre_event=query
        )
        await event_handler(
            client,
            query,
            pfunc,
            True
        )
    elif data[2] == "yto":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get(
            "yt_opt",
            False
        ) or config_dict["YT_DLP_OPTIONS"]:
            buttons.ibutton(
                "Remove YT-DLP Options",
                f"userset {user_id} yt_opt",
                "header"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} back"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        rmsg = """
Send YT-DLP Options. Timeout: 60 sec

Format: key:value|key:value|key:value.

Example: format:bv*+mergeall[vcodec=none]|nocheckcertificate:True

Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a>
or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.
"""
        await editMessage(
            message,
            rmsg,
            buttons.build_menu(1)
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="yt_opt"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "lss":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get(
            "split_size",
            False
        ):
            buttons.ibutton(
                "Reset Split Size",
                f"userset {user_id} split_size"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} leech"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        sp_msg = "Send Leech split size.\nDon't add unit(MB, GB), default unit is <b>GB</b>\n"
        sp_msg += "\nExamples:\nSend 4 for 4GB\nor 0.5 for 512MB\n\nTimeout: 60 sec"
        await editMessage(
            message,
            sp_msg,
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="split_size"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "rcc":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(rclone_conf):
            buttons.ibutton(
                "Delete rclone.conf",
                f"userset {user_id} rclone_config"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} rclone"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message, "Send rclone.conf. Timeout: 60 sec", buttons.build_menu(1)
        )
        pfunc = partial(
            add_rclone,
            pre_event=query
        )
        await event_handler(
            client,
            query,
            pfunc,
            document=True
        )
    elif data[2] == "rcp":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get(
            "rclone_path",
            False
        ):
            buttons.ibutton(
                "Reset Rclone Path",
                f"userset {user_id} rclone_path"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} rclone"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        rmsg = "Send Rclone Path. Timeout: 60 sec"
        await editMessage(
            message,
            rmsg,
            buttons.build_menu(1)
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="rclone_path"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "token":
        await query.answer()
        buttons = ButtonMaker()
        if await aiopath.exists(token_pickle):
            buttons.ibutton(
                "Delete token.pickle",
                f"userset {user_id} token_pickle"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} gdrive"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message, "Send token.pickle. Timeout: 60 sec",
            buttons.build_menu(1)
        )
        pfunc = partial(
            add_token_pickle,
            pre_event=query
        )
        await event_handler(
            client,
            query,
            pfunc,
            document=True
        )
    elif data[2] == "gdid":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get(
            "gdrive_id",
            False
        ):
            buttons.ibutton(
                "Reset Gdrive ID",
                f"userset {user_id} gdrive_id"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} gdrive"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        rmsg = "Send Gdrive ID. Timeout: 60 sec"
        await editMessage(
            message,
            rmsg,
            buttons.build_menu(1)
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="gdrive_id"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "index":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get(
            "index_url",
            False
        ):
            buttons.ibutton(
                "Remove Index URL",
                f"userset {user_id} index_url"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} gdrive"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        rmsg = "Send Index URL. Timeout: 60 sec"
        await editMessage(
            message,
            rmsg,
            buttons.build_menu(1)
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="index_url"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "leech_prefix":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get(
                "lprefix",
                False
            )
            or "lprefix" not in user_dict
            and config_dict["LEECH_FILENAME_PREFIX"]
        ):
            buttons.ibutton(
                "Remove Leech Prefix",
                f"userset {user_id} lprefix"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} leech"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message,
            "Send Leech Filename Prefix. You can add HTML tags. Timeout: 60 sec",
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="lprefix"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "leech_suffix":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get(
                "lsuffix",
                False
            )
            or "lsuffix" not in user_dict
            and config_dict["LEECH_FILENAME_SUFFIX"]
        ):
            buttons.ibutton(
                "Remove Leech Suffix",
                f"userset {user_id} lsuffix"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} leech"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message,
            "Send Leech Filename Suffix. You can add HTML tags. Timeout: 60 sec",
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="lsuffix"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "leech_cap_font":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get(
                "lcapfont",
                False
            )
            or "lcapfont" not in user_dict
            and config_dict["LEECH_CAPTION_FONT"]
        ):
            buttons.ibutton(
                "Remove Leech Caption Font",
                f"userset {user_id} lcapfont"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} leech"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        msg = """
Send Leech Caption Font. Default is regular.

Options:
b or bold for <b>bold</b>
i or italic for <i>italic</i>
u or underline for <u>underline</u>
bi for <b><i>bold italic</i></b>
bu for <b><u>bold underline</u></b>
iu for <i><u>italic underline</u></i>
biu for <b><i><u>bold italic underline</u></i></b>
m or mono or monospace for <code>monospace</code>

Timeout: 60 sec
"""
        await editMessage(
            message,
            msg,
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="lcapfont"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "ldest":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get(
                "leech_dest",
                False
            )
            or "leech_dest" not in user_dict
            and config_dict["USER_LEECH_DESTINATION"]
        ):
            buttons.ibutton(
                "Reset Leech Destination",
                f"userset {user_id} leech_dest"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} leech"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message,
            "Send leech destination ID/USERNAME/PM. Timeout: 60 sec",
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="leech_dest"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "ex_ex":
        await query.answer()
        buttons = ButtonMaker()
        if (
            user_dict.get(
                "excluded_extensions",
                False
            )
            or "excluded_extensions" not in user_dict
            and GLOBAL_EXTENSION_FILTER
        ):
            buttons.ibutton(
                "Remove Excluded Extensions",
                f"userset {user_id} excluded_extensions"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} back"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        ex_msg = "<b>Send exluded extenions seperated by space without dot at beginning.</b>\n"
        ex_msg += "<b>Ex:</b> <code>zip mp4 jpg</code>\n<b>Timeout:</b> 60 sec\n\n"
        ex_msg += f"<b>Added by Owner:</b> <code>{GLOBAL_EXTENSION_FILTER}</code>"
        await editMessage(
            message,
            ex_msg,
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="excluded_extensions"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "name_substitute":
        await query.answer()
        buttons = ButtonMaker()
        if user_dict.get(
            "name_sub",
            False
        ):
            buttons.ibutton(
                "Remove Name Substitute",
                f"userset {user_id} name_sub"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} back"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        emsg = r"""
Word Substitutions. You can add pattern instead of normal text. Timeout: 60 sec

NOTE: You must add \ before any character, those are the characters: \^$.|?*+()[]{}-

Example-1: text : code : s|mirror : leech|tea :  : s|clone

1. text will get replaced by code with sensitive case
2. mirror will get replaced by leech
4. tea will get removed with sensitive case
5. clone will get removed

Example-2: \(text\) | \[test\] : test | \\text\\ : text : s
1. (text) will get removed
2. [test] will get replaced by test
3. \text\ will get replaced by text with sensitive case
"""
        emsg += f"Your Current Value is {user_dict.get('name_sub') or 'not added yet!'}"
        await editMessage(
            message,
            emsg,
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="name_sub"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] in [
        "gd",
        "rc"
    ]:
        await query.answer()
        du = (
            "rc"
            if data[2] == "gd"
            else "gd"
        )
        update_user_ldata(
            user_id,
            "default_upload",
            du
        )
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManager().update_user_data(user_id)
    elif data[2] == "upload_paths":
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton(
            "New Path",
            f"userset {user_id} new_path"
        )
        if user_dict.get(
            data[2],
            False
        ):
            buttons.ibutton(
                "Show All Paths",
                f"userset {user_id} show_path"
            )
            buttons.ibutton(
                "Remove Path",
                f"userset {user_id} rm_path"
            )
        buttons.ibutton(
            "Back",
            f"userset {user_id} back"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message,
            "Add or remove upload path.\n",
            buttons.build_menu(1),
        )
    elif data[2] == "new_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton(
            "Back",
            f"userset {user_id} upload_paths"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message,
            "Send path name(no space in name) which you will use it as a shortcut and the path/id seperated by space. You can add multiple names and paths separated by new line. Timeout: 60 sec",
            buttons.build_menu(1),
        )
        pfunc = partial(
            set_option,
            pre_event=query,
            option="upload_paths"
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "rm_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton(
            "Back",
            f"userset {user_id} upload_paths"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        await editMessage(
            message,
            "Send paths names which you want to delete, separated by space. Timeout: 60 sec",
            buttons.build_menu(1),
        )
        pfunc = partial(
            delete_path,
            pre_event=query
        )
        await event_handler(
            client,
            query,
            pfunc
        )
    elif data[2] == "show_path":
        await query.answer()
        buttons = ButtonMaker()
        buttons.ibutton(
            "Back",
            f"userset {user_id} upload_paths"
        )
        buttons.ibutton(
            "Close",
            f"userset {user_id} close"
        )
        user_dict = user_data.get(
            user_id,
            {}
        )
        msg = "".join(
            f"<b>{key}</b>: <code>{value}</code>\n"
            for key, value in user_dict["upload_paths"].items()
        )
        await editMessage(
            message,
            msg,
            buttons.build_menu(1),
        )
    elif data[2] == "reset":
        await query.answer()
        if ud := user_data.get(
            user_id,
            {}
        ):
            if ud and (
                "is_sudo" in ud or
                "is_auth" in ud
            ):
                for k in list(ud.keys()):
                    if k not in [
                        "is_sudo",
                        "is_auth"
                    ]:
                        del user_data[user_id][k]
            else:
                user_data[user_id].clear()
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManager().update_user_data(user_id)
        for fpath in [
            thumb_path,
            rclone_conf,
            token_pickle
        ]:
            if await aiopath.exists(fpath):
                await remove(fpath)
    elif data[2] == "back":
        await query.answer()
        await update_user_settings(query)
    else:
        await query.answer()
        await deleteMessage(message.reply_to_message)
        await deleteMessage(message)


async def send_users_settings(_, message):
    if user_data:
        msg = ""
        for u, d in user_data.items():
            kmsg = f"\n<b>{u}:</b>\n"
            if vmsg := "".join(
                f"{k}: <code>{v}</code>\n"
                for k, v in d.items()
                if f"{v}"
            ):
                msg += kmsg + vmsg

        msg_ecd = msg.encode()
        if len(msg_ecd) > 4000:
            with BytesIO(msg_ecd) as ofile:
                ofile.name = "users_settings.txt"
                await sendFile(
                    message,
                    ofile
                )
        else:
            await sendMessage(
                message,
                msg
            )
    else:
        await sendMessage(
            message,
            "No users data!"
        )


bot.add_handler( # type: ignore
    MessageHandler(
        send_users_settings,
        filters=command(
            BotCommands.UsersCommand
        ) & CustomFilters.sudo,
    )
)
bot.add_handler( # type: ignore
    MessageHandler(
        user_settings,
        filters=command(
            BotCommands.UserSetCommand
        ) & CustomFilters.authorized,
    )
)
bot.add_handler( # type: ignore
    CallbackQueryHandler(
        edit_user_settings,
        filters=regex("^userset")
    )
)
