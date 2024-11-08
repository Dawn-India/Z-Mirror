from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asyncio import (
    Lock,
    new_event_loop,
    set_event_loop
)
from aria2p import (
    API as ariaAPI,
    Client as ariaClient
)
from collections import OrderedDict
from dotenv import (
    load_dotenv,
    dotenv_values
)
from logging import (
    ERROR,
    INFO,
    basicConfig,
    error as log_error,
    FileHandler,
    getLogger,
    info as log_info,
    StreamHandler,
    warning as log_warning,
)
from nekozee import Client as TgClient
from os import (
    environ,
    path as ospath,
    remove
)
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from qbittorrentapi import Client as QbClient
from sabnzbdapi import SabnzbdClient
from shutil import rmtree
from socket import setdefaulttimeout
from subprocess import (
    Popen,
    run
)
from sys import exit
from time import time
from tzlocal import get_localzone
from uvloop import install

# from faulthandler import enable as faulthandler_enable
# faulthandler_enable()

install()
setdefaulttimeout(600)

getLogger("qbittorrentapi").setLevel(INFO)
getLogger("requests").setLevel(INFO)
getLogger("urllib3").setLevel(INFO)
getLogger("apscheduler").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)
getLogger("pymongo").setLevel(ERROR)
getLogger("nekozee").setLevel(ERROR)

bot_start_time = time()

bot_loop = new_event_loop()
set_event_loop(bot_loop)


basicConfig(
    format="%(levelname)s | From %(name)s -> %(module)s line no: %(lineno)d | %(message)s",
    handlers=[
        FileHandler("Zee_Logs.txt"),
        StreamHandler()
    ],
    level=INFO,
)

LOGGER = getLogger(__name__)

load_dotenv(
    "config.env",
    override=True
)

intervals = {
    "status": {},
    "qb": "",
    "jd": "",
    "nzb": "",
    "stopAll": False
}
qb_torrents = {}
jd_downloads = {}
nzb_jobs = {}

drives_names = []
drives_ids = []
index_urls = []
global_extension_filter = [
    "aria2",
    "!qB"
]
shorteneres_list = []

extra_buttons = {}
user_data = {}
aria2_options = {}
qbit_options = {}
nzb_options = {}
queued_dl = {}
queued_up = {}

non_queued_dl = set()
non_queued_up = set()
multi_tags = set()

try:
    if bool(environ.get("_____REMOVE_THIS_LINE_____")):
        log_error("The README.md file there to be read! Exiting now!")
        exit(1)
except:
    pass

task_dict_lock = Lock()
queue_dict_lock = Lock()
qb_listener_lock = Lock()
nzb_listener_lock = Lock()
jd_lock = Lock()
cpu_eater_lock = Lock()
subprocess_lock = Lock()
same_directory_lock = Lock()

status_dict = {}
task_dict = {}
rss_dict = {}
cached_dict = {}

JAVA = ("uJjxvDIuQLVbyMZ61fyl7")


BOT_TOKEN = environ.get(
    "BOT_TOKEN",
    ""
)
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

BOT_ID = BOT_TOKEN.split(
    ":",
    1
)[0]

DATABASE_URL = environ.get(
    "DATABASE_URL",
    ""
)
if len(DATABASE_URL) == 0:
    DATABASE_URL = ""

if DATABASE_URL:
    try:
        conn = MongoClient(
            DATABASE_URL,
            server_api=ServerApi("1")
        )
        db = conn.zee
        current_config = dict(dotenv_values("config.env"))
        old_config = db.settings.deployConfig.find_one({"_id": BOT_ID})
        if old_config is None:
            db.settings.deployConfig.replace_one(
                {"_id": BOT_ID},
                current_config,
                upsert=True
            )
        else:
            del old_config["_id"]
        if (
            old_config
            and old_config != current_config
        ):
            db.settings.deployConfig.replace_one(
                {"_id": BOT_ID},
                current_config,
                upsert=True
            )
        elif config_dict := db.settings.config.find_one({"_id": BOT_ID}):
            del config_dict["_id"]
            for key, value in config_dict.items():
                environ[key] = str(value)
        if pf_dict := db.settings.files.find_one({"_id": BOT_ID}):
            del pf_dict["_id"]
            for key, value in pf_dict.items():
                if value:
                    file_ = key.replace(
                        "__",
                        "."
                    )
                    with open(
                        file_,
                        "wb+"
                    ) as f:
                        f.write(value)
        if a2c_options := db.settings.aria2c.find_one({"_id": BOT_ID}):
            del a2c_options["_id"]
            aria2_options = a2c_options
        if qbit_opt := db.settings.qbittorrent.find_one({"_id": BOT_ID}):
            del qbit_opt["_id"]
            qbit_options = qbit_opt
        if nzb_opt := db.settings.nzb.find_one({"_id": BOT_ID}):
            if ospath.exists("sabnzbd/SABnzbd.ini.bak"):
                remove("sabnzbd/SABnzbd.ini.bak")
            del nzb_opt["_id"]
            ((key, value),) = nzb_opt.items()
            file_ = key.replace("__", ".")
            with open(f"sabnzbd/{file_}", "wb+") as f:
                f.write(value)
        conn.close()
        BOT_TOKEN = environ.get(
            "BOT_TOKEN",
            ""
        )
        BOT_ID = BOT_TOKEN.split(
            ":",
            1
        )[0]
        DATABASE_URL = environ.get(
            "DATABASE_URL",
            ""
        )
    except Exception as e:
        LOGGER.error(f"Database ERROR: {e}")
else:
    config_dict = {}

if ospath.exists("cfg.zip"):
    if ospath.exists("/JDownloader/cfg"):
        rmtree(
            "/JDownloader/cfg",
            ignore_errors=True
        )
    run([
        "7z",
        "x",
        "cfg.zip",
        "-o/JDownloader"
    ])
    remove("cfg.zip")

if not ospath.exists(".netrc"):
    with open(
        ".netrc",
        "w"
    ):
        pass
run(
    "chmod 600 .netrc && cp .netrc /root/.netrc && chmod +x aria-nox-nzb.sh && ./aria-nox-nzb.sh",
    shell=True,
)

OWNER_ID = environ.get(
    "OWNER_ID",
    ""
)
if len(OWNER_ID) == 0:
    log_error("OWNER_ID variable is missing! Exiting now")
    exit(1)
else:
    OWNER_ID = int(OWNER_ID)

TELEGRAM_API = environ.get(
    "TELEGRAM_API",
    ""
)
if len(TELEGRAM_API) == 0:
    log_error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)
else:
    TELEGRAM_API = int(TELEGRAM_API)

TELEGRAM_HASH = environ.get(
    "TELEGRAM_HASH",
    ""
)
if len(TELEGRAM_HASH) == 0:
    log_error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)

USER_SESSION_STRING = environ.get(
    "USER_SESSION_STRING",
    ""
)
if len(USER_SESSION_STRING) != 0:
    try:
        user = TgClient(
            "zeeu",
            TELEGRAM_API,
            TELEGRAM_HASH,
            session_string=USER_SESSION_STRING,
            no_updates=True,
            app_version="@Z_Mirror Session",
            device_model="@Z_Mirror Bot",
            system_version="@Z_Mirror Server",
        ).start()
        IS_PREMIUM_USER = user.me.is_premium # type: ignore
        log_info(f"Successfully logged into @{user.me.username} DC: {user.session.dc_id}.") # type: ignore
        if user.me.is_bot: # type: ignore
            log_error("You added bot string in USER_SESSION_STRING which is not allowed!")
            user.stop() # type: ignore
            IS_PREMIUM_USER = False
            user = ""
    except:
        log_error("Failed to create client from USER_SESSION_STRING")
        IS_PREMIUM_USER = False
        user = ""
else:
    IS_PREMIUM_USER = False
    user = ""

GDRIVE_ID = environ.get(
    "GDRIVE_ID",
    ""
)
if len(GDRIVE_ID) == 0:
    GDRIVE_ID = ""

RCLONE_PATH = environ.get(
    "RCLONE_PATH",
    ""
)
if len(RCLONE_PATH) == 0:
    RCLONE_PATH = ""

RCLONE_FLAGS = environ.get(
    "RCLONE_FLAGS",
    ""
)
if len(RCLONE_FLAGS) == 0:
    RCLONE_FLAGS = ""

DEFAULT_UPLOAD = environ.get(
    "DEFAULT_UPLOAD",
    ""
)
if DEFAULT_UPLOAD != "rc":
    DEFAULT_UPLOAD = "gd"

DOWNLOAD_DIR = environ.get(
    "DOWNLOAD_DIR",
    ""
)
if len(DOWNLOAD_DIR) == 0:
    DOWNLOAD_DIR = "/usr/src/app/downloads/"
elif not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR = f"{DOWNLOAD_DIR}/"

AUTHORIZED_CHATS = environ.get(
    "AUTHORIZED_CHATS",
    ""
)
if len(AUTHORIZED_CHATS) != 0:
    aid = AUTHORIZED_CHATS.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {"is_auth": True}

SUDO_USERS = environ.get(
    "SUDO_USERS",
    ""
)
if len(SUDO_USERS) != 0:
    aid = SUDO_USERS.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {"is_sudo": True}

JAVA += ("wABhqCAAAAAAGZTZRSZfx")

EXTENSION_FILTER = environ.get(
    "EXTENSION_FILTER",
    ""
)
if len(EXTENSION_FILTER) > 0:
    fx = EXTENSION_FILTER.split()
    for x in fx:
        x = x.lstrip(".")
        global_extension_filter.append(x.strip().lower())

JD_EMAIL = environ.get(
    "JD_EMAIL",
    ""
)
JD_PASS = environ.get(
    "JD_PASS",
    ""
)
if (
    len(JD_EMAIL) == 0 or
    len(JD_PASS) == 0
):
    JD_EMAIL = ""
    JD_PASS = ""

USENET_SERVERS = environ.get("USENET_SERVERS", "")
try:
    if len(USENET_SERVERS) == 0:
        USENET_SERVERS = []
    elif (us := eval(USENET_SERVERS)) and not us[0].get("host"):
        USENET_SERVERS = []
    else:
        USENET_SERVERS = eval(USENET_SERVERS)
except:
    log_error(f"Wrong USENET_SERVERS format: {USENET_SERVERS}")
    USENET_SERVERS = []

FILELION_API = environ.get(
    "FILELION_API",
    ""
)
if len(FILELION_API) == 0:
    FILELION_API = ""

STREAMWISH_API = environ.get(
    "STREAMWISH_API",
    ""
)
if len(STREAMWISH_API) == 0:
    STREAMWISH_API = ""

JAVA += ("nbmdSB2UOfbkM3hj1ObkH")

INDEX_URL = environ.get(
    "INDEX_URL",
    ""
).rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = ""

SEARCH_API_LINK = environ.get(
    "SEARCH_API_LINK",
    ""
).rstrip("/")
if len(SEARCH_API_LINK) == 0:
    SEARCH_API_LINK = ""

LEECH_FILENAME_PREFIX = environ.get(
    "LEECH_FILENAME_PREFIX",
    ""
)
if len(LEECH_FILENAME_PREFIX) == 0:
    LEECH_FILENAME_PREFIX = ""

LEECH_FILENAME_SUFFIX = environ.get(
    "LEECH_FILENAME_SUFFIX",
    ""
)
if len(LEECH_FILENAME_SUFFIX) == 0:
    LEECH_FILENAME_SUFFIX = ""

LEECH_CAPTION_FONT = environ.get(
    "LEECH_CAPTION_FONT",
    ""
)
if len(LEECH_CAPTION_FONT) == 0:
    LEECH_CAPTION_FONT = ""

METADATA_TXT = environ.get(
    "METADATA_TXT",
    ""
)
if len(METADATA_TXT) == 0:
    METADATA_TXT = ""

META_ATTACHMENT = environ.get(
    "META_ATTACHMENT",
    ""
)
if len(META_ATTACHMENT) == 0:
    META_ATTACHMENT = ""

SEARCH_PLUGINS = environ.get(
    "SEARCH_PLUGINS",
    ""
)
if len(SEARCH_PLUGINS) == 0:
    SEARCH_PLUGINS = ""
else:
    try:
        SEARCH_PLUGINS = eval(SEARCH_PLUGINS)
    except:
        log_error(f"Wrong USENET_SERVERS format: {SEARCH_PLUGINS}")
        SEARCH_PLUGINS = ""

MAX_SPLIT_SIZE = (
    4194304000
    if IS_PREMIUM_USER
    else 2097152000
)

LEECH_SPLIT_SIZE = environ.get(
    "LEECH_SPLIT_SIZE",
    ""
)
if (
    len(LEECH_SPLIT_SIZE) == 0
    or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE
    or LEECH_SPLIT_SIZE == "2097152000"
):
    LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
else:
    LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE)

STATUS_UPDATE_INTERVAL = environ.get(
    "STATUS_UPDATE_INTERVAL",
    ""
)
if len(STATUS_UPDATE_INTERVAL) == 0:
    STATUS_UPDATE_INTERVAL = 15
else:
    STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)

AUTO_DELETE_MESSAGE_DURATION = environ.get(
    "AUTO_DELETE_MESSAGE_DURATION",
    ""
)
if len(AUTO_DELETE_MESSAGE_DURATION) == 0:
    AUTO_DELETE_MESSAGE_DURATION = 30
else:
    AUTO_DELETE_MESSAGE_DURATION = int(AUTO_DELETE_MESSAGE_DURATION)

YT_DLP_OPTIONS = environ.get(
    "YT_DLP_OPTIONS",
    ""
)
if len(YT_DLP_OPTIONS) == 0:
    YT_DLP_OPTIONS = ""

SEARCH_LIMIT = environ.get(
    "SEARCH_LIMIT",
    ""
)
SEARCH_LIMIT = (
    0
    if len(SEARCH_LIMIT) == 0
    else int(SEARCH_LIMIT)
)

JAVA += ("Ls_kQRgOToP9mN1JeGlMA")

USER_LEECH_DESTINATION = environ.get(
    "USER_LEECH_DESTINATION",
    ""
)
USER_LEECH_DESTINATION = (
    ""
    if len(USER_LEECH_DESTINATION) == 0
    else USER_LEECH_DESTINATION
)
if (
    USER_LEECH_DESTINATION.isdigit() or
    USER_LEECH_DESTINATION.startswith("-")
):
    USER_LEECH_DESTINATION = int(USER_LEECH_DESTINATION)

STATUS_LIMIT = environ.get(
    "STATUS_LIMIT",
    ""
)
STATUS_LIMIT = (
    5
    if len(STATUS_LIMIT) == 0
    else int(STATUS_LIMIT)
)

CMD_SUFFIX = environ.get(
    "CMD_SUFFIX",
    ""
)

RSS_CHAT = environ.get(
    "RSS_CHAT",
    ""
)
RSS_CHAT = (
    ""
    if len(RSS_CHAT) == 0
    else RSS_CHAT
)
if (
    RSS_CHAT.isdigit() or
    RSS_CHAT.startswith("-")
):
    RSS_CHAT = int(RSS_CHAT)

JAVA += ("iLAhm1ooTWmfdV6e5GLUe")

RSS_DELAY = environ.get(
    "RSS_DELAY",
    ""
)
RSS_DELAY = (
    600
    if len(RSS_DELAY) == 0
    else int(RSS_DELAY)
)

TORRENT_TIMEOUT = environ.get(
    "TORRENT_TIMEOUT",
    ""
)
TORRENT_TIMEOUT = (
    ""
    if len(TORRENT_TIMEOUT) == 0
    else int(TORRENT_TIMEOUT)
)

BASE = ("5GIemPhMxinY2wAHYXHmt")

QUEUE_ALL = environ.get(
    "QUEUE_ALL",
    ""
)
QUEUE_ALL = (
    ""
    if len(QUEUE_ALL) == 0
    else int(QUEUE_ALL)
)

QUEUE_DOWNLOAD = environ.get(
    "QUEUE_DOWNLOAD",
    ""
)
QUEUE_DOWNLOAD = (
    ""
    if len(QUEUE_DOWNLOAD) == 0
    else int(QUEUE_DOWNLOAD)
)

QUEUE_UPLOAD = environ.get(
    "QUEUE_UPLOAD",
    ""
)
QUEUE_UPLOAD = (
    ""
    if len(QUEUE_UPLOAD) == 0
    else int(QUEUE_UPLOAD)
)

JAVA += ("ict9yGHQY2FtZo2F6NYor")

INCOMPLETE_TASK_NOTIFIER = environ.get(
    "INCOMPLETE_TASK_NOTIFIER",
    ""
)
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == "true"

STOP_DUPLICATE = environ.get(
    "STOP_DUPLICATE",
    ""
)
STOP_DUPLICATE = STOP_DUPLICATE.lower() == "true"

IS_TEAM_DRIVE = environ.get(
    "IS_TEAM_DRIVE",
    ""
)
IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == "true"

USE_SERVICE_ACCOUNTS = environ.get(
    "USE_SERVICE_ACCOUNTS",
    ""
)
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == "true"

WEB_PINCODE = environ.get(
    "WEB_PINCODE",
    ""
)
WEB_PINCODE = WEB_PINCODE.lower() == "true"

AS_DOCUMENT = environ.get(
    "AS_DOCUMENT",
    ""
)
AS_DOCUMENT = AS_DOCUMENT.lower() == "true"

EQUAL_SPLITS = environ.get(
    "EQUAL_SPLITS",
    ""
)
EQUAL_SPLITS = EQUAL_SPLITS.lower() == "true"

MEDIA_GROUP = environ.get(
    "MEDIA_GROUP",
    ""
)
MEDIA_GROUP = MEDIA_GROUP.lower() == "true"

USER_TRANSMISSION = environ.get(
    "USER_TRANSMISSION",
    ""
)
USER_TRANSMISSION = (
    USER_TRANSMISSION.lower() == "true"
    and IS_PREMIUM_USER
)

BASE_URL_PORT = environ.get(
    "BASE_URL_PORT",
    ""
)
BASE_URL_PORT = (
    80
    if len(BASE_URL_PORT) == 0
    else int(BASE_URL_PORT)
)

BASE_URL = environ.get(
    "BASE_URL",
    ""
).rstrip("/")
if len(BASE_URL) == 0:
    log_warning("BASE_URL not provided!")
    BASE_URL = ""

UPSTREAM_REPO = environ.get(
    "UPSTREAM_REPO",
    ""
)
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = ""

JAVA += ("pvWgYNn2uZytuMxEjlnrj")

UPSTREAM_BRANCH = environ.get(
    "UPSTREAM_BRANCH",
    ""
)
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = "master"

RCLONE_SERVE_URL = environ.get(
    "RCLONE_SERVE_URL",
    ""
).rstrip("/")
if len(RCLONE_SERVE_URL) == 0:
    RCLONE_SERVE_URL = ""

RCLONE_SERVE_PORT = environ.get(
    "RCLONE_SERVE_PORT",
    ""
)
RCLONE_SERVE_PORT = (
    8080
    if len(RCLONE_SERVE_PORT) == 0
    else int(RCLONE_SERVE_PORT)
)

RCLONE_SERVE_USER = environ.get(
    "RCLONE_SERVE_USER",
    ""
)
if len(RCLONE_SERVE_USER) == 0:
    RCLONE_SERVE_USER = ""

RCLONE_SERVE_PASS = environ.get(
    "RCLONE_SERVE_PASS",
    ""
)
if len(RCLONE_SERVE_PASS) == 0:
    RCLONE_SERVE_PASS = ""

NAME_SUBSTITUTE = environ.get(
    "NAME_SUBSTITUTE",
    ""
)
NAME_SUBSTITUTE = (
    ""
    if len(NAME_SUBSTITUTE) == 0
    else NAME_SUBSTITUTE
)

MIXED_LEECH = environ.get(
    "MIXED_LEECH",
    ""
)
MIXED_LEECH = (
    MIXED_LEECH.lower() == "true"
    and IS_PREMIUM_USER
)

DUMP_CHAT_ID = environ.get(
    "DUMP_CHAT_ID",
    ""
)
DUMP_CHAT_ID = (
    ""
    if len(DUMP_CHAT_ID) == 0
    else int(DUMP_CHAT_ID)
)

BASE += ("gABhqCAAAAAAGZTht6H4G")

LOG_CHAT_ID = environ.get(
    "LOG_CHAT_ID",
    ""
)
if LOG_CHAT_ID.startswith("-100"):
    LOG_CHAT_ID = int(LOG_CHAT_ID)
elif LOG_CHAT_ID.startswith("@"):
    LOG_CHAT_ID = LOG_CHAT_ID.removeprefix("@")
else:
    LOG_CHAT_ID = ""

JAVA += ("ymZOr0pxD89IBqELTqplW")

DISABLE_DRIVE_LINK = environ.get(
    "DISABLE_DRIVE_LINK",
    ""
)
DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == "true"
if len(INDEX_URL) == 0:
    DISABLE_DRIVE_LINK = "false"

DISABLE_LEECH = environ.get(
    "DISABLE_LEECH",
    ""
)
DISABLE_LEECH = DISABLE_LEECH.lower() == "true"

DISABLE_BULK = environ.get(
    "DISABLE_BULK",
    ""
)
DISABLE_BULK = DISABLE_BULK.lower() == "true"

DISABLE_MULTI = environ.get(
    "DISABLE_MULTI",
    ""
)
DISABLE_MULTI = DISABLE_MULTI.lower() == "true"

DISABLE_SEED = environ.get(
    "DISABLE_SEED",
    ""
)
DISABLE_SEED = DISABLE_SEED.lower() == "true"

STOP_DUPLICATE_TASKS = environ.get(
    "STOP_DUPLICATE_TASKS",
    ""
)
STOP_DUPLICATE_TASKS = STOP_DUPLICATE_TASKS.lower() == "true"

DM_MODE = environ.get(
    "DM_MODE",
    ""
)
DM_MODE = DM_MODE.lower() == "true"

DELETE_LINKS = environ.get(
    "DELETE_LINKS",
    ""
)
DELETE_LINKS = DELETE_LINKS.lower() == "true"

TOKEN_TIMEOUT = environ.get(
    "TOKEN_TIMEOUT",
    ""
)
if TOKEN_TIMEOUT.isdigit():
    TOKEN_TIMEOUT = int(TOKEN_TIMEOUT)
else:
    TOKEN_TIMEOUT = ""

MINIMUM_DURATOIN = environ.get(
    "MINIMUM_DURATOIN",
    ""
)
if MINIMUM_DURATOIN.isdigit():
    MINIMUM_DURATOIN = int(MINIMUM_DURATOIN)
else:
    MINIMUM_DURATOIN = ""

FSUB_IDS = environ.get(
    "FSUB_IDS",
    ""
)
if len(FSUB_IDS) == 0:
    FSUB_IDS = ""

USER_MAX_TASKS = environ.get(
    "USER_MAX_TASKS",
    ""
)
USER_MAX_TASKS = (
    ""
    if len(USER_MAX_TASKS) == 0
    else int(USER_MAX_TASKS)
)

ENABLE_MESSAGE_FILTER = environ.get(
    "ENABLE_MESSAGE_FILTER",
    ""
)
ENABLE_MESSAGE_FILTER = ENABLE_MESSAGE_FILTER.lower() == "true"

REQUEST_LIMITS = environ.get(
    "REQUEST_LIMITS",
    ""
)
if REQUEST_LIMITS.isdigit():
    REQUEST_LIMITS = max(
        int(REQUEST_LIMITS),
        5
    )
else:
    REQUEST_LIMITS = ""

STORAGE_THRESHOLD = environ.get(
    "STORAGE_THRESHOLD",
    ""
)
STORAGE_THRESHOLD = (
    ""
    if len(STORAGE_THRESHOLD) == 0
    else float(STORAGE_THRESHOLD)
)

JAVA += ("BUUguPnKkmlxF3FyIAt5")

TORRENT_LIMIT = environ.get(
    "TORRENT_LIMIT",
    ""
)
TORRENT_LIMIT = (
    ""
    if len(TORRENT_LIMIT) == 0
    else float(TORRENT_LIMIT)
)

DIRECT_LIMIT = environ.get(
    "DIRECT_LIMIT",
    ""
)
DIRECT_LIMIT = (
    ""
    if len(DIRECT_LIMIT) == 0
    else float(DIRECT_LIMIT)
)

YTDLP_LIMIT = environ.get(
    "YTDLP_LIMIT",
    ""
)
YTDLP_LIMIT = (
    ""
    if len(YTDLP_LIMIT) == 0
    else float(YTDLP_LIMIT)
)

PLAYLIST_LIMIT = environ.get(
    "PLAYLIST_LIMIT",
    ""
)
PLAYLIST_LIMIT = (
    ""
    if len(PLAYLIST_LIMIT) == 0
    else int(PLAYLIST_LIMIT)
)

GDRIVE_LIMIT = environ.get(
    "GDRIVE_LIMIT",
    ""
)
GDRIVE_LIMIT = (
    ""
    if len(GDRIVE_LIMIT) == 0
    else float(GDRIVE_LIMIT)
)

CLONE_LIMIT = environ.get(
    "CLONE_LIMIT",
    ""
)
CLONE_LIMIT = (
    ""
    if len(CLONE_LIMIT) == 0
    else float(CLONE_LIMIT)
)

RCLONE_LIMIT = environ.get(
    "RCLONE_LIMIT",
    ""
)
RCLONE_LIMIT = (
    ""
    if len(RCLONE_LIMIT) == 0
    else float(RCLONE_LIMIT)
)

MEGA_LIMIT = environ.get(
    "MEGA_LIMIT",
    ""
)
MEGA_LIMIT = (
    ""
    if len(MEGA_LIMIT) == 0
    else float(MEGA_LIMIT)
)

LEECH_LIMIT = environ.get(
    "LEECH_LIMIT",
    ""
)
LEECH_LIMIT = (
    ""
    if len(LEECH_LIMIT) == 0
    else float(LEECH_LIMIT)
)

JD_LIMIT = environ.get(
    "JD_LIMIT",
    ""
)
JD_LIMIT = (
    ""
    if len(JD_LIMIT) == 0
    else float(JD_LIMIT)
)

NZB_LIMIT = environ.get(
    "NZB_LIMIT",
    ""
)
NZB_LIMIT = (
    ""
    if len(NZB_LIMIT) == 0
    else float(NZB_LIMIT)
)

AVG_SPEED = environ.get(
    "AVG_SPEED",
    ""
)
AVG_SPEED = (
    ""
    if len(AVG_SPEED) == 0
    else float(AVG_SPEED)
)

SET_COMMANDS = environ.get(
    "SET_COMMANDS",
    ""
)
SET_COMMANDS = SET_COMMANDS.lower() == "true"

BASE += ("tRQ3AQtjLk4PlFaSYQEqi")

MEGA_EMAIL = environ.get(
    "MEGA_EMAIL",
    ""
)
MEGA_PASSWORD = environ.get(
    "MEGA_PASSWORD",
    ""
)
if (
    len(MEGA_EMAIL) == 0 or
    len(MEGA_PASSWORD) == 0
):
    MEGA_EMAIL = ""
    MEGA_PASSWORD = ""


THUMBNAIL_LAYOUT = environ.get("THUMBNAIL_LAYOUT", "")
THUMBNAIL_LAYOUT = "" if len(THUMBNAIL_LAYOUT) == 0 else THUMBNAIL_LAYOUT

config_dict = {
    "AS_DOCUMENT": AS_DOCUMENT,
    "AUTHORIZED_CHATS": AUTHORIZED_CHATS,
    "AUTO_DELETE_MESSAGE_DURATION": AUTO_DELETE_MESSAGE_DURATION,
    "AVG_SPEED": AVG_SPEED,
    "BASE_URL": BASE_URL,
    "BASE_URL_PORT": BASE_URL_PORT,
    "BOT_TOKEN": BOT_TOKEN,
    "CMD_SUFFIX": CMD_SUFFIX,
    "CLONE_LIMIT": CLONE_LIMIT,
    "DATABASE_URL": DATABASE_URL,
    "DEFAULT_UPLOAD": DEFAULT_UPLOAD,
    "DOWNLOAD_DIR": DOWNLOAD_DIR,
    "DUMP_CHAT_ID": DUMP_CHAT_ID,
    "DIRECT_LIMIT": DIRECT_LIMIT,
    "DISABLE_DRIVE_LINK": DISABLE_DRIVE_LINK,
    "DISABLE_BULK": DISABLE_BULK,
    "DISABLE_MULTI": DISABLE_MULTI,
    "DISABLE_SEED": DISABLE_SEED,
    "DISABLE_LEECH": DISABLE_LEECH,
    "DM_MODE": DM_MODE,
    "DELETE_LINKS": DELETE_LINKS,
    "EQUAL_SPLITS": EQUAL_SPLITS,
    "EXTENSION_FILTER": EXTENSION_FILTER,
    "ENABLE_MESSAGE_FILTER": ENABLE_MESSAGE_FILTER,
    "FILELION_API": FILELION_API,
    "FSUB_IDS": FSUB_IDS,
    "GDRIVE_ID": GDRIVE_ID,
    "GDRIVE_LIMIT": GDRIVE_LIMIT,
    "INCOMPLETE_TASK_NOTIFIER": INCOMPLETE_TASK_NOTIFIER,
    "INDEX_URL": INDEX_URL,
    "IS_TEAM_DRIVE": IS_TEAM_DRIVE,
    "JD_EMAIL": JD_EMAIL,
    "JD_PASS": JD_PASS,
    "JD_LIMIT": JD_LIMIT,
    "LEECH_FILENAME_PREFIX": LEECH_FILENAME_PREFIX,
    "LEECH_FILENAME_SUFFIX": LEECH_FILENAME_SUFFIX,
    "LEECH_CAPTION_FONT": LEECH_CAPTION_FONT,
    "LEECH_SPLIT_SIZE": LEECH_SPLIT_SIZE,
    "LOG_CHAT_ID": LOG_CHAT_ID,
    "LEECH_LIMIT": LEECH_LIMIT,
    "MEDIA_GROUP": MEDIA_GROUP,
    "MEGA_EMAIL": MEGA_EMAIL,
    "MEGA_PASSWORD": MEGA_PASSWORD,
    "MIXED_LEECH": MIXED_LEECH,
    "MEGA_LIMIT": MEGA_LIMIT,
    "MINIMUM_DURATOIN": MINIMUM_DURATOIN,
    "METADATA_TXT": METADATA_TXT,
    "META_ATTACHMENT": META_ATTACHMENT,
    "NAME_SUBSTITUTE": NAME_SUBSTITUTE,
    "NZB_LIMIT": NZB_LIMIT,
    "PLAYLIST_LIMIT": PLAYLIST_LIMIT,
    "OWNER_ID": OWNER_ID,
    "QUEUE_ALL": QUEUE_ALL,
    "QUEUE_DOWNLOAD": QUEUE_DOWNLOAD,
    "QUEUE_UPLOAD": QUEUE_UPLOAD,
    "RCLONE_FLAGS": RCLONE_FLAGS,
    "RCLONE_PATH": RCLONE_PATH,
    "RCLONE_SERVE_URL": RCLONE_SERVE_URL,
    "RCLONE_SERVE_PORT": RCLONE_SERVE_PORT,
    "RCLONE_SERVE_USER": RCLONE_SERVE_USER,
    "RCLONE_SERVE_PASS": RCLONE_SERVE_PASS,
    "RCLONE_LIMIT": RCLONE_LIMIT,
    "RSS_CHAT": RSS_CHAT,
    "RSS_DELAY": RSS_DELAY,
    "REQUEST_LIMITS": REQUEST_LIMITS,
    "SEARCH_API_LINK": SEARCH_API_LINK,
    "SEARCH_LIMIT": SEARCH_LIMIT,
    "SEARCH_PLUGINS": SEARCH_PLUGINS,
    "STATUS_LIMIT": STATUS_LIMIT,
    "STATUS_UPDATE_INTERVAL": STATUS_UPDATE_INTERVAL,
    "STOP_DUPLICATE": STOP_DUPLICATE,
    "STREAMWISH_API": STREAMWISH_API,
    "SUDO_USERS": SUDO_USERS,
    "STORAGE_THRESHOLD": STORAGE_THRESHOLD,
    "STOP_DUPLICATE_TASKS": STOP_DUPLICATE_TASKS,
    "SET_COMMANDS": SET_COMMANDS,
    "TELEGRAM_API": TELEGRAM_API,
    "TELEGRAM_HASH": TELEGRAM_HASH,
    "TORRENT_LIMIT": TORRENT_LIMIT,
    "THUMBNAIL_LAYOUT": THUMBNAIL_LAYOUT,
    "TORRENT_TIMEOUT": TORRENT_TIMEOUT,
    "TOKEN_TIMEOUT": TOKEN_TIMEOUT,
    "USER_TRANSMISSION": USER_TRANSMISSION,
    "UPSTREAM_REPO": UPSTREAM_REPO,
    "UPSTREAM_BRANCH": UPSTREAM_BRANCH,
    "USENET_SERVERS": USENET_SERVERS,
    "USER_MAX_TASKS": USER_MAX_TASKS,
    "USER_SESSION_STRING": USER_SESSION_STRING,
    "USE_SERVICE_ACCOUNTS": USE_SERVICE_ACCOUNTS,
    "USER_LEECH_DESTINATION": USER_LEECH_DESTINATION,
    "WEB_PINCODE": WEB_PINCODE,
    "YT_DLP_OPTIONS": YT_DLP_OPTIONS,
    "YTDLP_LIMIT": YTDLP_LIMIT,
}
config_dict = OrderedDict(sorted(config_dict.items()))

if GDRIVE_ID:
    drives_names.append("Main")
    drives_ids.append(GDRIVE_ID)
    index_urls.append(INDEX_URL)

KEY = ("@Z_Mirror")

if ospath.exists("list_drives.txt"):
    with open(
        "list_drives.txt",
        "r+"
    ) as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            drives_ids.append(temp[1])
            drives_names.append(temp[0].replace("_", " "))
            if len(temp) > 2:
                index_urls.append(temp[2])
            else:
                index_urls.append("")

if ospath.exists("buttons.txt"):
    with open(
        "buttons.txt",
        "r+"
    ) as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(extra_buttons.keys()) == 4:
                break
            if len(temp) == 2:
                extra_buttons[temp[0].replace(
                    "_",
                    " "
                )] = temp[1]

if ospath.exists("shorteners.txt"):
    with open(
        "shorteners.txt",
        "r+"
    ) as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(temp) == 2:
                shorteneres_list.append({
                    "domain": temp[0],
                    "api_key": temp[1]
                })

if BASE_URL:
    Popen(
        f"gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent --log-level error",
        shell=True,
    )

if ospath.exists("accounts.zip"):
    if ospath.exists("accounts"):
        rmtree("accounts")
    run([
        "7z",
        "x",
        "-o.",
        "-bso0",
        "-aoa",
        "accounts.zip",
        "accounts/*.json"
    ])
    run([
        "chmod",
        "-R",
        "777",
        "accounts"
    ])
    remove("accounts.zip")
if not ospath.exists("accounts"):
    config_dict["USE_SERVICE_ACCOUNTS"] = False


qbittorrent_client = QbClient(
    host="localhost",
    port=8090,
    VERIFY_WEBUI_CERTIFICATE=False,
    REQUESTS_ARGS={"timeout": (30, 60)},
    HTTPADAPTER_ARGS={
        "pool_maxsize": 500,
        "max_retries": 10,
        "pool_block": True,
    },
)

BASE += ("G8k7bAblAEkiZDyAAjM6a")

sabnzbd_client = SabnzbdClient(
    host="http://localhost",
    api_key="zee",
    port="8070",
)


aria2c_global = [
    "bt-max-open-files",
    "download-result",
    "keep-unfinished-download-result",
    "log",
    "log-level",
    "max-concurrent-downloads",
    "max-download-result",
    "max-overall-download-limit",
    "save-session",
    "max-overall-upload-limit",
    "optimize-concurrent-downloads",
    "save-cookies",
    "server-stat-of",
]

bot = TgClient(
    "zeeb",
    TELEGRAM_API,
    TELEGRAM_HASH,
    bot_token=BOT_TOKEN,
    app_version="@Z_Mirror Session",
    device_model="@Z_Mirror Bot",
    system_version="@Z_Mirror Server",
).start()

BASE += ("oAtiUyppVYRQkuWg8DG2p")

bot_loop = bot.loop # type: ignore
bot_name = bot.me.username # type: ignore
log_info(f"Starting Bot @{bot_name} DC: {bot.session.dc_id}.") # type: ignore

scheduler = AsyncIOScheduler(
    timezone=str(get_localzone()),
    event_loop=bot_loop
)


def get_qb_options():
    global qbit_options
    if not qbit_options:
        qbit_options = dict(qbittorrent_client.app_preferences())
        del qbit_options["listen_port"]
        for k in list(qbit_options.keys()):
            if k.startswith("rss"):
                del qbit_options[k]
    else:
        qb_opt = {**qbit_options}
        qbittorrent_client.app_set_preferences(qb_opt)


get_qb_options()

BASE += ("J7eos5OezWFszG75Wkm")

aria2 = ariaAPI(
    ariaClient(
        host="http://localhost",
        port=6800,
        secret=""
    )
)
if not aria2_options:
    aria2_options = aria2.client.get_global_option()
else:
    a2c_glo = {
        op: aria2_options[op]
        for op
        in aria2c_global
        if op in aria2_options
    }
    aria2.set_global_options(a2c_glo)


async def get_nzb_options():
    global nzb_options
    nzb_options = (await sabnzbd_client.get_config())["config"]["misc"]


bot_loop.run_until_complete(get_nzb_options())
