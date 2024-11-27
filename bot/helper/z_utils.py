from hashlib import sha1
from os import (
    path,
    remove
)
from re import search
from xml.etree import ElementTree as ET

from base64 import (
    urlsafe_b64encode as b64e,
    urlsafe_b64decode as b64d
)

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from bencoding import (
    bdecode,
    bencode
)

from bot import (
    KEY,
    LOGGER,
    config_dict
)
from .ext_utils.links_utils import (
    is_magnet,
    is_gdrive_link
)
from .ext_utils.task_manager import check_user_tasks
from .ext_utils.token_manager import checking_access
from .ext_utils.db_handler import database
from .task_utils.gdrive_utils.helper import GoogleDriveHelper
from .telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    force_subscribe,
    message_filter,
    send_message
)


async def extract_link(link, should_delete=False):
    try:
        if link and is_magnet(link):
            raw_link = search(
                r"(?<=xt=urn:(btih|btmh):)[a-zA-Z0-9]+",
                link
            ).group(0).lower() # type: ignore
        elif is_gdrive_link(link):
            raw_link = GoogleDriveHelper().get_id_from_url(link)
        elif path.exists(link):
            if link.endswith(".nzb"):
                tree = ET.parse(link)
                root = tree.getroot()
                raw_link = root.get(
                    "id",
                    None
                )
                if not raw_link:
                    raw_link = root.findtext(".//segment")
            else:
                with open(
                    link,
                    "rb"
                ) as f:
                    decodedDict = bdecode(f.read())
                raw_link = str(sha1(bencode(decodedDict[b"info"])).hexdigest())
                if should_delete:
                    remove(link)
        else:
            raw_link = link
    except Exception as e:
        LOGGER.error(e)
        raw_link = link
    return raw_link


async def stop_duplicate_tasks(message, link, file_=None):
    if (
        config_dict["DATABASE_URL"]
        and config_dict["STOP_DUPLICATE_TASKS"]
    ):
        raw_url = (
            file_.file_unique_id
            if file_
            else await extract_link(link)
        )
        exist = await database.check_download(raw_url) # type: ignore
        if exist:
            _msg = f'<b>Download is already added by {exist["tag"]}</b>\n'
            _msg += f'Check the download status in /status{exist["suffix"]}@{exist["botname"]}\n\n'
            _msg += f'<b>Link</b>: <code>{exist["_id"]}</code>'
            reply_message = await send_message(
                message,
                _msg
            )
            await auto_delete_message(
                message,
                reply_message
            )
            await delete_links(message)
            return "duplicate_tasks"
        return raw_url


async def none_admin_utils(message, is_leech=False):
    msg = []
    if (
        is_leech
        and config_dict["DISABLE_LEECH"]
    ):
        msg.append("Leech is disabled on this bot.\n💡Use other bots;)")
    if filtered := await message_filter(message):
        msg.append(filtered)
    if (
        (
            maxtask := config_dict["USER_MAX_TASKS"]
        ) 
        and await check_user_tasks(
            message.from_user.id,
            maxtask
        )
    ):
        msg.append(f"Your tasks limit exceeded!\n💡Use other bots.\n\nTasks limit: {maxtask}")
    button = None
    if (
        is_leech
        and config_dict["DISABLE_LEECH"]
    ):
        msg.append("Leech is disabled!\n💡 Use other bots...")
    if (
        message.chat.type
        !=
        message.chat.type.PRIVATE
    ):
        (
            token_msg,
            button
        ) = await checking_access(
            message.from_user.id,
            button
        )
        if token_msg is not None:
            msg.append(token_msg)
        if ids := config_dict["FSUB_IDS"]:
            (
                _msg,
                button
            ) = await force_subscribe(
                message,
                ids,
                button
            )
            if _msg:
                msg.append(_msg)
    await delete_links(message)
    return (
        msg,
        button
    )


backend = default_backend()
iterations = 100_000

def _derive_key(
        password: bytes,
        salt: bytes,
        iterations: int = iterations
    ) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=backend
    )
    return b64e(kdf.derive(password))

def def_media(token: bytes) -> bytes:
    decoded = b64d(token)
    (
        salt,
        iter,
        token
    ) = (
        decoded[:16],
        decoded[16:20],
        b64e(decoded[20:])
    )
    iterations = int.from_bytes(
        iter,
        "big"
    )
    key = _derive_key(
        KEY.encode(),
        salt,
        iterations
    )
    return Fernet(key).decrypt(token)
