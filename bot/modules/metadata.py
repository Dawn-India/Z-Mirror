import json
from uuid import uuid4
from time import sleep, time
from base64 import b64encode
from nekozee import filters
from shutil import disk_usage
from urllib.parse import quote
from pymongo import MongoClient
from shlex import split as ssplit
from asyncio.subprocess import PIPE
from aiofiles import open as aiopen
from urllib3 import disable_warnings
from aiofiles.os import path as aiopath
from cloudscraper import create_scraper
from asyncio import create_subprocess_exec
from nekozee.filters import regex, command
from nekozee.handlers import MessageHandler
from random import choice, random, randrange

from nekozee.types import BotCommand, CallbackQuery
from re import findall as refindall, search as re_search
from subprocess import run as srun, check_output as scheck_output
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from os import remove as osremove, rename as osrename, path as ospath, replace as osreplace, getcwd
from nekozee.errors import PeerIdInvalid, RPCError, UserNotParticipant, FloodWait
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time

from bot import bot, pkg_info, botStartTime, config_dict, task_dict_lock, task_dict, DATABASE_URL, DOWNLOAD_DIR, LOGGER, OWNER_ID, shorteneres_list, user_data
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.files_utils import get_base_name
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.message_utils import get_tg_link_message
from bot.helper.ext_utils.links_utils import is_gdrive_id, is_telegram_link
from bot.helper.ext_utils.bot_utils import cmd_exec, sync_to_async, get_telegraph_list, new_task
from bot.helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.ext_utils.bot_utils import update_user_ldata
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import editMessage


leech_data = {}
bot_name = bot.me.username


async def edit_video_metadata(user_id, file_path):
    if not file_path.lower().endswith(('.mp4', '.mkv')):
        return

    user_dict = user_data.get(user_id, {})
    if user_dict.get("metadatatext", False):
        metadata_text = user_dict["metadatatext"]
    else:
        return

    file_name = ospath.basename(file_path)
    temp_ffile_name = ospath.basename(file_path)
    directory = ospath.dirname(file_path)
    temp_file = f"{file_name}.temp.mkv"
    temp_file_path = ospath.join(directory, temp_file)

    cmd = ['ffprobe', '-hide_banner', '-loglevel', 'error', '-print_format', 'json', '-show_streams', file_path]
    process = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        print(f"Error getting stream info: {stderr.decode().strip()}")
        return

    try:
        streams = json.loads(stdout)['streams']
    except:
        print(f"No streams found in the ffprobe output: {stdout.decode().strip()}")
        return

    cmd = [
        pkg_info["pkgs"][2], '-y', '-i', file_path, '-c', 'copy',
        '-metadata:s:v:0', f'title={metadata_text}',
        '-metadata', f'title={metadata_text}',
        '-metadata', 'copyright=',
        '-metadata', 'description=',
        '-metadata', 'license=',
        '-metadata', 'LICENSE=',
        '-metadata', 'author=',
        '-metadata', 'summary=',
        '-metadata', 'comment=',
        '-metadata', 'artist=',
        '-metadata', 'album=',
        '-metadata', 'genre=',
        '-metadata', 'date=',
        '-metadata', 'creation_time=',
        '-metadata', 'language=',
        '-metadata', 'publisher=',
        '-metadata', 'encoder=',
        '-metadata', 'SUMMARY=',
        '-metadata', 'AUTHOR=',
        '-metadata', 'WEBSITE=',
        '-metadata', 'COMMENT=',
        '-metadata', 'ENCODER=',
        '-metadata', 'FILENAME=',
        '-metadata', 'MIMETYPE=',
        '-metadata', 'PURL=',
        '-metadata', 'ALBUM='
    ]

    audio_index = 0
    subtitle_index = 0
    first_video = False

    for stream in streams:
        stream_index = stream['index']
        stream_type = stream['codec_type']

        if stream_type == 'video':
            if not first_video:
                cmd.extend(['-map', f'0:{stream_index}'])
                first_video = True
            cmd.extend([f'-metadata:s:v:{stream_index}', f'title={metadata_text}'])
        elif stream_type == 'audio':
            cmd.extend(['-map', f'0:{stream_index}', f'-metadata:s:a:{audio_index}', f'title={metadata_text}'])
            audio_index += 1
        elif stream_type == 'subtitle':
            codec_name = stream.get('codec_name', 'unknown')
            if codec_name in ['webvtt', 'unknown']:
                print(f"Skipping unsupported subtitle metadata modification: {codec_name} for stream {stream_index}")
            else:
                cmd.extend(['-map', f'0:{stream_index}', f'-metadata:s:s:{subtitle_index}', f'title={metadata_text}'])
                subtitle_index += 1
        else:
            cmd.extend(['-map', f'0:{stream_index}'])

    cmd.append(temp_file_path)
    process = await create_subprocess_exec(*cmd, stderr=PIPE, stdout=PIPE)
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        err = stderr.decode().strip()
        print(err)
        print(f"Error modifying metadata for file: {file_name}")
        return

    osreplace(temp_file_path, file_path)
    print(f"Metadata modified successfully for file: {file_name}")

async def add_attachment(user_id, file_path):
    if not file_path.lower().endswith(('.mp4', '.mkv')):
        return

    user_dict = user_data.get(user_id, {})
    if user_dict.get("attachmenturl", False):
        attachment_url = user_dict["attachmenturl"]
    else:
        return

    file_name = ospath.basename(file_path)
    temp_ffile_name = ospath.basename(file_path)
    directory = ospath.dirname(file_path)
    temp_file = f"{file_name}.temp.mkv"
    temp_file_path = ospath.join(directory, temp_file)
    
    attachment_ext = attachment_url.split('.')[-1].lower()
    if attachment_ext in ['jpg', 'jpeg']:
        mime_type = 'image/jpeg'
    elif attachment_ext == 'png':
        mime_type = 'image/png'
    else:
        mime_type = 'application/octet-stream'

    cmd = [
        pkg_info["pkgs"][2], '-y', '-i', file_path,
        '-attach', attachment_url,
        '-metadata:s:t', f'mimetype={mime_type}',
        '-c', 'copy', '-map', '0', temp_file_path
    ]

    process = await create_subprocess_exec(*cmd, stderr=PIPE, stdout=PIPE)
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        err = stderr.decode().strip()
        print(err)
        print(f"Error adding photo attachment to file: {file_name}")
        return

    osreplace(temp_file_path, file_path)
    print(f"Photo attachment added successfully to file: {file_name}")
