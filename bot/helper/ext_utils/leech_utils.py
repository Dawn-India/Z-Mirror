#!/usr/bin/env python3
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from os import path as ospath
from re import search as re_search, sub as re_sub
from time import time

from aiofiles.os import makedirs, path as aiopath, remove as aioremove

from bot import LOGGER, MAX_SPLIT_SIZE, config_dict, user_data, subprocess_lock
from bot.helper.ext_utils.bot_utils import cmd_exec, sync_to_async
from bot.helper.ext_utils.fs_utils import ARCH_EXT, get_mime_type


async def is_multi_streams(path):
    try:
        result = await cmd_exec(["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format",
                                 "json", "-show_streams", path])
        if res := result[1]:
            LOGGER.warning(f"Get Video Streams: {res} - File: {path}")
    except Exception as e:
        LOGGER.error(f"Get Video Streams: {e}. Mostly File not found! - File: {path}")
        return False
    fields = eval(result[0]).get('streams')
    if fields is None:
        LOGGER.error(f"get_video_streams: {result}")
        return False
    videos = 0
    audios = 0
    for stream in fields:
        if stream.get('codec_type') == 'video':
            videos += 1
        elif stream.get('codec_type') == 'audio':
            audios += 1
    return videos > 1 or audios > 1


async def get_media_info(path):
    try:
        result = await cmd_exec(["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format",
                                 "json", "-show_format", path])
        if res := result[1]:
            LOGGER.warning(f"Get Media Info: {res} - File: {path}")
    except Exception as e:
        LOGGER.error(f"Get Media Info: {e}. Mostly File not found! - File: {path}")
        return 0, None, None
    fields = eval(result[0]).get("format")
    if fields is None:
        LOGGER.error(f"get_media_info: {result}")
        return 0, None, None
    duration = round(float(fields.get('duration', 0)))
    tags = fields.get('tags', {})
    artist = tags.get('artist') or tags.get('ARTIST') or tags.get("Artist")
    title = tags.get('title') or tags.get('TITLE') or tags.get("Title")
    return duration, artist, title


async def get_document_type(path):
    is_video, is_audio, is_image = False, False, False
    if path.endswith(tuple(ARCH_EXT)) or re_search(r'.+(\.|_)(rar|7z|zip|bin)(\.0*\d+)?$', path):
        return is_video, is_audio, is_image
    mime_type = await sync_to_async(get_mime_type, path)
    if mime_type.startswith('image'):
        return False, False, True
    if mime_type.startswith('audio'):
        return False, True, False
    if not mime_type.startswith('video') and not mime_type.endswith('octet-stream'):
        return is_video, is_audio, is_image
    try:
        result = await cmd_exec(["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format",
                                 "json", "-show_streams", path])
        if res := result[1]:
            if mime_type.startswith('video'):
                is_video = True
    except Exception as e:
        LOGGER.error(f"Get Document Type: {e}. Mostly File not found! - File: {path}")
        if mime_type.startswith('video'):
            is_video = True
        return is_video, is_audio, is_image
    if result[0] and result[2] == 0:
        fields = eval(result[0]).get('streams')
        if fields is None:
            LOGGER.error(f'get_document_type: {result}')
            return is_video, is_audio, is_image
        is_video = False
        for stream in fields:
            if stream.get('codec_type') == 'video':
                is_video = True
            elif stream.get('codec_type') == 'audio':
                is_audio = True
    return is_video, is_audio, is_image


async def get_audio_thumb(audio_file):
    des_dir = "Thumbnails/"
    await makedirs(des_dir, exist_ok=True)
    des_dir = f"Thumbnails/{time()}.jpg"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error",
           "-i", audio_file, "-an", "-vcodec", "copy", des_dir]
    _, err, code = await cmd_exec(cmd)
    if code != 0 or not await aiopath.exists(des_dir):
        LOGGER.error(f'Error while extracting thumbnail from audio. Name: {audio_file} stderr: {err}')
        return None
    return des_dir


async def take_ss(video_file, duration):
    des_dir = 'Thumbnails'
    await makedirs(des_dir, exist_ok=True)
    des_dir = ospath.join(des_dir, f"{time()}.jpg")
    if duration is None:
        duration = (await get_media_info(video_file))[0]
    if duration == 0:
        duration = 3
    duration = duration // 2
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(duration),
           "-i", video_file, "-vf", "thumbnail", "-frames:v", "1", des_dir]
    _, err, code = await cmd_exec(cmd)
    if code != 0 or not await aiopath.exists(des_dir):
        LOGGER.error( f'Error while extracting thumbnail from video. Name: {video_file} stderr: {err}')
        return None
    return des_dir


async def split_file(path, size, dirpath, split_size, listener, start_time=0, i=1, inLoop=False, multi_streams=True):
    if listener.seed and not listener.newDir:
        dirpath = f"{dirpath}/splited_files_z"
        await makedirs(dirpath, exist_ok=True)
    user_id = listener.message.from_user.id
    user_dict = user_data.get(user_id, {})
    leech_split_size = user_dict.get('split_size') or config_dict['LEECH_SPLIT_SIZE']
    leech_split_size = min(leech_split_size, MAX_SPLIT_SIZE)
    parts = -(-size // leech_split_size)
    if (user_dict.get('equal_splits') or config_dict['EQUAL_SPLITS'] and 'equal_splits' not in user_dict) and not inLoop:
        split_size = (size // parts) + (size % parts)
    if not user_dict.get('as_doc') and (await get_document_type(path))[0]:
        if multi_streams:
            multi_streams = await is_multi_streams(path)
        duration = (await get_media_info(path))[0]
        base_name, extension = ospath.splitext(path)
        split_size -= 5000000
        while i <= parts or start_time < duration - 4:
            out_path = f"{base_name}.part{i:03}{extension}"
            cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(start_time), "-i", path,
                   "-fs", str(split_size), "-map", "0", "-map_chapters", "-1", "-async", "1", "-strict",
                   "-2", "-c", "copy", out_path]
            if not multi_streams:
                del cmd[10]
                del cmd[10]
            async with subprocess_lock:
                if listener.suproc == "cancelled":
                    return False
                listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
            _, stderr = await listener.suproc.communicate()
            code = listener.suproc.returncode
            if code == -9:
                return False
            elif code != 0:
                stderr = stderr.decode().strip()
                try:
                    await aioremove(out_path)
                except:
                    pass
                if multi_streams:
                    LOGGER.warning(f"{stderr}. Retrying without map, -map 0 not working in all situations. Path: {path}")
                    return await split_file(path, size, dirpath, split_size, listener, start_time, i, True, False)
                else:
                    LOGGER.warning(f"{stderr}. Unable to split this video, if it's size less than \
                                   {MAX_SPLIT_SIZE} will be uploaded as it is. Path: {path}")
                return "errored"
            out_size = await aiopath.getsize(out_path)
            if out_size > MAX_SPLIT_SIZE:
                dif = out_size - MAX_SPLIT_SIZE
                split_size -= dif + 5000000
                await aioremove(out_path)
                return await split_file(path, size, dirpath, split_size, listener, start_time, i, True, multi_streams)
            lpd = (await get_media_info(out_path))[0]
            if lpd == 0:
                LOGGER.error(f"Something went wrong while splitting, mostly file is corrupted. Path: {path}")
                break
            elif duration == lpd:
                LOGGER.warning(f"This file has been splitted with default stream and audio, \
                                so you will only see one part with less size from orginal one \
                                because it doesn't have all streams and audios. This happens \
                                mostly with MKV videos. Path: {path}")
                break
            elif lpd <= 3:
                await aioremove(out_path)
                break
            start_time += lpd - 3
            i += 1
    else:
        out_path = f"{path}."
        async with subprocess_lock:
            if listener.suproc == "cancelled":
                return False
            listener.suproc = await create_subprocess_exec("split", "--numeric-suffixes=1", "--suffix-length=3",
                                                          f"--bytes={split_size}", path, out_path, stderr=PIPE)
        _, stderr = await listener.suproc.communicate()
        code = listener.suproc.returncode
        if code == -9:
            return False
        elif code != 0:
            stderr = stderr.decode().strip()
            LOGGER.error(f"{stderr}. Split Document: {path}")
    return True


async def remove_unwanted(file_, lremname):
    if lremname and not lremname.startswith('|'):
        lremname = f"|{lremname}"
    lremname = lremname.replace('\s', ' ')
    div = lremname.split("|")
    zName = ospath.splitext(file_)[0]
    for rep in range(1, len(div)):
        args = div[rep].split(":")
        num_args = len(args)
        if num_args == 3:
            zName = re_sub(args[0], args[1], zName, int(args[2]))
        elif num_args == 2:
            zName = re_sub(args[0], args[1], zName)
        elif num_args == 1:
            zName = re_sub(args[0], '', zName)
    file_ = zName + ospath.splitext(file_)[1]
    LOGGER.info(f"New File Name: {file_}")
    return file_
