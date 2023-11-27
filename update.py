from logging import FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info
from os import path as ospath, environ
from subprocess import run as srun
from dotenv import load_dotenv
from pymongo import MongoClient

if ospath.exists('Z_Logs.txt'):
    with open('Z_Logs.txt', 'r+') as f:
        f.truncate(0)

basicConfig(format='%(levelname)s | From %(name)s -> %(module)s line no: %(lineno)d | %(message)s',
                    handlers=[FileHandler('Z_Logs.txt'), StreamHandler()], level=INFO)

load_dotenv('config.env', override=True)

try:
    if bool(environ.get('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

bot_id = BOT_TOKEN.split(':', 1)[0]

DATABASE_URL = environ.get('DATABASE_URL', '')
if len(DATABASE_URL) == 0:
    DATABASE_URL = None

if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.z
    if config_dict := db.settings.config.find_one({'_id': bot_id}):
        environ['UPSTREAM_REPO'] = config_dict['UPSTREAM_REPO']
        environ['UPSTREAM_BRANCH'] = config_dict['UPSTREAM_BRANCH']
    conn.close()

UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
log_info(f'Entered upstream repo: {UPSTREAM_REPO}')
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = 'https://github.com/Dawn-India/Z-Mirror'

UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', '')
log_info(f'Entered upstream branch: {UPSTREAM_BRANCH}')
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = 'main'

if UPSTREAM_REPO:
    if ospath.exists('.git'):
        srun(["rm", "-rf", ".git"])

    update = srun([f"git init -q \
                     && git config --global user.email z-mirror.tg@github.com \
                     && git config --global user.name Z-Mirror \
                     && git add . \
                     && git commit -sm update -q \
                     && git remote add origin {UPSTREAM_REPO} \
                     && git fetch origin -q \
                     && git reset --hard origin/{UPSTREAM_BRANCH} -q"], shell=True)
    log_info('Fetching latest updates...')
    if update.returncode == 0:
        log_info('Successfully updated...')
        log_info('Thanks For Using @Z_Mirror')
    else:
        log_error('Error while getting latest updates.')
        log_error('Check if entered UPSTREAM_REPO is valid or not!')
