#!/usr/bin/env python3
from asyncio import Lock
from collections import OrderedDict
from faulthandler import enable as faulthandler_enable
from logging import (ERROR, INFO, FileHandler, StreamHandler, basicConfig,
                     error, getLogger, info, warning)
from os import environ, path as ospath, remove, getcwd
from socket import setdefaulttimeout
from subprocess import Popen, run as zrun
from time import sleep, time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aria2p import API as ariaAPI
from aria2p import Client as ariaClient
from dotenv import load_dotenv
from pymongo import MongoClient
from pyrogram import Client as tgClient
from pyrogram import enums
from qbittorrentapi import Client as qbClient
from tzlocal import get_localzone
from uvloop import install

faulthandler_enable()
install()
setdefaulttimeout(600)

botStartTime = time()

basicConfig(format='%(levelname)s | From %(name)s -> %(module)s line no: %(lineno)d | %(message)s',
                    handlers=[FileHandler('Z_Logs.txt'), StreamHandler()], level=INFO)

LOGGER = getLogger(__name__)

getLogger("apscheduler").setLevel(ERROR)
getLogger("httpx").setLevel(ERROR)
getLogger("pyrogram").setLevel(ERROR)
getLogger("aria2c").setLevel(INFO)
getLogger("aria2p").setLevel(INFO)
getLogger("qbittorrentapi").setLevel(INFO)
getLogger("requests").setLevel(INFO)
getLogger("urllib3").setLevel(INFO)

load_dotenv('config.env', override=True)

aria2 = ariaAPI(ariaClient(host="http://localhost", port=6800, secret=""))

Interval = []
QbInterval = []
QbTorrents = {}
list_drives_dict = {}
shorteneres_list = []
extra_buttons = {}
GLOBAL_EXTENSION_FILTER = ['.aria2', '!qB']
user_data = {}
aria2_options = {}
qbit_options = {}
queued_dl = {}
queued_up = {}
categories_dict = {}
non_queued_dl = set()
non_queued_up = set()

try:
    if bool(environ.get('_____REMOVE_THIS_LINE_____')):
        error('README is there to be read! Read and try again! Exiting now!')
        exit()
except:
    pass

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
queue_dict_lock = Lock()
qb_listener_lock = Lock()
subprocess_lock = Lock()
status_reply_dict = {}
download_dict = {}
rss_dict = {}
cached_dict = {}

BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

bot_id = BOT_TOKEN.split(':', 1)[0]

DATABASE_URL = environ.get('DATABASE_URL', '')
if len(DATABASE_URL) == 0:
    DATABASE_URL = ''

if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.z
    # return config dict (all env vars)
    if config_dict := db.settings.config.find_one({'_id': bot_id}):
        del config_dict['_id']
        for key, value in config_dict.items():
            environ[key] = str(value)
    if pf_dict := db.settings.files.find_one({'_id': bot_id}):
        del pf_dict['_id']
        for key, value in pf_dict.items():
            if value:
                file_ = key.replace('__', '.')
                with open(file_, 'wb+') as f:
                    f.write(value)
    if a2c_options := db.settings.aria2c.find_one({'_id': bot_id}):
        del a2c_options['_id']
        aria2_options = a2c_options
    if qbit_opt := db.settings.qbittorrent.find_one({'_id': bot_id}):
        del qbit_opt['_id']
        qbit_options = qbit_opt
    conn.close()
    BOT_TOKEN = environ.get('BOT_TOKEN', '')
    bot_id = BOT_TOKEN.split(':', 1)[0]
    DATABASE_URL = environ.get('DATABASE_URL', '')
else:
    config_dict = {}

OWNER_ID = environ.get('OWNER_ID', '')
if len(OWNER_ID) == 0:
    error("OWNER_ID variable is missing! Exiting now")
    exit(1)
else:
    OWNER_ID = int(OWNER_ID)

TELEGRAM_API = environ.get('TELEGRAM_API', '')
if len(TELEGRAM_API) == 0:
    error("TELEGRAM_API variable is missing! Exiting now")
    exit(1)
else:
    TELEGRAM_API = int(TELEGRAM_API)

TELEGRAM_HASH = environ.get('TELEGRAM_HASH', '')
if len(TELEGRAM_HASH) == 0:
    error("TELEGRAM_HASH variable is missing! Exiting now")
    exit(1)

GDRIVE_ID = environ.get('GDRIVE_ID', '')
if len(GDRIVE_ID) == 0:
    warning('GDRIVE_ID not provided!')
    GDRIVE_ID = ''

RCLONE_PATH = environ.get('RCLONE_PATH', '')
if len(RCLONE_PATH) == 0:
    RCLONE_PATH = ''

RCLONE_FLAGS = environ.get('RCLONE_FLAGS', '')
if len(RCLONE_FLAGS) == 0:
    RCLONE_FLAGS = ''

DEFAULT_UPLOAD = environ.get('DEFAULT_UPLOAD', '')
if DEFAULT_UPLOAD != 'rc':
    DEFAULT_UPLOAD = 'gd'

DOWNLOAD_DIR = environ.get('DOWNLOAD_DIR', '')
if len(DOWNLOAD_DIR) == 0:
    DOWNLOAD_DIR = '/usr/src/app/downloads/'
elif not DOWNLOAD_DIR.endswith("/"):
    DOWNLOAD_DIR = f'{DOWNLOAD_DIR}/'

AUTHORIZED_CHATS = environ.get('AUTHORIZED_CHATS', '')
if len(AUTHORIZED_CHATS) != 0:
    aid = AUTHORIZED_CHATS.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_auth': True}

SUDO_USERS = environ.get('SUDO_USERS', '')
if len(SUDO_USERS) != 0:
    aid = SUDO_USERS.split()
    for id_ in aid:
        user_data[int(id_.strip())] = {'is_sudo': True}

EXTENSION_FILTER = environ.get('EXTENSION_FILTER', '')
if len(EXTENSION_FILTER) > 0:
    fx = EXTENSION_FILTER.split()
    for x in fx:
        if x.strip().startswith('.'):
            x = x.lstrip('.')
        GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

IS_PREMIUM_USER = False
user = ''
USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')
if len(USER_SESSION_STRING) != 0:
    user = tgClient('user', TELEGRAM_API, TELEGRAM_HASH, session_string=USER_SESSION_STRING,
                    workers=1000, parse_mode=enums.ParseMode.HTML, no_updates=True).start()
    if user.me.is_bot:
        error("You added bot string for USER_SESSION_STRING this is not allowed! Exiting now")
        user.stop()
        exit(1)
    else:
        IS_PREMIUM_USER = user.me.is_premium
        info(f"Successfully logged into @{user.me.username}...")

MEGA_EMAIL = environ.get('MEGA_EMAIL', '')
MEGA_PASSWORD = environ.get('MEGA_PASSWORD', '')
if len(MEGA_EMAIL) == 0 or len(MEGA_PASSWORD) == 0:
    MEGA_EMAIL = ''
    MEGA_PASSWORD = ''

FILELION_API = environ.get('FILELION_API', '')
if len(FILELION_API) == 0:
    FILELION_API = ''

STREAMWISH_API = environ.get('STREAMWISH_API', '')
if len(STREAMWISH_API) == 0:
    STREAMWISH_API = ''

JIODRIVE_ACCESS_TOKEN = environ.get('JIODRIVE_ACCESS_TOKEN', '')
if len(JIODRIVE_ACCESS_TOKEN) == 0:
    JIODRIVE_ACCESS_TOKEN = ''

INDEX_URL = environ.get('INDEX_URL', '').rstrip("/")
if len(INDEX_URL) == 0:
    INDEX_URL = ''

SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip("/")
if len(SEARCH_API_LINK) == 0:
    SEARCH_API_LINK = ''

LEECH_FILENAME_PREFIX = environ.get('LEECH_FILENAME_PREFIX', '')
if len(LEECH_FILENAME_PREFIX) == 0:
    LEECH_FILENAME_PREFIX = ''

LEECH_REMOVE_UNWANTED = environ.get('LEECH_REMOVE_UNWANTED', '')
if len(LEECH_REMOVE_UNWANTED) == 0:
    LEECH_REMOVE_UNWANTED = ''

SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
if len(SEARCH_PLUGINS) == 0:
    SEARCH_PLUGINS = ''

MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000

LEECH_SPLIT_SIZE = environ.get('LEECH_SPLIT_SIZE', '')
if len(LEECH_SPLIT_SIZE) == 0 or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE:
    LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
else:
    LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE)

STATUS_UPDATE_INTERVAL = environ.get('STATUS_UPDATE_INTERVAL', '')
if len(STATUS_UPDATE_INTERVAL) == 0:
    STATUS_UPDATE_INTERVAL = 10
else:
    STATUS_UPDATE_INTERVAL = int(STATUS_UPDATE_INTERVAL)

AUTO_DELETE_MESSAGE_DURATION = environ.get('AUTO_DELETE_MESSAGE_DURATION', '')
if len(AUTO_DELETE_MESSAGE_DURATION) == 0:
    AUTO_DELETE_MESSAGE_DURATION = 30
else:
    AUTO_DELETE_MESSAGE_DURATION = int(AUTO_DELETE_MESSAGE_DURATION)

YT_DLP_OPTIONS = environ.get('YT_DLP_OPTIONS', '')
if len(YT_DLP_OPTIONS) == 0:
    YT_DLP_OPTIONS = ''

SEARCH_LIMIT = environ.get('SEARCH_LIMIT', '')
SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

DUMP_CHAT_ID = environ.get('DUMP_CHAT_ID', '')
DUMP_CHAT_ID = '' if len(DUMP_CHAT_ID) == 0 else int(DUMP_CHAT_ID)

STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
STATUS_LIMIT = 5 if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)

CMD_SUFFIX = environ.get('CMD_SUFFIX', '')

RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
RSS_CHAT_ID = '' if len(RSS_CHAT_ID) == 0 else int(RSS_CHAT_ID)

RSS_DELAY = environ.get('RSS_DELAY', '')
RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)

TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
TORRENT_TIMEOUT = '' if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

QUEUE_ALL = environ.get('QUEUE_ALL', '')
QUEUE_ALL = '' if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)

QUEUE_DOWNLOAD = environ.get('QUEUE_DOWNLOAD', '')
QUEUE_DOWNLOAD = '' if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)

QUEUE_UPLOAD = environ.get('QUEUE_UPLOAD', '')
QUEUE_UPLOAD = '' if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)

INCOMPLETE_TASK_NOTIFIER = environ.get('INCOMPLETE_TASK_NOTIFIER', '')
INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'

STOP_DUPLICATE = environ.get('STOP_DUPLICATE', '')
STOP_DUPLICATE = STOP_DUPLICATE.lower() == 'true'

IS_TEAM_DRIVE = environ.get('IS_TEAM_DRIVE', '')
IS_TEAM_DRIVE = IS_TEAM_DRIVE.lower() == 'true'

USE_SERVICE_ACCOUNTS = environ.get('USE_SERVICE_ACCOUNTS', '')
USE_SERVICE_ACCOUNTS = USE_SERVICE_ACCOUNTS.lower() == 'true'

WEB_PINCODE = environ.get('WEB_PINCODE', '')
WEB_PINCODE = WEB_PINCODE.lower() == 'true'

AS_DOCUMENT = environ.get('AS_DOCUMENT', '')
AS_DOCUMENT = AS_DOCUMENT.lower() == 'true'

EQUAL_SPLITS = environ.get('EQUAL_SPLITS', '')
EQUAL_SPLITS = EQUAL_SPLITS.lower() == 'true'

MEDIA_GROUP = environ.get('MEDIA_GROUP', '')
MEDIA_GROUP = MEDIA_GROUP.lower() == 'true'

BASE_URL_PORT = environ.get('BASE_URL_PORT', '')
BASE_URL_PORT = 80 if len(BASE_URL_PORT) == 0 else int(BASE_URL_PORT)

BASE_URL = environ.get('BASE_URL', '').rstrip("/")
if len(BASE_URL) == 0:
    BASE_URL = ''

UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = 'https://github.com/Dawn-India/Z-Mirror'

UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', '')
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = 'main'

RCLONE_SERVE_URL = environ.get('RCLONE_SERVE_URL', '').rstrip("/")
if len(RCLONE_SERVE_URL) == 0:
    RCLONE_SERVE_URL = ''

RCLONE_SERVE_PORT = environ.get('RCLONE_SERVE_PORT', '')
RCLONE_SERVE_PORT = 8080 if len(
    RCLONE_SERVE_PORT) == 0 else int(RCLONE_SERVE_PORT)

RCLONE_SERVE_USER = environ.get('RCLONE_SERVE_USER', '')
if len(RCLONE_SERVE_USER) == 0:
    RCLONE_SERVE_USER = ''

RCLONE_SERVE_PASS = environ.get('RCLONE_SERVE_PASS', '')
if len(RCLONE_SERVE_PASS) == 0:
    RCLONE_SERVE_PASS = ''

LOG_CHAT_ID = environ.get('LOG_CHAT_ID', '')
if LOG_CHAT_ID.startswith('-100'):
    LOG_CHAT_ID = int(LOG_CHAT_ID)
elif LOG_CHAT_ID.startswith('@'):
    LOG_CHAT_ID = LOG_CHAT_ID.removeprefix('@')
else:
    LOG_CHAT_ID = ''

USER_MAX_TASKS = environ.get('USER_MAX_TASKS', '')
USER_MAX_TASKS = '' if len(USER_MAX_TASKS) == 0 else int(USER_MAX_TASKS)

STORAGE_THRESHOLD = environ.get('STORAGE_THRESHOLD', '')
STORAGE_THRESHOLD = '' if len(
    STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

TORRENT_LIMIT = environ.get('TORRENT_LIMIT', '')
TORRENT_LIMIT = '' if len(TORRENT_LIMIT) == 0 else float(TORRENT_LIMIT)

DIRECT_LIMIT = environ.get('DIRECT_LIMIT', '')
DIRECT_LIMIT = '' if len(DIRECT_LIMIT) == 0 else float(DIRECT_LIMIT)

YTDLP_LIMIT = environ.get('YTDLP_LIMIT', '')
YTDLP_LIMIT = '' if len(YTDLP_LIMIT) == 0 else float(YTDLP_LIMIT)

PLAYLIST_LIMIT = environ.get('PLAYLIST_LIMIT', '')
PLAYLIST_LIMIT = '' if len(PLAYLIST_LIMIT) == 0 else int(PLAYLIST_LIMIT)

GDRIVE_LIMIT = environ.get('GDRIVE_LIMIT', '')
GDRIVE_LIMIT = '' if len(GDRIVE_LIMIT) == 0 else float(GDRIVE_LIMIT)

CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
CLONE_LIMIT = '' if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
MEGA_LIMIT = '' if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

LEECH_LIMIT = environ.get('LEECH_LIMIT', '')
LEECH_LIMIT = '' if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

ENABLE_MESSAGE_FILTER = environ.get('ENABLE_MESSAGE_FILTER', '')
ENABLE_MESSAGE_FILTER = ENABLE_MESSAGE_FILTER.lower() == 'true'

STOP_DUPLICATE_TASKS = environ.get('STOP_DUPLICATE_TASKS', '')
STOP_DUPLICATE_TASKS = STOP_DUPLICATE_TASKS.lower() == 'true'

DISABLE_DRIVE_LINK = environ.get('DISABLE_DRIVE_LINK', '')
DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == 'true'

DISABLE_LEECH = environ.get('DISABLE_LEECH', '')
DISABLE_LEECH = DISABLE_LEECH.lower() == 'true'

SET_COMMANDS = environ.get('SET_COMMANDS', '')
SET_COMMANDS = SET_COMMANDS.lower() == 'true'

REQUEST_LIMITS = environ.get('REQUEST_LIMITS', '')
if REQUEST_LIMITS.isdigit():
    REQUEST_LIMITS = max(int(REQUEST_LIMITS), 5)
else:
    REQUEST_LIMITS = ''

DM_MODE = environ.get('DM_MODE', '')
DM_MODE = DM_MODE.lower() if DM_MODE.lower() in [
    'leech', 'mirror', 'all'] else ''

DELETE_LINKS = environ.get('DELETE_LINKS', '')
DELETE_LINKS = DELETE_LINKS.lower() == 'true'

TOKEN_TIMEOUT = environ.get('TOKEN_TIMEOUT', '')
if TOKEN_TIMEOUT.isdigit():
    TOKEN_TIMEOUT = int(TOKEN_TIMEOUT)
else:
    TOKEN_TIMEOUT = ''

FSUB_IDS = environ.get('FSUB_IDS', '')
if len(FSUB_IDS) == 0:
    FSUB_IDS = ''

USER_DUMP = environ.get('USER_DUMP', '')
USER_DUMP = '' if len(USER_DUMP) == 0 else USER_DUMP
if USER_DUMP.isdigit() or USER_DUMP.startswith('-'):
    USER_DUMP = int(USER_DUMP)

config_dict = {
    "AS_DOCUMENT": AS_DOCUMENT,
    "AUTHORIZED_CHATS": AUTHORIZED_CHATS,
    "AUTO_DELETE_MESSAGE_DURATION": AUTO_DELETE_MESSAGE_DURATION,
    "BASE_URL": BASE_URL,
    "BASE_URL_PORT": BASE_URL_PORT,
    "BOT_TOKEN": BOT_TOKEN,
    "CMD_SUFFIX": CMD_SUFFIX,
    "DATABASE_URL": DATABASE_URL,
    "DEFAULT_UPLOAD": DEFAULT_UPLOAD,
    "DOWNLOAD_DIR": DOWNLOAD_DIR,
    "DUMP_CHAT_ID": DUMP_CHAT_ID,
    "EQUAL_SPLITS": EQUAL_SPLITS,
    "EXTENSION_FILTER": EXTENSION_FILTER,
    "FILELION_API": FILELION_API,
    "GDRIVE_ID": GDRIVE_ID,
    "INCOMPLETE_TASK_NOTIFIER": INCOMPLETE_TASK_NOTIFIER,
    "INDEX_URL": INDEX_URL,
    "IS_TEAM_DRIVE": IS_TEAM_DRIVE,
    "JIODRIVE_ACCESS_TOKEN": JIODRIVE_ACCESS_TOKEN,
    "LEECH_FILENAME_PREFIX": LEECH_FILENAME_PREFIX,
    "LEECH_REMOVE_UNWANTED": LEECH_REMOVE_UNWANTED,
    "LEECH_SPLIT_SIZE": LEECH_SPLIT_SIZE,
    "MEDIA_GROUP": MEDIA_GROUP,
    "MEGA_EMAIL": MEGA_EMAIL,
    "MEGA_PASSWORD": MEGA_PASSWORD,
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
    "RSS_CHAT_ID": RSS_CHAT_ID,
    "RSS_DELAY": RSS_DELAY,
    "SEARCH_API_LINK": SEARCH_API_LINK,
    "SEARCH_LIMIT": SEARCH_LIMIT,
    "SEARCH_PLUGINS": SEARCH_PLUGINS,
    "STATUS_LIMIT": STATUS_LIMIT,
    "STATUS_UPDATE_INTERVAL": STATUS_UPDATE_INTERVAL,
    "STOP_DUPLICATE": STOP_DUPLICATE,
    'STREAMWISH_API': STREAMWISH_API,
    "SUDO_USERS": SUDO_USERS,
    "TELEGRAM_API": TELEGRAM_API,
    "TELEGRAM_HASH": TELEGRAM_HASH,
    "TORRENT_TIMEOUT": TORRENT_TIMEOUT,
    "UPSTREAM_REPO": UPSTREAM_REPO,
    "UPSTREAM_BRANCH": UPSTREAM_BRANCH,
    "USER_DUMP": USER_DUMP,
    "USER_SESSION_STRING": USER_SESSION_STRING,
    "USE_SERVICE_ACCOUNTS": USE_SERVICE_ACCOUNTS,
    "WEB_PINCODE": WEB_PINCODE,
    "YT_DLP_OPTIONS": YT_DLP_OPTIONS,
    "USER_MAX_TASKS": USER_MAX_TASKS,
    "LOG_CHAT_ID": LOG_CHAT_ID,
    "FSUB_IDS": FSUB_IDS,
    "STORAGE_THRESHOLD": STORAGE_THRESHOLD,
    "TORRENT_LIMIT": TORRENT_LIMIT,
    "DIRECT_LIMIT": DIRECT_LIMIT,
    "YTDLP_LIMIT": YTDLP_LIMIT,
    "PLAYLIST_LIMIT": PLAYLIST_LIMIT,
    "GDRIVE_LIMIT": GDRIVE_LIMIT,
    "CLONE_LIMIT": CLONE_LIMIT,
    "MEGA_LIMIT": MEGA_LIMIT,
    "LEECH_LIMIT": LEECH_LIMIT,
    "ENABLE_MESSAGE_FILTER": ENABLE_MESSAGE_FILTER,
    "STOP_DUPLICATE_TASKS": STOP_DUPLICATE_TASKS,
    "DISABLE_DRIVE_LINK": DISABLE_DRIVE_LINK,
    "SET_COMMANDS": SET_COMMANDS,
    "DISABLE_LEECH": DISABLE_LEECH,
    "REQUEST_LIMITS": REQUEST_LIMITS,
    "DM_MODE": DM_MODE,
    "DELETE_LINKS": DELETE_LINKS,
    "TOKEN_TIMEOUT": TOKEN_TIMEOUT
}

config_dict = OrderedDict(sorted(config_dict.items()))

if GDRIVE_ID:
    list_drives_dict['Main'] = {"drive_id": GDRIVE_ID, "index_link": INDEX_URL}
    categories_dict['Root'] = {"drive_id": GDRIVE_ID, "index_link": INDEX_URL}

if ospath.exists('list_drives.txt'):
    with open('list_drives.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            name = temp[0].replace("_", " ")
            if name.casefold() == "Main":
                name = "Main Custom"
            tempdict = {}
            tempdict['drive_id'] = temp[1]
            if len(temp) > 2:
                tempdict['index_link'] = temp[2]
            else:
                tempdict['index_link'] = ''
            list_drives_dict[name] = tempdict

if ospath.exists('buttons.txt'):
    with open('buttons.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(extra_buttons.keys()) == 4:
                break
            if len(temp) == 2:
                extra_buttons[temp[0].replace("_", " ")] = temp[1]

if ospath.exists('shorteners.txt'):
    with open('shorteners.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(temp) == 2:
                shorteneres_list.append({'domain': temp[0],'api_key': temp[1]})

if ospath.exists('categories.txt'):
    with open('categories.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            name = temp[0].replace("_", " ")
            if name.casefold() == "Root":
                name = "Root Custom"
            tempdict = {}
            tempdict['drive_id'] = temp[1]
            if len(temp) > 2:
                tempdict['index_link'] = temp[2]
            else:
                tempdict['index_link'] = ''
            categories_dict[name] = tempdict

if BASE_URL:
    Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{BASE_URL_PORT} --worker-class gevent", shell=True)

zrun(["qbittorrent-nox", "-d", f"--profile={getcwd()}"])
if not ospath.exists('.netrc'):
    with open('.netrc', 'w'):
        pass
zrun("chmod 600 .netrc && cp .netrc /root/.netrc && chmod +x aria.sh && ./aria.sh", shell=True,)
if ospath.exists('accounts.zip'):
    if ospath.exists('accounts'):
        zrun(["rm", "-rf", "accounts"])
    zrun(["7z", "x", "-o.", "-bso0", "-aoa", "accounts.zip", "accounts/*.json", "&&", "chmod", "-R", "777", "accounts"])
    remove('accounts.zip')
if not ospath.exists('accounts'):
    config_dict['USE_SERVICE_ACCOUNTS'] = False
sleep(0.5)


def get_client():
    return qbClient(host="localhost", port=8090, REQUESTS_ARGS={"timeout": (30, 60)})


aria2c_global = ['bt-max-open-files', 'download-result', 'keep-unfinished-download-result', 'log', 'log-level',
                 'max-concurrent-downloads', 'max-download-result', 'max-overall-download-limit', 'save-session',
                 'max-overall-upload-limit', 'optimize-concurrent-downloads', 'save-cookies', 'server-stat-of']

qb_client = get_client()
if not qbit_options:
    qbit_options = dict(qb_client.app_preferences())
    del qbit_options['listen_port']
    for k in list(qbit_options.keys()):
        if k.startswith('rss'):
            del qbit_options[k]
else:
    qb_opt = {**qbit_options}
    for k, v in list(qb_opt.items()):
        if v in ["", "*"]:
            del qb_opt[k]
    qb_client.app_set_preferences(qb_opt)

bot = tgClient('bot',
            TELEGRAM_API,
            TELEGRAM_HASH,
            bot_token=BOT_TOKEN,
            workers=1000,
            parse_mode=enums.ParseMode.HTML
            ).start()

bot_loop = bot.loop
bot_name = bot.me.username
info(f"Starting Bot @{bot_name}...")
scheduler = AsyncIOScheduler(timezone=str(get_localzone()), event_loop=bot_loop)

if not aria2_options:
    aria2_options = aria2.client.get_global_option()
else:
    a2c_glo = {op: aria2_options[op] for op in aria2c_global if op in aria2_options}
    aria2.set_global_options(a2c_glo)
