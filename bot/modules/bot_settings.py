from functools import partial
from os import environ, path, remove, rename
from subprocess import Popen, run
from time import sleep, time

from dotenv import load_dotenv
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler)

from bot import (DATABASE_URL, GLOBAL_EXTENSION_FILTER, IS_PREMIUM_USER,
                 LOGGER, MAX_SPLIT_SIZE, SHORTENER_APIS, SHORTENERES, Interval,
                 aria2, aria2_options, aria2c_global, categories, config_dict,
                 dispatcher, download_dict, extra_buttons, get_client,
                 list_drives, qbit_options, status_reply_dict_lock, user_data)
from bot.helper.ext_utils.bot_utils import (get_readable_file_size, new_thread,
                                            set_commands, setInterval)
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.queued_starter import start_from_queued
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (editMessage, sendFile,
                                                      sendMessage,
                                                      update_all_messages)
from bot.modules.search import initiate_search_tools

START = 0
STATE = 'view'
handler_dict = {}
default_values = {'AUTO_DELETE_MESSAGE_DURATION': 30,
                  'DOWNLOAD_DIR': '/usr/src/app/downloads/',
                  'LEECH_SPLIT_SIZE': MAX_SPLIT_SIZE,
                  'RSS_DELAY': 900,
                  'DOWNLOAD_STATUS_UPDATE_INTERVAL': 10,
                  'SEARCH_LIMIT': 0,
                  'UPSTREAM_BRANCH': 'master'}


def load_config():

    BOT_TOKEN = environ.get('BOT_TOKEN', '')
    if len(BOT_TOKEN) == 0:
        BOT_TOKEN = config_dict['BOT_TOKEN']

    TELEGRAM_API = environ.get('TELEGRAM_API', '')
    if len(TELEGRAM_API) == 0:
        TELEGRAM_API = config_dict['TELEGRAM_API']
    else:
        TELEGRAM_API = int(TELEGRAM_API)

    TELEGRAM_HASH = environ.get('TELEGRAM_HASH', '')
    if len(TELEGRAM_HASH) == 0:
        TELEGRAM_HASH = config_dict['TELEGRAM_HASH']

    OWNER_ID = environ.get('OWNER_ID', '')
    if len(OWNER_ID) == 0:
        OWNER_ID = config_dict['OWNER_ID']
    else:
        OWNER_ID = int(OWNER_ID)

    DATABASE_URL = environ.get('DATABASE_URL', '')
    if len(DATABASE_URL) == 0:
        DATABASE_URL = ''

    DOWNLOAD_DIR = environ.get('DOWNLOAD_DIR', '')
    if len(DOWNLOAD_DIR) == 0:
        DOWNLOAD_DIR = '/usr/src/app/downloads/'
    elif not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR = f'{DOWNLOAD_DIR}/'

    GDRIVE_ID = environ.get('GDRIVE_ID', '')
    if len(GDRIVE_ID) == 0:
        GDRIVE_ID = ''

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
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.append('.aria2')
        for x in fx:
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

    MEGA_API_KEY = environ.get('MEGA_API_KEY', '')
    if len(MEGA_API_KEY) == 0:
        MEGA_API_KEY = ''

    MEGA_EMAIL_ID = environ.get('MEGA_EMAIL_ID', '')
    MEGA_PASSWORD = environ.get('MEGA_PASSWORD', '')
    if len(MEGA_EMAIL_ID) == 0 or len(MEGA_PASSWORD) == 0:
        MEGA_EMAIL_ID = ''
        MEGA_PASSWORD = ''

    UPTOBOX_TOKEN = environ.get('UPTOBOX_TOKEN', '')
    if len(UPTOBOX_TOKEN) == 0:
        UPTOBOX_TOKEN = ''

    INDEX_URL = environ.get('INDEX_URL', '').rstrip("/")
    if len(INDEX_URL) == 0:
        INDEX_URL = ''

    SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip("/")
    if len(SEARCH_API_LINK) == 0:
        SEARCH_API_LINK = ''

    RSS_COMMAND = environ.get('RSS_COMMAND', '')
    if len(RSS_COMMAND) == 0:
        RSS_COMMAND = ''

    LEECH_FILENAME_PREFIX = environ.get('LEECH_FILENAME_PREFIX', '')
    if len(LEECH_FILENAME_PREFIX) == 0:
        LEECH_FILENAME_PREFIX = ''

    SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
    if len(SEARCH_PLUGINS) == 0:
        SEARCH_PLUGINS = ''

    MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000

    LEECH_SPLIT_SIZE = environ.get('LEECH_SPLIT_SIZE', '')
    if len(LEECH_SPLIT_SIZE) == 0 or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE:
        LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
    else:
        LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE)

    DOWNLOAD_STATUS_UPDATE_INTERVAL = environ.get('DOWNLOAD_STATUS_UPDATE_INTERVAL', '')
    if len(DOWNLOAD_STATUS_UPDATE_INTERVAL) == 0:
        DOWNLOAD_STATUS_UPDATE_INTERVAL = 10
    else:
        DOWNLOAD_STATUS_UPDATE_INTERVAL = int(DOWNLOAD_STATUS_UPDATE_INTERVAL)
    if len(download_dict) != 0:
        with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(setInterval(DOWNLOAD_STATUS_UPDATE_INTERVAL, update_all_messages))

    AUTO_DELETE_MESSAGE_DURATION = environ.get('AUTO_DELETE_MESSAGE_DURATION', '')
    if len(AUTO_DELETE_MESSAGE_DURATION) == 0:
        AUTO_DELETE_MESSAGE_DURATION = 30
    else:
        AUTO_DELETE_MESSAGE_DURATION = int(AUTO_DELETE_MESSAGE_DURATION)

    YT_DLP_QUALITY = environ.get('YT_DLP_QUALITY', '')
    if len(YT_DLP_QUALITY) == 0:
        YT_DLP_QUALITY = ''

    SEARCH_LIMIT = environ.get('SEARCH_LIMIT', '')
    SEARCH_LIMIT = 0 if len(SEARCH_LIMIT) == 0 else int(SEARCH_LIMIT)

    DUMP_CHAT = environ.get('DUMP_CHAT', '')
    DUMP_CHAT = '' if len(DUMP_CHAT) == 0 else int(DUMP_CHAT)

    LOG_CHAT = environ.get('LOG_CHAT', '')
    LOG_CHAT = '' if len(LOG_CHAT) == 0 else int(LOG_CHAT)

    STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
    STATUS_LIMIT = '' if len(STATUS_LIMIT) == 0 else int(STATUS_LIMIT)

    USER_MAX_TASKS = environ.get('USER_MAX_TASKS', '')
    USER_MAX_TASKS = '' if len(USER_MAX_TASKS) == 0 else int(USER_MAX_TASKS)

    RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
    RSS_CHAT_ID = '' if len(RSS_CHAT_ID) == 0 else int(RSS_CHAT_ID)

    RSS_DELAY = environ.get('RSS_DELAY', '')
    RSS_DELAY = 900 if len(RSS_DELAY) == 0 else int(RSS_DELAY)

    CMD_SUFFIX = environ.get('CMD_SUFFIX', '')

    USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')

    RSS_USER_SESSION_STRING = environ.get('RSS_USER_SESSION_STRING', '')

    TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
    downloads = aria2.get_downloads()
    if len(TORRENT_TIMEOUT) == 0:
        for download in downloads:
            if not download.is_complete:
                try:
                    aria2.client.change_option(download.gid, {'bt-stop-timeout': '0'})
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = '0'
        if DATABASE_URL:
            DbManger().update_aria2('bt-stop-timeout', '0')
        TORRENT_TIMEOUT = ''
    else:
        for download in downloads:
            if not download.is_complete:
                try:
                    aria2.client.change_option(download.gid, {'bt-stop-timeout': TORRENT_TIMEOUT})
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = TORRENT_TIMEOUT
        if DATABASE_URL:
            DbManger().update_aria2('bt-stop-timeout', TORRENT_TIMEOUT)
        TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)

    QUEUE_ALL = environ.get('QUEUE_ALL', '')
    QUEUE_ALL = '' if len(QUEUE_ALL) == 0 else int(QUEUE_ALL)

    QUEUE_DOWNLOAD = environ.get('QUEUE_DOWNLOAD', '')
    QUEUE_DOWNLOAD = '' if len(QUEUE_DOWNLOAD) == 0 else int(QUEUE_DOWNLOAD)

    QUEUE_UPLOAD = environ.get('QUEUE_UPLOAD', '')
    QUEUE_UPLOAD = '' if len(QUEUE_UPLOAD) == 0 else int(QUEUE_UPLOAD)

    INCOMPLETE_TASK_NOTIFIER = environ.get('INCOMPLETE_TASK_NOTIFIER', '')
    INCOMPLETE_TASK_NOTIFIER = INCOMPLETE_TASK_NOTIFIER.lower() == 'true'

    if not INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        DbManger().trunc_table('tasks')

    STOP_DUPLICATE = environ.get('STOP_DUPLICATE', '')
    STOP_DUPLICATE = STOP_DUPLICATE.lower() == 'true'

    VIEW_LINK = environ.get('VIEW_LINK', '')
    VIEW_LINK = VIEW_LINK.lower() == 'true'

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

    IGNORE_PENDING_REQUESTS = environ.get('IGNORE_PENDING_REQUESTS', '')
    IGNORE_PENDING_REQUESTS = IGNORE_PENDING_REQUESTS.lower() == 'true'

    SERVER_PORT = environ.get('SERVER_PORT', '')
    SERVER_PORT = 80 if len(SERVER_PORT) == 0 else int(SERVER_PORT)
    BASE_URL = environ.get('BASE_URL', '').rstrip("/")
    if len(BASE_URL) == 0:
        BASE_URL = ''
        run(["pkill", "-9", "-f", "gunicorn"])
    else:
        run(["pkill", "-9", "-f", "gunicorn"])
        Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{SERVER_PORT}", shell=True)

    UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
    if len(UPSTREAM_REPO) == 0:
       UPSTREAM_REPO = ''

    UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', '')
    if len(UPSTREAM_BRANCH) == 0:
        UPSTREAM_BRANCH = 'master'

    STORAGE_THRESHOLD = environ.get('STORAGE_THRESHOLD', '')
    STORAGE_THRESHOLD = '' if len(STORAGE_THRESHOLD) == 0 else float(STORAGE_THRESHOLD)

    TORRENT_LIMIT = environ.get('TORRENT_LIMIT', '')
    TORRENT_LIMIT = '' if len(TORRENT_LIMIT) == 0 else float(TORRENT_LIMIT)

    DIRECT_LIMIT = environ.get('DIRECT_LIMIT', '')
    DIRECT_LIMIT = '' if len(DIRECT_LIMIT) == 0 else float(DIRECT_LIMIT)

    YTDLP_LIMIT = environ.get('YTDLP_LIMIT', '')
    YTDLP_LIMIT = '' if len(YTDLP_LIMIT) == 0 else float(YTDLP_LIMIT)

    GDRIVE_LIMIT = environ.get('GDRIVE_LIMIT', '')
    GDRIVE_LIMIT = '' if len(GDRIVE_LIMIT) == 0 else float(GDRIVE_LIMIT)

    CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
    CLONE_LIMIT = '' if len(CLONE_LIMIT) == 0 else float(CLONE_LIMIT)

    MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
    MEGA_LIMIT = '' if len(MEGA_LIMIT) == 0 else float(MEGA_LIMIT)

    LEECH_LIMIT = environ.get('LEECH_LIMIT', '')
    LEECH_LIMIT = '' if len(LEECH_LIMIT) == 0 else float(LEECH_LIMIT)

    MAX_PLAYLIST = environ.get('MAX_PLAYLIST', '')
    MAX_PLAYLIST = '' if len(MAX_PLAYLIST) == 0 else int(MAX_PLAYLIST)

    ENABLE_RATE_LIMIT = environ.get('ENABLE_RATE_LIMIT', '')
    ENABLE_RATE_LIMIT = ENABLE_RATE_LIMIT.lower() == 'true'

    ENABLE_MESSAGE_FILTER = environ.get('ENABLE_MESSAGE_FILTER', '')
    ENABLE_MESSAGE_FILTER = ENABLE_MESSAGE_FILTER.lower() == 'true'

    STOP_DUPLICATE_TASKS = environ.get('STOP_DUPLICATE_TASKS', '')
    STOP_DUPLICATE_TASKS = STOP_DUPLICATE_TASKS.lower() == 'true'

    if not STOP_DUPLICATE_TASKS and DATABASE_URL:
        DbManger().clear_download_links()

    DISABLE_DRIVE_LINK = environ.get('DISABLE_DRIVE_LINK', '')
    DISABLE_DRIVE_LINK = DISABLE_DRIVE_LINK.lower() == 'true'

    DISABLE_LEECH = environ.get('DISABLE_LEECH', '')
    DISABLE_LEECH = DISABLE_LEECH.lower() == 'true'

    SET_COMMANDS = environ.get('SET_COMMANDS', '')
    SET_COMMANDS = SET_COMMANDS.lower() == 'true'

    DM_MODE = environ.get('DM_MODE', '')
    DM_MODE = DM_MODE.lower() if DM_MODE.lower() in ['leech', 'mirror', 'all'] else ''

    DELETE_LINKS = environ.get('DELETE_LINKS', '')
    DELETE_LINKS = DELETE_LINKS.lower() == 'true'

    FSUB_IDS = environ.get('FSUB_IDS', '')
    if len(FSUB_IDS) == 0:
        FSUB_IDS = ''

    list_drives.clear()
    categories.clear()

    if GDRIVE_ID:
        list_drives['Main'] = {"drive_id": GDRIVE_ID, "index_link": INDEX_URL}
        categories['Root'] = {"drive_id": GDRIVE_ID, "index_link": INDEX_URL}

    if path.exists('list_drives.txt'):
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
                list_drives[name] = tempdict

    if path.exists('categories.txt'):
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
                categories[name] = tempdict

    extra_buttons.clear()
    if path.exists('buttons.txt'):
        with open('buttons.txt', 'r+') as f:
            lines = f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(extra_buttons.keys()) == 4:
                    break
                if len(temp) == 2:
                    extra_buttons[temp[0].replace("_", " ")] = temp[1]

    SHORTENERES.clear()
    SHORTENER_APIS.clear()
    if path.exists('shorteners.txt'):
        with open('shorteners.txt', 'r+') as f:
            lines = f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    SHORTENERES.append(temp[0])
                    SHORTENER_APIS.append(temp[1])

    if path.exists('accounts.zip'):
        if path.exists('accounts'):
            run(["rm", "-rf", "accounts"])
        run(["unzip", "-q", "-o", "accounts.zip", "-W", "accounts/*.json"])
        run(["chmod", "-R", "777", "accounts"])
        remove('accounts.zip')
    if not path.exists('accounts'):
        USE_SERVICE_ACCOUNTS = False

    config_dict.update({'AS_DOCUMENT': AS_DOCUMENT,
                   'AUTHORIZED_CHATS': AUTHORIZED_CHATS,
                   'FSUB_IDS': FSUB_IDS,
                   'AUTO_DELETE_MESSAGE_DURATION': AUTO_DELETE_MESSAGE_DURATION,
                   'BASE_URL': BASE_URL,
                   'BOT_TOKEN': BOT_TOKEN,
                   'CMD_SUFFIX': CMD_SUFFIX,
                   'DATABASE_URL': DATABASE_URL,
                   'DOWNLOAD_DIR': DOWNLOAD_DIR,
                   'DUMP_CHAT': DUMP_CHAT,
                   'LOG_CHAT': LOG_CHAT,
                   'EQUAL_SPLITS': EQUAL_SPLITS,
                   'EXTENSION_FILTER': EXTENSION_FILTER,
                   'GDRIVE_ID': GDRIVE_ID,
                   'IGNORE_PENDING_REQUESTS': IGNORE_PENDING_REQUESTS,
                   'INCOMPLETE_TASK_NOTIFIER': INCOMPLETE_TASK_NOTIFIER,
                   'INDEX_URL': INDEX_URL,
                   'IS_TEAM_DRIVE': IS_TEAM_DRIVE,
                   'LEECH_FILENAME_PREFIX': LEECH_FILENAME_PREFIX,
                   'LEECH_SPLIT_SIZE': LEECH_SPLIT_SIZE,
                   'MEDIA_GROUP': MEDIA_GROUP,
                   'MEGA_API_KEY': MEGA_API_KEY,
                   'MEGA_EMAIL_ID': MEGA_EMAIL_ID,
                   'MEGA_PASSWORD': MEGA_PASSWORD,
                   'OWNER_ID': OWNER_ID,
                   'QUEUE_ALL': QUEUE_ALL,
                   'QUEUE_DOWNLOAD': QUEUE_DOWNLOAD,
                   'QUEUE_UPLOAD': QUEUE_UPLOAD,
                   'RSS_USER_SESSION_STRING': RSS_USER_SESSION_STRING,
                   'RSS_CHAT_ID': RSS_CHAT_ID,
                   'RSS_COMMAND': RSS_COMMAND,
                   'RSS_DELAY': RSS_DELAY,
                   'SEARCH_API_LINK': SEARCH_API_LINK,
                   'SEARCH_LIMIT': SEARCH_LIMIT,
                   'SEARCH_PLUGINS': SEARCH_PLUGINS,
                   'SERVER_PORT': SERVER_PORT,
                   'STATUS_LIMIT': STATUS_LIMIT,
                   'USER_MAX_TASKS': USER_MAX_TASKS,
                   'DOWNLOAD_STATUS_UPDATE_INTERVAL': DOWNLOAD_STATUS_UPDATE_INTERVAL,
                   'STOP_DUPLICATE': STOP_DUPLICATE,
                   'SUDO_USERS': SUDO_USERS,
                   'TELEGRAM_API': TELEGRAM_API,
                   'TELEGRAM_HASH': TELEGRAM_HASH,
                   'TORRENT_TIMEOUT': TORRENT_TIMEOUT,
                   'UPSTREAM_REPO': UPSTREAM_REPO,
                   'UPSTREAM_BRANCH': UPSTREAM_BRANCH,
                   'UPTOBOX_TOKEN': UPTOBOX_TOKEN,
                   'USER_SESSION_STRING': USER_SESSION_STRING,
                   'USE_SERVICE_ACCOUNTS': USE_SERVICE_ACCOUNTS,
                   'VIEW_LINK': VIEW_LINK,
                   'WEB_PINCODE': WEB_PINCODE,
                   'YT_DLP_QUALITY': YT_DLP_QUALITY,
                   'STORAGE_THRESHOLD': STORAGE_THRESHOLD,
                   'TORRENT_LIMIT': TORRENT_LIMIT,
                   'DIRECT_LIMIT': DIRECT_LIMIT,
                   'YTDLP_LIMIT': YTDLP_LIMIT,
                   'GDRIVE_LIMIT': GDRIVE_LIMIT,
                   'CLONE_LIMIT': CLONE_LIMIT,
                   'MEGA_LIMIT': MEGA_LIMIT,
                   'LEECH_LIMIT': LEECH_LIMIT,
                   'MAX_PLAYLIST': MAX_PLAYLIST,
                   'ENABLE_RATE_LIMIT': ENABLE_RATE_LIMIT,
                   'ENABLE_MESSAGE_FILTER': ENABLE_MESSAGE_FILTER,
                   'STOP_DUPLICATE_TASKS': STOP_DUPLICATE_TASKS,
                   'DISABLE_DRIVE_LINK': DISABLE_DRIVE_LINK,
                   'SET_COMMANDS': SET_COMMANDS,
                   'DISABLE_LEECH': DISABLE_LEECH,
                   'DM_MODE': DM_MODE,
                   'DELETE_LINKS': DELETE_LINKS})

    if DATABASE_URL:
        DbManger().update_config(config_dict)
    initiate_search_tools()
    start_from_queued()

def get_buttons(key=None, edit_type=None):
    buttons = ButtonMaker()
    if key is None:
        if DATABASE_URL:
            buttons.sbutton('Fetch Config', "botset fetch")
        buttons.sbutton('Config Variables', "botset var")
        buttons.sbutton('Private Files', "botset private")
        buttons.sbutton('Qbit Settings', "botset qbit")
        buttons.sbutton('Aria2c Settings', "botset aria")
        buttons.sbutton('Close', "botset close")
        msg = 'Bot Settings:'
    elif key == 'var':
        for k in list(config_dict.keys())[START:10+START]:
            buttons.sbutton(k, f"botset editvar {k}")
        if STATE == 'view':
            buttons.sbutton('Edit', "botset edit var")
        else:
            buttons.sbutton('View', "botset view var")
        buttons.sbutton('Back', "botset back")
        buttons.sbutton('Close', "botset close")
        for x in range(0, len(config_dict)-1, 10):
            buttons.sbutton(int(x/10), f"botset start var {x}", position='footer')
        msg = f'Config Variables | Page: {int(START/10)} | State: {STATE}'
    elif key == 'private':
        buttons.sbutton('Back', "botset back")
        buttons.sbutton('Close', "botset close")
        msg = f'Send private file: config.env, token.pickle, accounts.zip, list_drives.txt, categories.txt, shorteners.txt, buttons.txt, cookies.txt, terabox.txt or .netrc.\nTimeout: 60 sec' \
            '\nTo delete private file send the name of the file only as text message.\nTimeout: 60 sec'
    elif key == 'aria':
        for k in list(aria2_options.keys())[START:10+START]:
            buttons.sbutton(k, f"botset editaria {k}")
        if STATE == 'view':
            buttons.sbutton('Edit', "botset edit aria")
        else:
            buttons.sbutton('View', "botset view aria")
        buttons.sbutton('Add new key', "botset editaria newkey")
        buttons.sbutton('Back', "botset back")
        buttons.sbutton('Close', "botset close")
        for x in range(0, len(aria2_options)-1, 10):
            buttons.sbutton(int(x/10), f"botset start aria {x}", position='footer')
        msg = f'Aria2c Options | Page: {int(START/10)} | State: {STATE}'
    elif key == 'qbit':
        for k in list(qbit_options.keys())[START:10+START]:
            buttons.sbutton(k, f"botset editqbit {k}")
        if STATE == 'view':
            buttons.sbutton('Edit', "botset edit qbit")
        else:
            buttons.sbutton('View', "botset view qbit")
        buttons.sbutton('Back', "botset back")
        buttons.sbutton('Close', "botset close")
        for x in range(0, len(qbit_options)-1, 10):
            buttons.sbutton(int(x/10), f"botset start qbit {x}", position='footer')
        msg = f'Qbittorrent Options | Page: {int(START/10)} | State: {STATE}'
    elif edit_type == 'editvar':
        msg = ''
        buttons.sbutton('Back', "botset back var")
        if key not in ['TELEGRAM_HASH', 'TELEGRAM_API', 'OWNER_ID', 'BOT_TOKEN']:
            buttons.sbutton('Default', f"botset resetvar {key}")
        buttons.sbutton('Close', "botset close")
        if key in ['SUDO_USERS', 'RSS_USER_SESSION_STRING', 'IGNORE_PENDING_REQUESTS', 'CMD_SUFFIX', 'OWNER_ID',
                   'USER_SESSION_STRING', 'TELEGRAM_HASH', 'TELEGRAM_API', 'AUTHORIZED_CHATS', 'RSS_DELAY'
                   'DATABASE_URL', 'BOT_TOKEN', 'DOWNLOAD_DIR']:
            msg += 'Restart required for this edit to take effect!\n\n'
        msg += f'Send a valid value for {key}. Timeout: 60 sec'
    elif edit_type == 'editaria':
        buttons.sbutton('Back', "botset back aria")
        if key != 'newkey':
            buttons.sbutton('Default', f"botset resetaria {key}")
            buttons.sbutton('Empty String', f"botset emptyaria {key}")
        buttons.sbutton('Close', "botset close")
        if key == 'newkey':
            msg = 'Send a key with value. Example: https-proxy-user:value'
        else:
            msg = f'Send a valid value for {key}. Timeout: 60 sec'
    elif edit_type == 'editqbit':
        buttons.sbutton('Back', "botset back qbit")
        buttons.sbutton('Empty String', f"botset emptyqbit {key}")
        buttons.sbutton('Close', "botset close")
        msg = f'Send a valid value for {key}. Timeout: 60 sec'
    button = buttons.build_menu(1) if key is None else buttons.build_menu(2)
    return msg, button

def update_buttons(message, key=None, edit_type=None):
    msg, button = get_buttons(key, edit_type)
    editMessage(msg, message, button)

def edit_variable(update, context, omsg, key):
    handler_dict[omsg.chat.id] = False
    value = update.message.text
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
        if key == 'INCOMPLETE_TASK_NOTIFIER' and DATABASE_URL:
            DbManger().trunc_table('tasks')
        elif key == 'STOP_DUPLICATE_TASKS' and DATABASE_URL:
            DbManger().clear_download_links()
    elif key == 'DOWNLOAD_DIR':
        if not value.endswith('/'):
            value = f'{value}/'
    elif key == 'DOWNLOAD_STATUS_UPDATE_INTERVAL':
        value = int(value)
        if len(download_dict) != 0:
            with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
                    Interval.append(setInterval(value, update_all_messages))
    elif key == 'TORRENT_TIMEOUT':
        value = int(value)
        downloads = aria2.get_downloads()
        for download in downloads:
            if not download.is_complete:
                try:
                    aria2.client.change_option(download.gid, {'bt-stop-timeout': f'{value}'})
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = f'{value}'
    elif key == 'LEECH_SPLIT_SIZE':
        value = min(int(value), MAX_SPLIT_SIZE)
    elif key == 'SERVER_PORT':
        value = int(value)
        run(["pkill", "-9", "-f", "gunicorn"])
        Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{value}", shell=True)
    elif key == 'EXTENSION_FILTER':
        fx = value.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.append('.aria2')
        for x in fx:
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    elif key == 'GDRIVE_ID':
        list_drives['Main'] = {"drive_id": value, "index_link": config_dict['INDEX_URL']}
        list_drives['Root'] = {"drive_id": value, "index_link": config_dict['INDEX_URL']}
    elif key == 'INDEX_URL':
        if GDRIVE_ID:=config_dict['GDRIVE_ID']:
            list_drives['Main'] = {"drive_id": GDRIVE_ID, "index_link": value}
            categories['Root'] = {"drive_id": GDRIVE_ID, "index_link": value}
    elif key == 'DM_MODE':
        value = value.lower() if value.lower() in ['leech', 'mirror', 'all'] else ''
    elif key not in ['SEARCH_LIMIT', 'STATUS_LIMIT'] and key.endswith(('_THRESHOLD', '_LIMIT')):
        value = float(value)
    elif value.isdigit() and key != 'FSUB_IDS':
        value = int(value)
    config_dict[key] = value
    update_buttons(omsg, 'var')
    update.message.delete()
    if DATABASE_URL:
        DbManger().update_config({key: value})
    if key in ['SEARCH_PLUGINS', 'SEARCH_API_LINK']:
        initiate_search_tools()
    elif key in ['QUEUE_ALL', 'QUEUE_DOWNLOAD', 'QUEUE_UPLOAD']:
        start_from_queued()
    elif key == 'SET_COMMANDS':
        set_commands(context.bot)

def edit_aria(update, context, omsg, key):
    handler_dict[omsg.chat.id] = False
    value = update.message.text
    if key == 'newkey':
        key, value = [x.strip() for x in value.split(':', 1)]
    elif value.lower() == 'true':
        value = "true"
    elif value.lower() == 'false':
        value = "false"
    if key in aria2c_global:
        aria2.set_global_options({key: value})
    else:
        downloads = aria2.get_downloads()
        for download in downloads:
            if not download.is_complete:
                try:
                    aria2.client.change_option(download.gid, {key: value})
                except Exception as e:
                    LOGGER.error(e)
    aria2_options[key] = value
    update_buttons(omsg, 'aria')
    update.message.delete()
    if DATABASE_URL:
        DbManger().update_aria2(key, value)

def edit_qbit(update, context, omsg, key):
    handler_dict[omsg.chat.id] = False
    value = update.message.text
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif key == 'max_ratio':
        value = float(value)
    elif value.isdigit():
        value = int(value)
    client = get_client()
    client.app_set_preferences({key: value})
    qbit_options[key] = value
    update_buttons(omsg, 'qbit')
    update.message.delete()
    if DATABASE_URL:
        DbManger().update_qbittorrent(key, value)

def update_private_file(update, context, omsg):
    handler_dict[omsg.chat.id] = False
    message = update.message
    if not message.document and message.text:
        file_name = message.text.strip()
        fn = file_name.rsplit('.zip', 1)[0]
        if path.isfile(fn):
            remove(fn)
        if fn == 'accounts':
            if path.exists('accounts'):
                run(["rm", "-rf", "accounts"])
            config_dict['USE_SERVICE_ACCOUNTS'] = False
            if DATABASE_URL:
                DbManger().update_config({'USE_SERVICE_ACCOUNTS': False})
        elif file_name in ['.netrc', 'netrc']:
            run(["touch", ".netrc"])
            run(["cp", ".netrc", "/root/.netrc"])
            run(["chmod", "600", ".netrc"])
        elif file_name == 'buttons.txt':
            extra_buttons.clear()
        elif file_name == 'categories.txt':
            categories.clear()            
            if GDRIVE_ID:= config_dict['GDRIVE_ID']:
                categories['Root'] = {"drive_id": GDRIVE_ID, "index_link": config_dict['INDEX_URL']}
        elif file_name == 'list_drives.txt':
            list_drives.clear()
            if GDRIVE_ID:= config_dict['GDRIVE_ID']:
                list_drives['Main'] = {"drive_id": GDRIVE_ID, "index_link": config_dict['INDEX_URL']}
        elif file_name == 'shorteners.txt':
            SHORTENERES.clear()
            SHORTENER_APIS.clear()
        message.delete()
    else:
        doc = message.document
        file_name = doc.file_name
        doc.get_file().download(custom_path=file_name)
        if file_name == 'accounts.zip':
            if path.exists('accounts'):
                run(["rm", "-rf", "accounts"])
            run(["unzip", "-q", "-o", "accounts.zip", "-W", "accounts/*.json"])
            run(["chmod", "-R", "777", "accounts"])
        elif file_name == 'list_drives.txt':
            list_drives.clear()
            if GDRIVE_ID:= config_dict['GDRIVE_ID']:
                list_drives['Main'] = {"drive_id": GDRIVE_ID, "index_link": config_dict['INDEX_URL']}
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
                    list_drives[name] = tempdict
        elif file_name == 'categories.txt':
            categories.clear()
            if GDRIVE_ID:= config_dict['GDRIVE_ID']:
                list_drives['Root'] = {"drive_id": GDRIVE_ID, "index_link": config_dict['INDEX_URL']}
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
                    categories[name] = tempdict
        elif file_name == 'shorteners.txt':
            SHORTENERES.clear()
            SHORTENER_APIS.clear()
            with open('shorteners.txt', 'r+') as f:
                lines = f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    if len(temp) == 2:
                        SHORTENERES.append(temp[0])
                        SHORTENER_APIS.append(temp[1])
        elif file_name == 'buttons.txt':
            extra_buttons.clear()
            with open('buttons.txt', 'r+') as f:
                lines = f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    if len(extra_buttons.keys()) == 4:
                        break
                    if len(temp) == 2:
                        extra_buttons[temp[0].replace("_", " ")] = temp[1]
        elif file_name in ['.netrc', 'netrc']:
            if file_name == 'netrc':
                rename('netrc', '.netrc')
                file_name = '.netrc'
            run(["cp", ".netrc", "/root/.netrc"])
            run(["chmod", "600", "/root/.netrc"])
            run(["chmod", "600", ".netrc"])
        elif file_name == 'config.env':
            load_dotenv('config.env', override=True)
            load_config()
        if '@github.com' in config_dict['UPSTREAM_REPO']:
            buttons = ButtonMaker()
            msg = 'Push to UPSTREAM_REPO ?'
            buttons.sbutton('Yes!', f"botset push {file_name}")
            buttons.sbutton('No', "botset close")
            sendMessage(msg, context.bot, message, buttons.build_menu(2))
        else:
            message.delete()
    update_buttons(omsg)
    if DATABASE_URL and file_name != 'config.env':
        DbManger().update_private_file(file_name)
    if path.exists('accounts.zip'):
        remove('accounts.zip')

@new_thread
def edit_bot_settings(update, context):
    query = update.callback_query
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    if not CustomFilters.owner_query(user_id):
        query.answer(text="You don't have premision to use these buttons!", show_alert=True)
    elif data[1] == 'close':
        query.answer()
        handler_dict[message.chat.id] = False
        message.delete()
        message.reply_to_message.delete()
    elif data[1] == 'fetch':
        query.answer()
        handler_dict[message.chat.id] = False
        message.delete()
        message.reply_to_message.delete()
        DbManger().load_configs()
        load_config()
    elif data[1] == 'back':
        query.answer()
        handler_dict[message.chat.id] = False
        key = data[2] if len(data) == 3 else None
        if key is None:
            globals()['START'] = 0
        update_buttons(message, key)
    elif data[1] in ['var', 'aria', 'qbit']:
        query.answer()
        update_buttons(message, data[1])
    elif data[1] == 'resetvar':
        query.answer()
        handler_dict[message.chat.id] = False
        value = ''
        if data[2] in default_values:
            value = default_values[data[2]]
            if data[2] == "DOWNLOAD_STATUS_UPDATE_INTERVAL" and len(download_dict) != 0:
                with status_reply_dict_lock:
                    if Interval:
                        Interval[0].cancel()
                        Interval.clear()
                        Interval.append(setInterval(value, update_all_messages))
        elif data[2] == 'EXTENSION_FILTER':
            GLOBAL_EXTENSION_FILTER.clear()
            GLOBAL_EXTENSION_FILTER.append('.aria2')
        elif data[2] == 'TORRENT_TIMEOUT':
            downloads = aria2.get_downloads()
            for download in downloads:
                if not download.is_complete:
                    try:
                        download.options.bt_stop_timeout = 0
                    except Exception as e:
                        LOGGER.error(e)
            aria2_options['bt-stop-timeout'] = '0'
            if DATABASE_URL:
                DbManger().update_aria2('bt-stop-timeout', '0')
        elif data[2] == 'BASE_URL':
            run(["pkill", "-9", "-f", "gunicorn"])
        elif data[2] == 'SERVER_PORT':
            value = 80
            run(["pkill", "-9", "-f", "gunicorn"])
            Popen("gunicorn web.wserver:app --bind 0.0.0.0:80", shell=True)
        elif data[2] == 'GDRIVE_ID':
            if 'Main' in list_drives:
                del list_drives['Main']
            if 'Root' in categories:
                del categories['Root']
        elif data[2] == 'INDEX_URL':
            if (GDRIVE_ID:= config_dict['GDRIVE_ID']) and 'Main' in list_drives:
                list_drives['Main'] = {"drive_id": GDRIVE_ID, "index_link": ''}
            if (GDRIVE_ID:= config_dict['GDRIVE_ID']) and 'Root' in categories:
                categories['Root'] = {"drive_id": GDRIVE_ID, "index_link": ''}
        elif data[2] == 'INCOMPLETE_TASK_NOTIFIER' and DATABASE_URL:
            DbManger().trunc_table('tasks')
        elif data[2] == 'STOP_DUPLICATE_TASKS' and DATABASE_URL:
            DbManger().clear_download_links()
        config_dict[data[2]] = value
        update_buttons(message, 'var')
        if DATABASE_URL:
            DbManger().update_config({data[2]: value})
        if data[2] in ['SEARCH_PLUGINS', 'SEARCH_API_LINK']:
            initiate_search_tools()
        elif data[2] in ['QUEUE_ALL', 'QUEUE_DOWNLOAD', 'QUEUE_UPLOAD']:
            start_from_queued()
    elif data[1] == 'resetaria':
        handler_dict[message.chat.id] = False
        aria2_defaults = aria2.client.get_global_option()
        if aria2_defaults[data[2]] == aria2_options[data[2]]:
            query.answer(text='Value already same as you added in aria.sh!')
            return
        query.answer()
        value = aria2_defaults[data[2]]
        aria2_options[data[2]] = value
        update_buttons(message, 'aria')
        downloads = aria2.get_downloads()
        for download in downloads:
            if not download.is_complete:
                try:
                    aria2.client.change_option(download.gid, {data[2]: value})
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            DbManger().update_aria2(data[2], value)
    elif data[1] == 'emptyaria':
        query.answer()
        handler_dict[message.chat.id] = False
        aria2_options[data[2]] = ''
        update_buttons(message, 'aria')
        downloads = aria2.get_downloads()
        for download in downloads:
            if not download.is_complete:
                try:
                    aria2.client.change_option(download.gid, {data[2]: ''})
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            DbManger().update_aria2(data[2], '')
    elif data[1] == 'emptyqbit':
        query.answer()
        handler_dict[message.chat.id] = False
        client = get_client()
        client.app_set_preferences({data[2]: value})
        qbit_options[data[2]] = ''
        update_buttons(message, 'qbit')
        if DATABASE_URL:
            DbManger().update_qbittorrent(data[2], '')
    elif data[1] == 'private':
        query.answer()
        if handler_dict.get(message.chat.id):
            handler_dict[message.chat.id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[message.chat.id] = True
        update_buttons(message, 'private')
        partial_fnc = partial(update_private_file, omsg=message)
        file_handler = MessageHandler(filters=(Filters.document | Filters.text) & Filters.chat(message.chat.id) & Filters.user(user_id), callback=partial_fnc)
        dispatcher.add_handler(file_handler)
        while handler_dict[message.chat.id]:
            if time() - start_time > 60:
                handler_dict[message.chat.id] = False
                update_buttons(message)
        dispatcher.remove_handler(file_handler)
    elif data[1] == 'editvar' and STATE == 'edit':
        query.answer()
        if handler_dict.get(message.chat.id):
            handler_dict[message.chat.id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[message.chat.id] = True
        update_buttons(message, data[2], data[1])
        partial_fnc = partial(edit_variable, omsg=message, key=data[2])
        value_handler = MessageHandler(filters=Filters.text & Filters.chat(message.chat.id) & Filters.user(user_id),
                        callback=partial_fnc)
        dispatcher.add_handler(value_handler)
        while handler_dict[message.chat.id]:
            if time() - start_time > 60:
                handler_dict[message.chat.id] = False
                update_buttons(message, 'var')
        dispatcher.remove_handler(value_handler)
    elif data[1] == 'editvar' and STATE == 'view':
        value = config_dict[data[2]]
        if len(str(value)) > 200:
            query.answer()
            fileName = f"{data[2]}.txt"
            sendFile(context.bot, message, value, fileName, data[2])
            return
        elif value and data[2] not in ['SEARCH_LIMIT', 'STATUS_LIMIT'] and data[2].endswith(('_THRESHOLD', '_LIMIT')):
            value = float(value)
            value = get_readable_file_size(value * 1024**3)
        elif not value:
            value = None
        query.answer(text=f'{value}', show_alert=True)
    elif data[1] == 'editaria' and (STATE == 'edit' or data[2] == 'newkey'):
        query.answer()
        if handler_dict.get(message.chat.id):
            handler_dict[message.chat.id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[message.chat.id] = True
        update_buttons(message, data[2], data[1])
        partial_fnc = partial(edit_aria, omsg=message, key=data[2])
        value_handler = MessageHandler(filters=Filters.text & Filters.chat(message.chat.id) & Filters.user(user_id),
                                       callback=partial_fnc)
        dispatcher.add_handler(value_handler)
        while handler_dict[message.chat.id]:
            if time() - start_time > 60:
                handler_dict[message.chat.id] = False
                update_buttons(message, 'aria')
        dispatcher.remove_handler(value_handler)
    elif data[1] == 'editaria' and STATE == 'view':
        value = aria2_options[data[2]]
        if len(value) > 200:
            query.answer()
            filename = f"{data[2]}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f'{value}')
            sendFile(context.bot, message, filename)
            return
        elif value == '':
            value = None
        query.answer(text=f'{value}', show_alert=True)
    elif data[1] == 'editqbit' and STATE == 'edit':
        query.answer()
        if handler_dict.get(message.chat.id):
            handler_dict[message.chat.id] = False
            sleep(0.5)
        start_time = time()
        handler_dict[message.chat.id] = True
        update_buttons(message, data[2], data[1])
        partial_fnc = partial(edit_qbit, omsg=message, key=data[2])
        value_handler = MessageHandler(filters=Filters.text & Filters.chat(message.chat.id) & Filters.user(user_id),
                                       callback=partial_fnc)
        dispatcher.add_handler(value_handler)
        while handler_dict[message.chat.id]:
            if time() - start_time > 60:
                handler_dict[message.chat.id] = False
                update_buttons(message, 'var')
        dispatcher.remove_handler(value_handler)
    elif data[1] == 'editqbit' and STATE == 'view':
        value = qbit_options[data[2]]
        if len(str(value)) > 200:
            query.answer()
            filename = f"{data[2]}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f'{value}')
            sendFile(context.bot, message, filename)
            return
        elif value == '':
            value = None
        query.answer(text=f'{value}', show_alert=True)
    elif data[1] == 'edit':
        query.answer()
        globals()['STATE'] = 'edit'
        update_buttons(message, data[2])
    elif data[1] == 'view':
        query.answer()
        globals()['STATE'] = 'view'
        update_buttons(message, data[2])
    elif data[1] == 'start':
        query.answer()
        if START != int(data[3]):
            globals()['START'] = int(data[3])
            update_buttons(message, data[2])
    elif data[1] == 'push':
        filename = data[2].rsplit('.zip', 1)[0]
        if path.exists(filename):
            run([f"git add -f {filename} \
                    && git commit -sm botsettings -q \
                    && git push origin {config_dict['UPSTREAM_BRANCH']} -q"], shell=True)
        else:
            run([f"git rm -r --cached {filename} \
                    && git commit -sm botsettings -q \
                    && git push origin {config_dict['UPSTREAM_BRANCH']} -q"], shell=True)
        message.delete()
        message.reply_to_message.delete()


def bot_settings(update, context):
    msg, button = get_buttons()
    globals()['START'] = 0
    sendMessage(msg, context.bot, update.message, button)


bot_settings_handler = CommandHandler(BotCommands.BotSetCommand, bot_settings,
                                      filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
bb_set_handler = CallbackQueryHandler(edit_bot_settings, pattern="botset")

dispatcher.add_handler(bot_settings_handler)
dispatcher.add_handler(bb_set_handler)
