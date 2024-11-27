from aiofiles.os import (
    makedirs,
    path as aiopath,
    remove
)
from asyncio import (
    create_subprocess_exec,
    gather,
    sleep
)
from asyncio.subprocess import PIPE
from os import (
    path as ospath,
    walk
)
from secrets import token_urlsafe
from aioshutil import (
    copy2,
    move
)
from nekozee.enums import ChatAction
from re import (
    sub,
    I
)

from bot import (
    DOWNLOAD_DIR,
    LOGGER,
    IS_PREMIUM_USER,
    MAX_SPLIT_SIZE,
    bot,
    config_dict,
    cpu_eater_lock,
    global_extension_filter,
    intervals,
    multi_tags,
    subprocess_lock,
    task_dict_lock,
    task_dict,
    user_data,
    user
)
from .ext_utils.bot_utils import (
    get_size_bytes,
    new_task,
    sync_to_async
)
from .ext_utils.bulk_links import extract_bulk_links
from .ext_utils.exceptions import NotSupportedExtractionArchive
from .ext_utils.files_utils import (
    clean_target,
    get_base_name,
    get_path_size,
    is_first_archive_split,
    is_archive,
    is_archive_split
)
from .ext_utils.links_utils import (
    is_gdrive_id,
    is_rclone_path,
    is_gdrive_link,
    is_telegram_link
)
from .ext_utils.media_utils import (
    add_attachment,
    create_thumb,
    create_sample_video,
    edit_video_metadata,
    take_ss
)
from .ext_utils.media_utils import (
    convert_video,
    convert_audio,
    split_file,
    get_document_type
)
from .task_utils.gdrive_utils.list import GoogleDriveList
from .task_utils.rclone_utils.list import RcloneList
from .task_utils.status_utils.extract_status import ExtractStatus
from .task_utils.status_utils.sample_video_status import (
    SampleVideoStatus,
)
from .task_utils.status_utils.media_convert_status import (
    MediaConvertStatus,
)
from .task_utils.status_utils.meta_status import MetaStatus
from .task_utils.status_utils.split_status import SplitStatus
from .task_utils.status_utils.zip_status import ZipStatus
from .telegram_helper.bot_commands import BotCommands
from .telegram_helper.message_utils import (
    anno_checker,
    auto_delete_message,
    delete_links,
    delete_message,
    edit_message,
    get_tg_link_message,
    is_admin,
    is_bot_can_dm,
    request_limiter,
    send_to_chat,
    send_message,
    send_log_message,
    send_status_message
)
from .z_utils import (
    none_admin_utils,
    stop_duplicate_tasks
)


class TaskConfig:
    def __init__(self):
        self.mid = self.message.id # type: ignore
        self.user = None
        self.user_id = None
        self.user_dict = {}
        self.dir = f"{DOWNLOAD_DIR}{self.mid}"
        self.link = ""
        self.up_dest = ""
        self.rc_flags = ""
        self.tag = ""
        self.name = ""
        self.new_dir = ""
        self.name_sub = ""
        self.mode = ""
        self.time = ""
        self.chat_id = ""
        self.thumbnail_layout = ""
        self.metadata = None
        self.m_attachment = None
        self.folder_name = ""
        self.get_chat = None
        self.split_size = 0
        self.max_split_size = 0
        self.multi = 0
        self.size = 0
        self.is_leech = False
        self.is_qbit = False
        self.is_nzb = False
        self.is_jd = False
        self.is_clone = False
        self.is_ytdlp = False
        self.equal_splits = False
        self.user_transmission = False
        self.mixed_leech = False
        self.extract = False
        self.compress = False
        self.select = False
        self.seed = False
        self.compress = False
        self.extract = False
        self.join = False
        self.private_link = False
        self.stop_duplicate = False
        self.sample_video = False
        self.convert_audio = False
        self.convert_video = False
        self.screen_shots = False
        self.is_cancelled = False
        self.force_run = False
        self.force_download = False
        self.force_upload = False
        self.is_torrent = False
        self.is_playlist = False
        self.as_med = False
        self.as_doc = False
        self.suproc = None
        self.thumb = None
        self.dm_message = None
        self.log_message = None
        self.raw_url = None
        self.extension_filter = []
        self.is_super_chat = self.message.chat.type.name in [ # type: ignore
            "SUPERGROUP",
            "CHANNEL"
        ]


    async def get_id(self):
        self.user = self.message.from_user # type: ignore
        if not self.message.from_user: # type: ignore
            self.user = self.message.from_user = await anno_checker( # type: ignore
                self.message, # type: ignore
                self.pmsg # type: ignore
            )
        self.user_id = self.user.id
        self.user_dict = user_data.get(
            self.user_id,
            {}
        )
        self.chat_id = self.message.chat.id # type: ignore
        self.get_chat = await self.client.get_chat(self.chat_id) # type: ignore


    async def set_mode(self):
        mode = (
            "Telegram"
            if self.is_leech
            else
            "RcDrive"
            if (
                self.up_dest == "rc" or
                self.up_dest == "rcl" or
                self.up_dest == "rcu" or
                is_rclone_path(str(self.up_dest)) == True
            )
            else
            "GDrive" if (
                self.is_clone or
                self.up_dest == "gd" or
                self.up_dest == "gdl" or
                self.up_dest == "gdu" or
                is_gdrive_id(str(self.up_dest)) == True
            )
            else
            f"{self.up_dest}"
        )

        if self.compress:
            mode += " as Zip"
        elif self.extract:
            mode += " as Unzip"
        self.mode = mode


    def get_token_path(self, dest):
        if dest.startswith("mtp:"):
            return f"tokens/{self.user_id}.pickle"
        elif (
            dest.startswith("sa:")
            or config_dict["USE_SERVICE_ACCOUNTS"]
            and not dest.startswith("tp:")
        ):
            return "accounts"
        else:
            return "token.pickle"

    def get_config_path(self, dest):
        return (
            f"rclone/{self.user_id}.conf"
            if dest.startswith("mrcc:")
            else "rclone.conf"
        )

    async def is_token_exists(self, path, status):
        if is_rclone_path(path):
            config_path = self.get_config_path(path)
            if (
                config_path != "rclone.conf"
                and status == "up"
            ):
                self.private_link = True
            if not await aiopath.exists(config_path):
                raise ValueError(f"Rclone Config: {config_path} not Exists!")

        elif (
            status == "dl"
            and is_gdrive_link(path)
            or status == "up"
            and is_gdrive_id(path)
        ):
            token_path = self.get_token_path(path)

            if (
                token_path.startswith("tokens/")
                and status == "up"
            ):
                self.private_link = True

            if not await aiopath.exists(token_path):
                raise ValueError(f"NO TOKEN! {token_path} not Exists!")

    async def permission_check(self):
        error_msg = []
        error_button = None

        if not await is_admin(self.message): # type: ignore
            if await request_limiter(self.message): # type: ignore
                await delete_links(self.message) # type: ignore
                return

            self.raw_url = await stop_duplicate_tasks(
                self.message, # type: ignore
                self.link, # type: ignore
                self.file_ # type: ignore
            )

            if self.raw_url == "duplicate_tasks":
                await delete_message(self.pmsg) # type: ignore
                await delete_links(self.message) # type: ignore
                return

            (
                none_admin_msg,
                error_button
            ) = await none_admin_utils(
                self.message, # type: ignore
                self.is_leech
            )

            if none_admin_msg:
                error_msg.extend(none_admin_msg)

        if (
            (dmMode := config_dict["DM_MODE"])
            and self.message.chat.type == self.message.chat.type.SUPERGROUP # type: ignore
        ):
            if (
                self.is_leech 
                and IS_PREMIUM_USER 
                and not config_dict["DUMP_CHAT_ID"]
            ):
                error_msg.append("DM_MODE and User Session need DUMP_CHAT_ID")

            (
                self.dm_message,
                error_button
            ) = await is_bot_can_dm(
                self.message, # type: ignore
                dmMode,
                error_button
            )

            if (
                self.dm_message is not None
                and self.dm_message != "BotStarted"
            ):
                error_msg.append(self.dm_message)

        else:
            self.dm_message = None

        if error_msg:
            final_msg = f"Hey, <b>{self.tag}</b>,\n"

            for (
                _i,
                _msg
            ) in enumerate(
                error_msg,
                1
            ):
                final_msg += f"\n<b>{_i}</b>: {_msg}\n"

            final_msg += f"\n<b>Thank You</b>"

            if error_button is not None:
                error_button = error_button.build_menu(2)

            await delete_links(self.message) # type: ignore
            try:
                mmsg = await edit_message(
                    self.pmsg, # type: ignore
                    final_msg,
                    error_button
                )
            except:
                mmsg = await send_message(
                    self.message, # type: ignore
                    final_msg,
                    error_button
                )

            await auto_delete_message(
                self.pmsg, # type: ignore
                mmsg
            )
            return
        return True

    async def before_start(self):
        if (
            config_dict["DISABLE_SEED"]
            and self.seed
            and not await is_admin(self.message) # type: ignore
        ):
            raise ValueError("Seed is Disabled!")
        self.name_sub = (
            self.name_sub
            or self.user_dict.get(
                "name_sub",
                False
            )
            or (
                config_dict["NAME_SUBSTITUTE"]
                if "name_sub" not in self.user_dict
                else ""
            )
        )
        if self.name_sub:
            self.name_sub = [
                x.split("/")
                for x
                in self.name_sub.split(" | ") # type: ignore
            ]
            self.seed = False
        self.extension_filter = self.user_dict.get("excluded_extensions") or (
            global_extension_filter
            if "excluded_extensions" not in self.user_dict
            else [
                "aria2",
                "!qB"
            ]
        )
        self.metadata = self.metadata or self.user_dict.get("metatxt") or (
            config_dict["METADATA_TXT"]
            if "metatxt" not in self.user_dict
            else False
        )
        self.m_attachment = self.m_attachment or self.user_dict.get("attachmenturl") or (
            config_dict["META_ATTACHMENT"]
            if "attachmenturl" not in self.user_dict
            else False
        )
        if self.link not in [
            "rcl",
            "gdl"
        ]:
            if (not self.is_jd
                and is_rclone_path(self.link)
                or is_gdrive_link(self.link)
            ):
                await self.is_token_exists(
                    self.link,
                    "dl"
                )
        elif self.link == "rcl":
            if (
                not self.is_ytdlp
                and not self.is_jd
            ):
                self.link = await RcloneList(self).get_rclone_path("rcd")
                if not is_rclone_path(self.link):
                    raise ValueError(self.link)
        elif self.link == "gdl":
            if (
                not self.is_ytdlp
                and not self.is_jd
            ):
                self.link = await GoogleDriveList(self).get_target_id("gdd")
                if not is_gdrive_id(self.link):
                    raise ValueError(self.link)

        self.user_transmission = IS_PREMIUM_USER and (
            self.user_dict.get("user_transmission")
            or config_dict["USER_TRANSMISSION"]
            and "user_transmission" not in self.user_dict
        )

        if (
            "upload_paths" in self.user_dict
            and self.up_dest
            and self.up_dest
            in self.user_dict["upload_paths"]
        ):
            self.up_dest = self.user_dict["upload_paths"][self.up_dest]

        if not self.is_leech:
            self.stop_duplicate = (
                self.user_dict.get("stop_duplicate")
                or "stop_duplicate"
                not in self.user_dict
                and config_dict["STOP_DUPLICATE"]
            )
            default_upload = (
                self.user_dict.get(
                    "default_upload",
                    ""
                )
                or config_dict["DEFAULT_UPLOAD"]
            )
            if (
                not self.up_dest
                and default_upload == "rc"
            ) or self.up_dest == "rc":
                self.up_dest = (
                    self.user_dict.get("rclone_path")
                    or config_dict["RCLONE_PATH"]
                )
            elif (
                not self.up_dest
                and default_upload == "gd"
            ) or self.up_dest == "gd":
                self.up_dest = (
                    self.user_dict.get("gdrive_id")
                    or config_dict["GDRIVE_ID"]
                )
            if not self.up_dest:
                raise ValueError("No Upload Destination!")
            if (
                not is_gdrive_id(str(self.up_dest))
                and not is_rclone_path(str(self.up_dest))
            ):
                raise ValueError("Wrong Upload Destination!")
            if (
                self.up_dest
                not in [
                    "rcl",
                    "gdl"
                ]
            ):
                await self.is_token_exists(
                    self.up_dest,
                    "up"
                )

            if self.up_dest == "rcl":
                if self.is_clone:
                    if not is_rclone_path(self.link):
                        raise ValueError(
                            "You can't clone from different types of tools"
                        )
                    config_path = self.get_config_path(self.link)
                else:
                    config_path = None
                self.up_dest = await RcloneList(self).get_rclone_path(
                    "rcu",
                    config_path
                )
                if not is_rclone_path(self.up_dest):
                    raise ValueError(self.up_dest)
            elif self.up_dest == "gdl":
                if self.is_clone:
                    if not is_gdrive_link(self.link):
                        raise ValueError(
                            "You can't clone from different types of tools"
                        )
                    token_path = self.get_token_path(self.link)
                else:
                    token_path = None
                self.up_dest = await GoogleDriveList(self).get_target_id(
                    "gdu",
                    token_path
                )
                if not is_gdrive_id(self.up_dest):
                    raise ValueError(self.up_dest)
            elif self.is_clone:
                if (
                    is_gdrive_link(self.link)
                    and self.get_token_path(self.link)
                    != self.get_token_path(self.up_dest)
                ):
                    raise ValueError("You must use the same token to clone!")
                elif (
                    is_rclone_path(self.link)
                    and self.get_config_path(self.link)
                    != self.get_config_path(self.up_dest)
                ):
                    raise ValueError("You must use the same config to clone!")
        else:
            if self.message.chat.type != self.message.chat.type.SUPERGROUP: # type: ignore
                raise ValueError("Leech is not allowed in private!\nUse me in a supergroup!")
            self.up_dest = (
                self.up_dest
                or self.user_dict.get("leech_dest")
                or config_dict["USER_LEECH_DESTINATION"]
            )
            self.mixed_leech = IS_PREMIUM_USER and (
                self.user_dict.get("mixed_leech")
                or config_dict["MIXED_LEECH"]
                and "mixed_leech"
                not in self.user_dict
            )
            if self.up_dest:
                if not isinstance(
                    self.up_dest,
                    int
                ):
                    if self.up_dest.startswith("b:"):
                        self.up_dest = self.up_dest.replace(
                            "b:",
                            "",
                            1
                        )
                        self.user_transmission = False
                        self.mixed_leech = False
                    elif self.up_dest.startswith("u:"):
                        self.up_dest = self.up_dest.replace(
                            "u:",
                            "",
                            1
                        )
                        self.user_transmission = IS_PREMIUM_USER
                        self.mixed_leech = False
                    elif self.up_dest.startswith("m:"):
                        self.user_transmission = IS_PREMIUM_USER
                        self.mixed_leech = self.user_transmission
                    if (
                        self.up_dest.isdigit()
                        or self.up_dest.startswith("-")
                    ):
                        self.up_dest = int(self.up_dest)
                    elif self.up_dest.lower() in [
                        "pm",
                        "dm"
                    ]:
                        self.up_dest = self.user_id

                udc = user.session.dc_id if user else 0
                bdc = bot.session.dc_id # type: ignore
                if udc != bdc and self.mixed_leech:
                    self.mixed_leech = False

                chat = await self.client.get_chat(self.up_dest) # type: ignore
                uploader_id = self.client.me.id # type: ignore

                if chat.type.name in [
                    "SUPERGROUP",
                    "CHANNEL"
                ]:
                    member = await chat.get_member(uploader_id)
                    if (
                        not member.privileges.can_manage_chat
                        or not member.privileges.can_post_messages 
                    ):
                        raise ValueError(
                            "I don't have enough permissions in the <b>leech destination</b>!\n"
                            "Allow me <b>post messages</b> and <b>manage chat</b> permissions!"
                        )
                else:
                    try:
                        await self.client.send_chat_action( # type: ignore
                            self.up_dest,
                            ChatAction.TYPING
                        )
                    except:
                        raise ValueError("Start me in DM and try again!")

                if config_dict["LOG_CHAT_ID"]:
                    try:
                        log_chat = await self.client.get_chat(config_dict["LOG_CHAT_ID"]) # type: ignore
                    except:
                        raise ValueError("First add me in LOG_CHAT_ID!")
                    if log_chat.type.name != "CHANNEL":
                        raise ValueError(
                            "LOG_CHAT_ID must be a channel!"
                        )
                    member = await log_chat.get_member(uploader_id)
                    if not member.privileges.can_post_messages:
                        raise ValueError(
                            "I don't have enough permission in LOG_CHAT_ID!"
                            "Allow me 'post messages' permissions!"
                        )

                if config_dict["DUMP_CHAT_ID"]:
                    try:
                        dump_chat = await self.client.get_chat(config_dict["DUMP_CHAT_ID"]) # type: ignore
                    except:
                        raise ValueError("First add me in DUMP_CHAT_ID!")
                    if dump_chat.type.name != "CHANNEL":
                        raise ValueError(
                            "DUMP_CHAT_ID must be a channel!"
                        )
                    member = await dump_chat.get_member(uploader_id)
                    if not member.privileges.can_post_messages:
                        raise ValueError(
                            "I don't have enough permission in DUMP_CHAT_ID!"
                            "Allow me 'post messages' permissions!"
                        )

            if self.split_size:
                if self.split_size.isdigit(): # type: ignore
                    self.split_size = int(self.split_size)
                else:
                    self.split_size = get_size_bytes(self.split_size)
            self.split_size = (
                self.split_size
                or self.user_dict.get("split_size")
                or config_dict["LEECH_SPLIT_SIZE"]
            )
            self.equal_splits = (
                self.user_dict.get("equal_splits")
                or config_dict["EQUAL_SPLITS"]
                and "equal_splits" not in self.user_dict
            )
            self.max_split_size = (
                MAX_SPLIT_SIZE
                if self.user_transmission
                else 2097152000
            )
            self.split_size = min(
                self.split_size,
                self.max_split_size
            )

            if not self.as_doc:
                self.as_doc = (
                    not self.as_med
                    if self.as_med
                    else (
                        self.user_dict.get("as_doc", False)
                        or config_dict["AS_DOCUMENT"]
                        and "as_doc" not in self.user_dict
                    )
                )

            self.thumbnail_layout = (
                self.thumbnail_layout
                or self.user_dict.get(
                    "thumb_layout",
                    False
                )
                or (
                    config_dict["THUMBNAIL_LAYOUT"]
                    if "thumb_layout" not in self.user_dict
                    else ""
                )
            )

            if is_telegram_link(str(self.thumb)):
                thumb = await get_tg_link_message(self.thumb)
                msg = (f"{thumb}")[0]
                self.thumb = (
                    await create_thumb(msg)
                    if msg.photo # type: ignore
                    or msg.document # type: ignore
                    else ""
                )
        await self.set_mode()
        self.log_message = await send_log_message(
            self.message, # type: ignore
            self.link,
            self.tag
        )
        await delete_links(self.message) # type: ignore
        if self.dm_message == "BotStarted":
            chat_id = self.message.from_user.id # type: ignore
            if (
                self.is_leech and
                self.up_dest
            ):
                chat_id = self.up_dest
            if reply_to := self.message.reply_to_message: # type: ignore
                if not reply_to.text:
                    self.dm_message = await reply_to.copy(chat_id)
                else:
                    self.dm_message = await send_to_chat(
                        self.message._client, # type: ignore
                        chat_id,
                        self.message.reply_to_message.text # type: ignore
                    )
            else:
                self.dm_message = await send_to_chat(
                    self.message._client, # type: ignore
                    chat_id,
                    self.message.text # type: ignore
                )

    async def get_tag(self, text: list):
        if len(text) > 1 and text[1].startswith("Tag: "):
            user_info = text[1].split("Tag: ")
            if len(user_info) >= 3:
                id_ = user_info[-1]
                self.tag = " ".join(user_info[:-1])
            else:
                (
                    self.tag,
                    id_
                ) = text[1].split("Tag: ")[1].split()
            self.user = self.message.from_user = await self.client.get_users(id_) # type: ignore
            self.user_id = self.user.id
            self.user_dict = user_data.get(
                self.user_id,
                {}
            )
            try:
                await self.message.unpin() # type: ignore
            except:
                pass
        if self.user:
            if username := self.user.username:
                self.tag = f"@{username}"
            elif hasattr(
                self.user,
                "mention"
            ):
                self.tag = self.user.mention
            else:
                self.tag = self.user.id

    @new_task
    async def run_multi(self, input_list, obj):
        if (
            config_dict["DISABLE_MULTI"]
            and self.multi > 1
            and not await is_admin(self.message) # type: ignore
        ):
            smsg = await send_message(
                self.message, # type: ignore
                f"Multi Task is Disabled!\n\ncc: {self.tag}"
            )
            await auto_delete_message(
                self.message, # type: ignore
                smsg
            )
            return
        await sleep(7)
        if (
            not self.multi_tag
            and self.multi > 1
        ):
            self.multi_tag = token_urlsafe(3)
            multi_tags.add(self.multi_tag)
        elif self.multi <= 1:
            if self.multi_tag in multi_tags:
                multi_tags.discard(self.multi_tag)
            return
        if (
            self.multi_tag
            and self.multi_tag
            not in multi_tags
        ):
            smsg = await send_message(
                self.message, # type: ignore
                f"{self.tag} Multi Task has been cancelled!"
            )
            await send_status_message(self.message) # type: ignore
            await auto_delete_message(
                self.message, # type: ignore
                smsg
            )
            async with task_dict_lock:
                for fd_name in self.same_dir: # type: ignore
                    self.same_dir[fd_name]["total"] -= self.multi # type: ignore
            return
        if len(self.bulk) != 0:
            msg = input_list[:1]
            msg.append(f"{self.bulk[0]} -m {self.multi - 1} {self.options}")
            msgts = " ".join(msg)
            if self.multi > 2:
                msgts += f"\nCancel Multi: <code>/{BotCommands.CancelTaskCommand[1]} {self.multi_tag}</code>"
            nextmsg = await send_message(
                self.message, # type: ignore
                msgts
            )
        else:
            msg = [
                s.strip()
                for s
                in input_list
            ]
            index = msg.index("-m")
            msg[index + 1] = f"{self.multi - 1}"
            nextmsg = await self.client.get_messages( # type: ignore
                chat_id=self.message.chat.id, # type: ignore
                message_ids=self.message.reply_to_message_id + 1, # type: ignore
            )
            msgts = " ".join(msg)
            if self.multi > 2:
                msgts += f"\nCancel Multi: <code>/{BotCommands.CancelTaskCommand[1]} {self.multi_tag}</code>"
            nextmsg = await send_message(
                nextmsg,
                msgts
            )
        nextmsg = await self.client.get_messages( # type: ignore
            chat_id=self.message.chat.id, # type: ignore
            message_ids=nextmsg.id # type: ignore
        )
        if self.message.from_user: # type: ignore
            nextmsg.from_user = self.user
        else:
            nextmsg.sender_chat = self.user
        if intervals["stopAll"]:
            return
        await obj(
            self.client, # type: ignore
            nextmsg,
            self.is_qbit,
            self.is_leech,
            self.is_jd,
            self.is_nzb,
            self.same_dir, # type: ignore
            self.bulk,
            self.multi_tag,
            self.options,
        ).new_event()

    async def init_bulk(self, input_list, bulk_start, bulk_end, obj):
        if (
            config_dict["DISABLE_BULK"]
            and not await is_admin(self.message) # type: ignore
        ):
            smsg = await send_message(
                self.message, # type: ignore
                f"Bulk Task is Disabled!\n\ncc: {self.tag}"
            )
            await auto_delete_message(
                self.message, # type: ignore
                smsg
            )
            return
        try:
            self.bulk = await extract_bulk_links(
                self.message, # type: ignore
                bulk_start,
                bulk_end
            )
            if len(self.bulk) == 0:
                raise ValueError("Bulk Empty!")
            b_msg = input_list[:1]
            self.options = input_list[1:]
            index = self.options.index("-b")
            del self.options[index]
            if bulk_start or bulk_end:
                del self.options[index + 1]
            self.options = " ".join(self.options)
            b_msg.append(f"{self.bulk[0]} -m {len(self.bulk)} {self.options}")
            msg = " ".join(b_msg)
            if len(self.bulk) > 2:
                self.multi_tag = token_urlsafe(3)
                multi_tags.add(self.multi_tag)
                msg += f"\nCancel Multi: <code>/{BotCommands.CancelTaskCommand[1]} {self.multi_tag}</code>"
            nextmsg = await send_message(
                self.message, # type: ignore
                msg
            )
            nextmsg = await self.client.get_messages( # type: ignore
                chat_id=self.message.chat.id, # type: ignore
                message_ids=nextmsg.id # type: ignore
            )
            if self.message.from_user: # type: ignore
                nextmsg.from_user = self.user
            else:
                nextmsg.sender_chat = self.user
            await obj(
                self.client, # type: ignore
                nextmsg,
                self.is_qbit,
                self.is_leech,
                self.is_jd,
                self.is_nzb,
                self.same_dir, # type: ignore
                self.bulk,
                self.multi_tag,
                self.options,
            ).new_event()
        except:
            smsg = await send_message(
                self.message, # type: ignore
                "Reply to text file or to telegram message that have links seperated by new line!",
            )
            await auto_delete_message(
                self.message, # type: ignore
                smsg
            )

    async def decompress_zst(self, dl_path, is_dir=False):
        if is_dir:
            for dirpath, _, files in await sync_to_async(walk, dl_path, topdown=False):
                for file_ in files:
                    if file_.endswith(".zst"):
                        f_path = ospath.join(dirpath, file_)
                        out_path = get_base_name(f_path)
                        cmd = ["unzstd", f_path, "-o", out_path]
                        if self.is_cancelled:
                            return ""
                        async with subprocess_lock:
                            self.suproc = await create_subprocess_exec(
                                *cmd, stderr=PIPE
                            )
                        _, stderr = await self.suproc.communicate()
                        if self.is_cancelled:
                            return ""
                        code = self.suproc.returncode
                        if code != 0:
                            try:
                                stderr = stderr.decode().strip()
                            except:
                                stderr = "Unable to decode the error!"
                            LOGGER.error(
                                f"{stderr}. Unable to extract zst file!. Path: {f_path}"
                            )
                        elif not self.seed:
                            await remove(f_path)
            return
        elif dl_path.endswith(".zst"):
            out_path = get_base_name(dl_path)
            cmd = ["unzstd", dl_path, "-o", out_path]
            if self.is_cancelled:
                return ""
            async with subprocess_lock:
                self.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
            _, stderr = await self.suproc.communicate()
            if self.is_cancelled:
                return ""
            code = self.suproc.returncode
            if code != 0:
                try:
                    stderr = stderr.decode().strip()
                except:
                    stderr = "Unable to decode the error!"
                LOGGER.error(f"{stderr}. Unable to extract zst file!. Path: {dl_path}")
            elif not self.seed:
                await remove(dl_path)
            return out_path
        return dl_path

    async def proceed_extract(self, dl_path, gid):
        pswd = (
            self.extract
            if isinstance(
                self.extract,
                str
            )
            else ""
        )
        try:
            LOGGER.info(f"Extracting: {self.name}")
            async with task_dict_lock:
                task_dict[self.mid] = ExtractStatus(
                    self,
                    gid
                )
            if await aiopath.isdir(dl_path):
                if self.seed:
                    self.new_dir = f"{self.dir}10000"
                    up_path = f"{self.new_dir}/{self.name}"
                else:
                    up_path = dl_path
                await self.decompress_zst(
                    dl_path,
                    is_dir=True
                )
                for (
                    dirpath,
                    _,
                    files
                ) in await sync_to_async(
                    walk,
                    dl_path,
                    topdown=False
                ):
                    for file_ in files:
                        if (
                            is_first_archive_split(file_)
                            or is_archive(file_)
                            and not file_.endswith(".rar")
                            and not file_.endswith(".zst")
                        ):
                            f_path = ospath.join(
                                dirpath,
                                file_
                            )
                            t_path = (
                                dirpath.replace(
                                    self.dir,
                                    self.new_dir
                                )
                                if self.seed
                                else dirpath
                            )
                            cmd = [
                                "7z",
                                "x",
                                f"-p{pswd}",
                                f_path,
                                f"-o{t_path}",
                                "-aot",
                                "-xr!@PaxHeader",
                            ]
                            if not pswd:
                                del cmd[2]
                            if self.is_cancelled:
                                return ""
                            async with subprocess_lock:
                                self.suproc = await create_subprocess_exec(
                                    *cmd,
                                    stderr=PIPE
                                )
                            (
                                _,
                                stderr
                            ) = await self.suproc.communicate()
                            if self.is_cancelled:
                                return ""
                            code = self.suproc.returncode
                            if code != 0:
                                try:
                                    stderr = stderr.decode().strip()
                                except:
                                    stderr = "Unable to decode the error!"
                                LOGGER.error(
                                    f"{stderr}. Unable to extract archive splits!. Path: {f_path}"
                                )
                    if (
                        not self.seed
                        and self.suproc is not None
                        and self.suproc.returncode == 0
                    ):
                        for file_ in files:
                            if (
                                is_archive_split(file_) or
                                is_archive(file_)
                            ):
                                del_path = ospath.join(
                                    dirpath,
                                    file_
                                )
                                try:
                                    await remove(del_path)
                                except:
                                    self.is_cancelled = True
                return up_path
            else:
                dl_path = await self.decompress_zst(dl_path)
                up_path = get_base_name(dl_path)
                if self.seed:
                    self.new_dir = f"{self.dir}10000"
                    up_path = up_path.replace(
                        self.dir,
                        self.new_dir
                    )
                cmd = [
                    "7z",
                    "x",
                    f"-p{pswd}",
                    dl_path,
                    f"-o{up_path}",
                    "-aot",
                    "-xr!@PaxHeader",
                ]
                if not pswd:
                    del cmd[2]
                if self.is_cancelled:
                    return ""
                async with subprocess_lock:
                    self.suproc = await create_subprocess_exec(
                        *cmd,
                        stderr=PIPE
                    )
                (
                    _,
                    stderr
                ) = await self.suproc.communicate()
                if self.is_cancelled:
                    return ""
                code = self.suproc.returncode
                if code == -9:
                    self.is_cancelled = True
                    return ""
                elif code == 0:
                    LOGGER.info(f"Extracted Path: {up_path}")
                    if not self.seed:
                        try:
                            await remove(dl_path) # type: ignore
                        except:
                            self.is_cancelled = True
                    return up_path
                else:
                    try:
                        stderr = stderr.decode().strip()
                    except:
                        stderr = "Unable to decode the error!"
                    LOGGER.error(
                        f"{stderr}. Unable to extract archive! Uploading anyway. Path: {dl_path}"
                    )
                    self.new_dir = ""
                    return dl_path
        except NotSupportedExtractionArchive:
            LOGGER.info(
                f"Not any valid archive, uploading file as it is. Path: {dl_path}"
            )
            self.new_dir = ""
            return dl_path

    async def proceed_compress(self, dl_path, gid, o_files, ft_delete):
        pswd = (
            self.compress
            if isinstance(
                self.compress,
                str
            )
            else ""
        )
        if (
            self.seed
            and not self.new_dir
        ):
            self.new_dir = f"{self.dir}10000"
            up_path = f"{self.new_dir}/{self.name}.7z"
            delete = False
        else:
            up_path = f"{dl_path}.7z"
            delete = True
        async with task_dict_lock:
            task_dict[self.mid] = ZipStatus(self, gid)
        size = await get_path_size(dl_path)
        if self.equal_splits:
            parts = -(-size // self.split_size)
            split_size = (size // parts) + (size % parts)
        else:
            split_size = self.split_size
        cmd = [
            "7z",
            f"-v{split_size}b",
            "a",
            "-mx=0",
            f"-p{pswd}",
            up_path,
            dl_path,
        ]
        if await aiopath.isdir(dl_path):
            cmd.extend(
                f"-xr!*.{ext}"
                for ext
                in self.extension_filter
            )
            if o_files:
                for f in o_files:
                    if self.new_dir and self.new_dir in f:
                        fte = f.replace(
                            f"{self.new_dir}/",
                            ""
                        )
                    else:
                        fte = f.replace(
                            f"{self.dir}/",
                            ""
                        )
                    cmd.append(f"-xr!{fte}")
        if self.is_leech and int(size) > self.split_size:
            if not pswd:
                del cmd[4]
            LOGGER.info(f"Zip: orig_path: {dl_path}, zip_path: {up_path}.0*")
        else:
            del cmd[1]
            if not pswd:
                del cmd[3]
            LOGGER.info(f"Zip: orig_path: {dl_path}, zip_path: {up_path}")
        if self.is_cancelled:
            return ""
        async with subprocess_lock:
            self.suproc = await create_subprocess_exec(
                *cmd,
                stderr=PIPE
            )
        (
            _,
            stderr
        ) = await self.suproc.communicate()
        if self.is_cancelled:
            return ""
        code = self.suproc.returncode
        if code == -9:
            self.is_cancelled = True
            return ""
        elif code == 0:
            if not self.seed or delete:
                await clean_target(dl_path)
            for f in ft_delete:
                if await aiopath.exists(f):
                    try:
                        await remove(f)
                    except:
                        pass
            ft_delete.clear()
            return up_path
        else:
            await clean_target(self.new_dir)
            if not delete:
                self.new_dir = ""
            try:
                stderr = stderr.decode().strip()
            except:
                stderr = "Unable to decode the error!"
            LOGGER.error(f"{stderr}. Unable to zip this path: {dl_path}")
            return dl_path

    async def proceed_split(self, up_dir, m_size, o_files, gid):
        checked = False
        for (
            dirpath,
            _,
            files
        ) in await sync_to_async(
            walk,
            up_dir,
            topdown=False
        ):
            for file_ in files:
                f_path = ospath.join(
                    dirpath,
                    file_
                )
                if f_path in o_files:
                    continue
                f_size = await aiopath.getsize(f_path)
                if f_size > self.split_size:
                    if not checked:
                        checked = True
                        async with task_dict_lock:
                            task_dict[self.mid] = SplitStatus(self, gid)
                        LOGGER.info(f"Splitting: {self.name}")
                    res = await split_file(
                        f_path,
                        f_size,
                        dirpath,
                        file_,
                        self.split_size,
                        self
                    )
                    if self.is_cancelled:
                        return
                    if not res:
                        if f_size >= self.max_split_size:
                            if (
                                self.seed
                                and not self.new_dir
                            ):
                                m_size.append(f_size)
                                o_files.append(f_path)
                            else:
                                try:
                                    await remove(f_path)
                                except:
                                    return
                        continue
                    elif (
                        not self.seed
                        or self.new_dir
                    ):
                        try:
                            await remove(f_path)
                        except:
                            return
                    else:
                        m_size.append(f_size)
                        o_files.append(f_path)

    async def generate_sample_video(self, dl_path, gid, unwanted_files, ft_delete):
        data = (
            self.sample_video.split(":")
            if isinstance(
                self.sample_video,
                str
            )
            else ""
        )
        if data:
            sample_duration = (
                int(data[0])
                if data[0]
                else 60
            )
            part_duration = (
                int(data[1])
                if len(data) > 1
                else 4
            )
        else:
            sample_duration = 60
            part_duration = 4

        async with task_dict_lock:
            task_dict[self.mid] = SampleVideoStatus(
                self,
                gid
            )

        checked = False
        if await aiopath.isfile(dl_path):
            if (await get_document_type(dl_path))[0]:
                checked = True
                async with cpu_eater_lock:
                    LOGGER.info(f"Creating Sample video: {self.name}")
                    res = await create_sample_video(
                        self,
                        dl_path,
                        sample_duration,
                        part_duration
                    )
                if res:
                    newfolder = ospath.splitext(dl_path)[0]
                    name = dl_path.rsplit(
                        "/",
                        1
                    )[1]
                    if (
                        self.seed
                        and not self.new_dir
                    ):
                        if (
                            self.is_leech
                            and not self.compress
                        ):
                            return self.dir
                        self.new_dir = f"{self.dir}10000"
                        newfolder = newfolder.replace(
                            self.dir,
                            self.new_dir
                        )
                        await makedirs(
                            newfolder,
                            exist_ok=True
                        )
                        await gather(
                            copy2(
                                dl_path,
                                f"{newfolder}/{name}"
                            ),
                            move(
                                res,
                                f"{newfolder}/SAMPLE.{name}"
                            ),
                        )
                    else:
                        await makedirs(
                            newfolder,
                            exist_ok=True
                        )
                        await gather(
                            move(
                                dl_path,
                                f"{newfolder}/{name}"
                            ),
                            move(
                                res,
                                f"{newfolder}/SAMPLE.{name}"
                            ),
                        )
                    return newfolder
        else:
            for (
                dirpath,
                _,
                files
            ) in await sync_to_async(
                walk,
                dl_path,
                topdown=False
            ):
                for file_ in files:
                    f_path = ospath.join(
                        dirpath,
                        file_
                    )
                    if f_path in unwanted_files:
                        continue
                    if (await get_document_type(f_path))[0]:
                        if not checked:
                            checked = True
                            await cpu_eater_lock.acquire()
                            LOGGER.info(f"Creating Sample videos: {self.name}")
                        if self.is_cancelled:
                            cpu_eater_lock.release()
                            return ""
                        res = await create_sample_video(
                            self,
                            f_path,
                            sample_duration,
                            part_duration
                        )
                        if res:
                            ft_delete.append(res)
            if checked:
                cpu_eater_lock.release()

        return dl_path

    async def convert_media(self, dl_path, gid, o_files, m_size, ft_delete):
        fvext = []
        if self.convert_video:
            vdata = self.convert_video.split() # type: ignore
            vext = vdata[0]
            if len(vdata) > 2:
                if "+" in vdata[1].split():
                    vstatus = "+"
                elif "-" in vdata[1].split():
                    vstatus = "-"
                else:
                    vstatus = ""
                fvext.extend(
                    f".{ext}"
                    for ext
                    in vdata[2:]
                )
            else:
                vstatus = ""
        else:
            vext = ""
            vstatus = ""

        faext = []
        if self.convert_audio:
            adata = self.convert_audio.split() # type: ignore
            aext = adata[0]
            if len(adata) > 2:
                if "+" in adata[1].split():
                    astatus = "+"
                elif "-" in adata[1].split():
                    astatus = "-"
                else:
                    astatus = ""
                faext.extend(
                    f".{ext}"
                    for ext
                    in adata[2:]
                )
            else:
                astatus = ""
        else:
            aext = ""
            astatus = ""

        checked = False

        async def proceed_convert(m_path):
            nonlocal checked
            (
                is_video,
                is_audio,
                _
            ) = await get_document_type(m_path)
            if (
                is_video
                and vext
                and not m_path.endswith(f".{vext}")
                and (
                    vstatus == "+"
                    and m_path.endswith(tuple(fvext))
                    or vstatus == "-"
                    and not m_path.endswith(tuple(fvext))
                    or not vstatus
                )
            ):
                if not checked:
                    checked = True
                    async with task_dict_lock:
                        task_dict[self.mid] = MediaConvertStatus(
                            self,
                            gid
                        )
                    await cpu_eater_lock.acquire()
                    LOGGER.info(f"Converting: {self.name}")
                else:
                    LOGGER.info(f"Converting: {m_path}")
                res = await convert_video(
                    self,
                    m_path,
                    vext
                )
                return (
                    ""
                    if self.is_cancelled
                    else res
                )
            elif (
                is_audio
                and aext
                and not is_video
                and not m_path.endswith(f".{aext}")
                and (
                    astatus == "+"
                    and m_path.endswith(tuple(faext))
                    or astatus == "-"
                    and not m_path.endswith(tuple(faext))
                    or not astatus
                )
            ):
                if not checked:
                    checked = True
                    async with task_dict_lock:
                        task_dict[self.mid] = MediaConvertStatus(
                            self,
                            gid
                        )
                    await cpu_eater_lock.acquire()
                    LOGGER.info(f"Converting: {self.name}")
                else:
                    LOGGER.info(f"Converting: {m_path}")
                res = await convert_audio(
                    self,
                    m_path,
                    aext
                )
                return (
                    ""
                    if self.is_cancelled
                    else res
                )
            else:
                return ""

        if await aiopath.isfile(dl_path):
            output_file = await proceed_convert(dl_path) # type: ignore
            if checked:
                cpu_eater_lock.release()
            if output_file:
                if self.seed:
                    self.new_dir = f"{self.dir}10000"
                    new_output_file = output_file.replace(
                        self.dir,
                        self.new_dir
                    )
                    await makedirs(
                        self.new_dir,
                        exist_ok=True
                    )
                    await move(
                        output_file,
                        new_output_file
                    )
                    return new_output_file
                else:
                    try:
                        await remove(dl_path)
                    except:
                        pass
                    return output_file
        else:
            for (
                dirpath,
                _,
                files
            ) in await sync_to_async(
                walk,
                dl_path,
                topdown=False
            ):
                for file_ in files:
                    if self.is_cancelled:
                        cpu_eater_lock.release()
                        return ""
                    f_path = ospath.join(
                        dirpath,
                        file_
                    )
                    res = await proceed_convert(f_path)
                    if res:
                        if self.seed and not self.new_dir:
                            o_files.append(f_path)
                            fsize = await aiopath.getsize(f_path)
                            m_size.append(fsize)
                            ft_delete.append(res)
                        else:
                            try:
                                await remove(f_path)
                            except:
                                pass
            if checked:
                cpu_eater_lock.release()
        return dl_path

    async def generate_screenshots(self, dl_path):
        ss_nb = (
            int(self.screen_shots)
            if isinstance(
                self.screen_shots,
                str
            )
            else 10
        )
        if await aiopath.isfile(dl_path):
            if (await get_document_type(dl_path))[0]:
                LOGGER.info(f"Creating Screenshot for: {dl_path}")
                res = await take_ss(
                    dl_path,
                    ss_nb
                )
                if res:
                    newfolder = ospath.splitext(dl_path)[0]
                    name = dl_path.rsplit(
                        "/",
                        1
                    )[1]
                    if (
                        self.seed
                        and not self.new_dir
                    ):
                        if (
                            self.is_leech
                            and not self.compress
                        ):
                            return self.dir
                        await makedirs(
                            newfolder,
                            exist_ok=True
                        )
                        self.new_dir = f"{self.dir}10000"
                        newfolder = newfolder.replace(
                            self.dir,
                            self.new_dir
                        )
                        await gather(
                            copy2(
                                dl_path,
                                f"{newfolder}/{name}"
                            ),
                            move(
                                res,
                                newfolder
                            ),
                        )
                    else:
                        await makedirs(
                            newfolder,
                            exist_ok=True
                        )
                        await gather(
                            move(
                                dl_path,
                                f"{newfolder}/{name}"
                            ),
                            move(
                                res,
                                newfolder
                            ),
                        )
                    return newfolder
        else:
            LOGGER.info(f"Creating Screenshot for: {dl_path}")
            for (
                dirpath,
                _,
                files
            ) in await sync_to_async(
                walk,
                dl_path,
                topdown=False
            ):
                for file_ in files:
                    f_path = ospath.join(
                        dirpath,
                        file_
                    )
                    if (await get_document_type(f_path))[0]:
                        await take_ss(
                            f_path,
                            ss_nb
                        )
        return dl_path

    async def substitute(self, dl_path):
        if await aiopath.isfile(dl_path):
            (
                up_dir,
                name
            ) = dl_path.rsplit(
                "/",
                1
            )
            for substitution in self.name_sub:
                sen = False
                pattern = substitution[0]
                if len(substitution) > 1:
                    if len(substitution) > 2:
                        sen = substitution[2] == "s"
                        res = substitution[1]
                    elif len(substitution[1]) == 0:
                        res = " "
                    else:
                        res = substitution[1]
                else:
                    res = ""
                try:
                    name = sub(
                        rf"{pattern}",
                        res,
                        name,
                        flags=I
                        if sen
                        else 0
                    )
                except Exception as e:
                    LOGGER.error(
                        f"Substitute Error: pattern: {pattern} res: {res}. Error: {e}"
                    )
                    return dl_path
                if len(name.encode()) > 255:
                    LOGGER.error(
                        f"Substitute: {name} is too long"
                    )
                    return dl_path
            new_path = ospath.join(
                up_dir,
                name
            )
            await move(
                dl_path,
                new_path
            )
            return new_path
        else:
            for (
                dirpath,
                _,
                files
            ) in await sync_to_async(
                walk,
                dl_path,
                topdown=False
            ):
                for file_ in files:
                    f_path = ospath.join(
                        dirpath,
                        file_
                    )
                    for substitution in self.name_sub:
                        sen = False
                        pattern = substitution[0]
                        if len(substitution) > 1:
                            if len(substitution) > 2:
                                sen = substitution[2] == "s"
                                res = substitution[1]
                            elif len(substitution[1]) == 0:
                                res = " "
                            else:
                                res = substitution[1]
                        else:
                            res = ""
                        try:
                            file_ = sub(
                                rf"{pattern}",
                                res,
                                file_,
                                flags=I
                                if sen
                                else 0
                            )
                        except Exception as e:
                            LOGGER.error(
                                f"Substitute Error: pattern: {pattern} res: {res}. Error: {e}"
                            )
                            continue
                        if len(file_.encode()) > 255:
                            LOGGER.error(
                                f"Substitute: {file_} is too long"
                            )
                            continue
                    await move(
                        f_path,
                        ospath.join(
                            dirpath,
                            file_
                        )
                    )
            return dl_path

    async def proceedMetadata(self, up_path, gid):
        async with task_dict_lock:
            task_dict[self.mid] = MetaStatus(
                self,
                gid
            )
        LOGGER.info(f"Editing Metadata: {self.metadata} into {up_path}")
        await edit_video_metadata(
            self,
            up_path
        )
        return up_path

    async def proceedAttachment(self, up_path, gid):
        async with task_dict_lock:
            task_dict[self.mid] = MetaStatus(
                self,
                gid
            )
        LOGGER.info(f"Adding Attachment: {self.m_attachment} into {up_path}")
        await add_attachment(
            self,
            up_path
        )
        return up_path
