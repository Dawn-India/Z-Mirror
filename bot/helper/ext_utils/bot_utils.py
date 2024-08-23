from asyncio import (
    create_subprocess_exec,
    create_subprocess_shell,
    run_coroutine_threadsafe,
    sleep,
)
from asyncio.subprocess import PIPE
from functools import partial, wraps

from nekozee.types import BotCommand
from httpx import AsyncClient

from bot import (
    user_data,
    config_dict,
    bot_loop,
    extra_buttons
)
from bot.helper.ext_utils.help_messages import (
    YT_HELP_DICT,
    MIRROR_HELP_DICT,
    CLONE_HELP_DICT,
)
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands

COMMAND_USAGE = {}


class setInterval:
    def __init__(self, interval, action, *args, **kwargs):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(
            self._set_interval(
                *args,
                **kwargs
            )
        )

    async def _set_interval(self, *args, **kwargs):
        while True:
            await sleep(self.interval)
            await self.action(
                *args,
                **kwargs
            )

    def cancel(self):
        self.task.cancel()


def create_help_buttons():
    buttons = ButtonMaker()
    for name in list(MIRROR_HELP_DICT.keys())[1:]:
        buttons.ibutton(
            name,
            f"help mirror {name}"
        )
    buttons.ibutton(
        "ᴄʟᴏꜱᴇ",
        "help close"
    )
    COMMAND_USAGE["mirror"] = [
        MIRROR_HELP_DICT["main"],
        buttons.build_menu(2)
    ]
    buttons.reset()
    for name in list(YT_HELP_DICT.keys())[1:]:
        buttons.ibutton(
            name,
            f"help yt {name}"
        )
    buttons.ibutton(
        "ᴄʟᴏꜱᴇ",
        "help close"
    )
    COMMAND_USAGE["yt"] = [
        YT_HELP_DICT["main"],
        buttons.build_menu(2)
    ]
    buttons.reset()
    for name in list(CLONE_HELP_DICT.keys())[1:]:
        buttons.ibutton(
            name,
            f"help clone {name}"
        )
    buttons.ibutton(
        "ᴄʟᴏꜱᴇ",
        "help close"
    )
    COMMAND_USAGE["clone"] = [
        CLONE_HELP_DICT["main"],
        buttons.build_menu(2)
    ]


def bt_selection_buttons(id_):
    gid = (
        id_[:12]
        if len(id_) > 25
        else id_
    )
    pincode = "".join(
        [
            n
            for n
            in id_
            if n.isdigit()
        ][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict["BASE_URL"]
    if config_dict["WEB_PINCODE"]:
        buttons.ubutton(
            "ꜱᴇʟᴇᴄᴛ ꜰɪʟᴇꜱ",
            f"{BASE_URL}/app/files/{id_}"
        )
        buttons.ibutton(
            "ᴘɪɴᴄᴏᴅᴇ",
            f"sel pin {gid} {pincode}"
        )
    else:
        buttons.ubutton(
            "ꜱᴇʟᴇᴄᴛ ꜰɪʟᴇꜱ",
            f"{BASE_URL}/app/files/{id_}?pin_code={pincode}"
        )
    buttons.ibutton(
        "ᴅᴏɴᴇ ꜱᴇʟᴇᴄᴛɪɴɢ",
        f"sel done {gid} {id_}"
    )
    buttons.ibutton(
        "ᴄʟᴏꜱᴇ",
        f"sel cancel {gid}"
    )
    return buttons.build_menu(2)


def extra_btns(buttons):
    if extra_buttons:
        for (
            btn_name,
            btn_url
        ) in extra_buttons.items():
            buttons.ubutton(
                btn_name,
                btn_url
            )
    return buttons


async def set_commands(client):
    if config_dict["SET_COMMANDS"]:
        await client.set_bot_commands([
            BotCommand(
                f"{BotCommands.MirrorCommand[0]}",
                "ᴍɪʀʀᴏʀ ᴅɪʀᴇᴄᴛ ʟɪɴᴋꜱ ᴜꜱɪɴɢ ᴀʀɪᴀ2ᴄ"
            ),
            BotCommand(
                f"{BotCommands.JdMirrorCommand[0]}",
                "ᴍɪʀʀᴏʀ ᴊᴅᴏᴡɴʟᴏᴀᴅᴇʀ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋꜱ"
            ),
            BotCommand(
                f"{BotCommands.NzbMirrorCommand[0]}",
                "ᴍɪʀʀᴏʀ ꜱᴀʙɴᴢʙᴅ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋꜱ ᴏʀ ꜰɪʟᴇꜱ"
            ),
            BotCommand(
                f"{BotCommands.QbMirrorCommand[0]}",
                "ᴍɪʀʀᴏʀ Qʙɪᴛ-ᴛᴏʀʀᴇɴᴛ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋꜱ ᴏʀ ꜰɪʟᴇꜱ"
            ),
            BotCommand(
                f"{BotCommands.YtdlCommand[0]}",
                "ᴍɪʀʀᴏʀ ʏᴛ-ᴅʟᴘ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋꜱ"
            ),
            BotCommand(
                f"{BotCommands.LeechCommand[0]}",
                "ʟᴇᴇᴄʜ ᴅɪʀᴇᴄᴛ ʟɪɴᴋꜱ ᴜꜱɪɴɢ ᴀʀɪᴀ2ᴄ"
            ),
            BotCommand(
                f"{BotCommands.JdLeechCommand[0]}",
                "ʟᴇᴇᴄʜ ᴊᴅᴏᴡɴʟᴏᴀᴅᴇʀ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋꜱ"
            ),
            BotCommand(
                f"{BotCommands.NzbLeechCommand[0]}",
                "ʟᴇᴇᴄʜ ꜱᴀʙɴᴢʙᴅ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋꜱ ᴏʀ ꜰɪʟᴇꜱ"
            ),
            BotCommand(
                f"{BotCommands.QbLeechCommand[0]}",
                "ʟᴇᴇᴄʜ Qʙɪᴛ-ᴛᴏʀʀᴇɴᴛ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋꜱ ᴏʀ ꜰɪʟᴇꜱ"
            ),
            BotCommand(
                f"{BotCommands.YtdlLeechCommand[0]}",
                "ʟᴇᴇᴄʜ ʏᴛ-ᴅʟᴘ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋꜱ"
            ),
            BotCommand(
                f"{BotCommands.CloneCommand}",
                "ᴄᴏᴘʏ ꜰɪʟᴇ ᴏʀ ꜰᴏʟᴅᴇʀ ᴛᴏ ᴛʜᴇ ᴅʀɪᴠᴇ"
            ),
            BotCommand(
                f"{BotCommands.CountCommand}",
                "[ᴅʀɪᴠᴇ ᴜʀʟ]: ᴄᴏᴜɴᴛ ꜰɪʟᴇ ᴏʀ ꜰᴏʟᴅᴇʀ ᴏꜰ ᴛʜᴇ ɢᴏᴏɢʟᴇ ᴅʀɪᴠᴇ"
            ),
            BotCommand(
                f"{BotCommands.StatusCommand[0]}",
                "ɢᴇᴛ ᴀʟʟ ᴛᴀꜱᴋꜱ ꜱᴛᴀᴛᴜꜱ ᴍᴇꜱꜱᴀɢᴇ"
            ),
            BotCommand(
                f"{BotCommands.StatsCommand[0]}",
                "ᴄʜᴇᴄᴋ ʙᴏᴛ ꜱᴛᴀᴛꜱ"
            ),
            BotCommand(
                f"{BotCommands.CancelTaskCommand[0]}",
                "ᴄᴀɴᴄᴇʟ ᴀ ᴛᴀꜱᴋ"
            ),
            BotCommand(
                f"{BotCommands.CancelAllCommand}",
                "ᴄᴀɴᴄᴇʟ ᴀʟʟ ᴛᴀꜱᴋꜱ ᴡʜɪᴄʜ ᴀᴅᴅᴇᴅ ʙʏ ʏᴏᴜ"
            ),
            BotCommand(
                f"{BotCommands.ListCommand}",
                "ꜱᴇᴀʀᴄʜ ɪɴ ᴅʀɪᴠᴇ"
            ),
            BotCommand(
                f"{BotCommands.SearchCommand}",
                "ꜱᴇᴀʀᴄʜ ɪɴ ᴛᴏʀʀᴇɴᴛ"
            ),
            BotCommand(
                f"{BotCommands.UserSetCommand[0]}",
                "ᴜꜱᴇʀꜱ ꜱᴇᴛᴛɪɴɢꜱ"
            ),
            BotCommand(
                f"{BotCommands.HelpCommand}",
                "ɢᴇᴛ ᴅᴇᴛᴀɪʟᴇᴅ ʜᴇʟᴘ"
            ),
        ])


async def get_telegraph_list(telegraph_content):
    path = [
        (
            await telegraph.create_page(
                title="ᴢ-ᴍɪʀʀᴏʀ ᴅʀɪᴠᴇ ꜱᴇᴀʀᴄʜ",
                content=content
            )
        )["path"]
        for content in telegraph_content
    ]
    if len(path) > 1:
        await telegraph.edit_telegraph(
            path,
            telegraph_content
        )
    buttons = ButtonMaker()
    buttons.ubutton(
        "🔎 ᴠɪᴇᴡ\nʀᴇꜱᴜʟᴛꜱ",
        f"https://telegra.ph/{path[0]}"
    )
    return buttons.build_menu(1)


def arg_parser(items, arg_base):
    if not items:
        return
    bool_arg_set = {
        "-b",
        "-e",
        "-z",
        "-s",
        "-j",
        "-d",
        "-sv",
        "-ss",
        "-f",
        "-fd",
        "-fu",
        "-sync",
        "-ml",
    }
    t = len(items)
    i = 0
    arg_start = -1

    while i + 1 <= t:
        part = items[i]
        if part in arg_base:
            if arg_start == -1:
                arg_start = i
            if (
                i + 1 == t
                and part in bool_arg_set
                or part in [
                    "-s",
                    "-j",
                    "-f",
                    "-fd",
                    "-fu",
                    "-sync",
                    "-ml"
                ]
            ):
                arg_base[part] = True
            else:
                sub_list = []
                for j in range(i + 1, t):
                    item = items[j]
                    if item in arg_base:
                        if (
                            part in bool_arg_set
                            and not sub_list
                        ):
                            arg_base[part] = True
                        break
                    sub_list.append(item)
                    i += 1
                if sub_list:
                    arg_base[part] = " ".join(sub_list)
        i += 1
    if (
        "link" in arg_base
        and items[0] not in arg_base
    ):
        link = []
        if arg_start == -1:
            link.extend(iter(items))
        else:
            link.extend(items[r] for r in range(arg_start))
        if link:
            arg_base["link"] = " ".join(link)


def getSizeBytes(size):
    size = size.lower()
    if size.endswith("mb"):
        size = size.split("mb")[0]
        size = int(float(size) * 1048576)
    elif size.endswith("gb"):
        size = size.split("gb")[0]
        size = int(float(size) * 1073741824)
    else:
        size = 0
    return size


async def get_content_type(url):
    try:
        async with AsyncClient() as client:
            response = await client.get(
                url,
                allow_redirects=True,
                verify=False
            )
            return response.headers.get("Content-Type")
    except:
        return None


def update_user_ldata(id_, key, value):
    user_data.setdefault(id_, {})
    user_data[id_][key] = value


async def retry_function(func, *args, **kwargs):
    try:
        return await func(
            *args,
            **kwargs
        )
    except:
        return await retry_function(
            func,
            *args,
            **kwargs
        )


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(
            cmd,
            stdout=PIPE,
            stderr=PIPE
        )
    else:
        proc = await create_subprocess_exec(
            *cmd,
            stdout=PIPE,
            stderr=PIPE
        )
    (
        stdout,
        stderr
    ) = await proc.communicate()
    try:
        stdout = stdout.decode().strip()
    except:
        stdout = "Unable to decode the response!"
    try:
        stderr = stderr.decode().strip()
    except:
        stderr = "Unable to decode the error!"
    return (
        stdout,
        stderr,
        proc.returncode
    )


def new_task(func):
    @wraps(func)
    def wrapper(
        *args,
        **kwargs
    ):
        bot_loop.create_task(
            func(
                *args,
                **kwargs
            )
        )

        async def dummy():
            pass

        return dummy

    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(
        func,
        *args,
        **kwargs
    )
    future = bot_loop.run_in_executor(
        None,
        pfunc
    )
    return (
        await future
        if wait
        else future
    )


def async_to_sync(func, *args, wait=True, **kwargs):
    future = run_coroutine_threadsafe(
        func(
            *args,
            **kwargs
        ),
        bot_loop
    )
    return (
        future.result()
        if wait
        else future
    )


def new_thread(func):
    @wraps(func)
    def wrapper(
        *args,
        wait=False,
        **kwargs
    ):
        future = run_coroutine_threadsafe(
            func(
                *args,
                **kwargs
            ),
            bot_loop
        )
        return (
            future.result()
            if wait
            else future
        )

    return wrapper
