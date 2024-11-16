from aioshutil import rmtree
from shlex import split as ssplit
from aiofiles.os import (
    remove,
    path as aiopath,
    makedirs
)
from asyncio import (
    create_subprocess_exec,
    gather,
    wait_for
)
from asyncio.subprocess import PIPE
from os import (
    cpu_count,
    path as ospath
)
from pathlib import Path
from PIL import Image
from re import (
    escape,
    search as re_search
)
from time import time

from bot import (
    LOGGER,
    DOWNLOAD_DIR,
    subprocess_lock
)
from .bot_utils import (
    cmd_exec,
    sync_to_async
)
from .files_utils import (
    ARCH_EXT, 
    get_mime_type
)
from .links_utils import is_telegram_link
from ..telegram_helper.message_utils import get_tg_link_message


async def convert_video(listener, video_file, ext, retry=False):
    base_name = ospath.splitext(video_file)[0]
    output = f"{base_name}.{ext}"
    if retry:
        cmd = [
            "ffmpeg",
            "-i",
            video_file,
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-threads",
            f"{cpu_count() // 2}", # type: ignore
            output,
        ]
        if ext == "mp4":
            cmd[7:7] = [
                "-c:s",
                "mov_text"
            ]
        elif ext == "mkv":
            cmd[7:7] = [
                "-c:s",
                "ass"
            ]
        else:
            cmd[7:7] = [
                "-c:s",
                "copy"
            ]
    else:
        cmd = [
            "ffmpeg",
            "-i",
            video_file,
            "-map",
            "0",
            "-c",
            "copy",
            output
        ]
    if listener.is_cancelled:
        return False
    async with subprocess_lock:
        listener.suproc = await create_subprocess_exec(
            *cmd,
            stderr=PIPE
        )
    (
        _,
        stderr
    ) = await listener.suproc.communicate()
    if listener.is_cancelled:
        return False
    code = listener.suproc.returncode
    if code == 0:
        return output
    elif code == -9:
        listener.is_cancelled = True
        return False
    else:
        if not retry:
            if await aiopath.exists(output):
                await remove(output)
            return await convert_video(
                listener,
                video_file,
                ext,
                True
            )
        else:
            try:
                stderr = stderr.decode().strip()
            except:
                stderr = "Unable to decode the error!"
            LOGGER.error(
                f"{stderr}. Something went wrong while converting video, mostly file need specific codec. Path: {video_file}"
            )
    return False


async def convert_audio(listener, audio_file, ext):
    base_name = ospath.splitext(audio_file)[0]
    output = f"{base_name}.{ext}"
    cmd = [
        "ffmpeg",
        "-i",
        audio_file,
        "-threads",
        f"{cpu_count() // 2}", # type: ignore
        output,
    ]
    if listener.is_cancelled:
        return False
    async with subprocess_lock:
        listener.suproc = await create_subprocess_exec(
            *cmd,
            stderr=PIPE
        )
    (
        _,
        stderr
    ) = await listener.suproc.communicate()
    if listener.is_cancelled:
        return False
    code = listener.suproc.returncode
    if code == 0:
        return output
    elif code == -9:
        listener.is_cancelled = True
        return False
    else:
        try:
            stderr = stderr.decode().strip()
        except:
            stderr = "Unable to decode the error!"
        LOGGER.error(
            f"{stderr}. Something went wrong while converting audio, mostly file need specific codec. Path: {audio_file}"
        )
        if await aiopath.exists(output):
            await remove(output)
    return False


async def create_thumb(msg, _id=""):
    if not _id:
        _id = msg.id
        path = f"{DOWNLOAD_DIR}Thumbnails"
    else:
        path = "Thumbnails"
    await makedirs(
        path,
        exist_ok=True
    )
    photo_dir = await msg.download()
    output = ospath.join(
        path,
        f"{_id}.jpg"
    )
    await sync_to_async(
        Image.open(
            photo_dir
        ).convert(
            "RGB"
        ).save,
        output,
        "JPEG"
    )
    await remove(photo_dir)
    return output


global_streams = {}
async def is_multi_streams(path):
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                path,
            ]
        )
    except Exception as e:
        LOGGER.error(f"Get Video Streams: {e}. Mostly File not found! - File: {path}")
        return False
    if (
        result[0]
        and result[2] == 0
    ):
        fields = eval(result[0]).get("streams")
        if fields is None:
            return False
        global_streams["stream"] = fields
        videos = 0
        audios = 0
        for stream in fields:
            if stream.get("codec_type") == "video":
                videos += 1
            elif stream.get("codec_type") == "audio":
                audios += 1
        return videos > 1 or audios > 1
    return False


async def get_media_info(path):
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_format",
                path,
            ]
        )
    except Exception as e:
        LOGGER.error(f"Get Media Info: {e}. Mostly File not found! - File: {path}")
        return (
            0,
            None,
            None
        )
    if (
        result[0]
        and result[2] == 0
    ):
        fields = eval(result[0]).get("format")
        if fields is None:
            LOGGER.error(f"get_media_info: {result}")
            return (
                0,
                None,
                None
            )
        duration = round(float(fields.get(
            "duration",
            0
        )))
        tags = fields.get(
            "tags",
            {}
        )
        artist = (
            tags.get("artist") or
            tags.get("ARTIST") or
            tags.get("Artist")
        )
        title = (
            tags.get("title") or
            tags.get("TITLE") or
            tags.get("Title")
        )
        return (
            duration,
            artist,
            title
        )
    return (
        0,
        None,
        None
    )


async def get_document_type(path):
    (
        is_video,
        is_audio,
        is_image
    ) = (
        False,
        False,
        False
    )
    if path.endswith(tuple(ARCH_EXT)) or re_search(
        r".+(\.|_)(rar|7z|zip|bin)(\.0*\d+)?$",
        path
    ):
        return (
            is_video,
            is_audio,
            is_image
        )
    mime_type = await sync_to_async(
        get_mime_type,
        path
    )
    if mime_type.startswith("image"):
        return (
            False,
            False,
            True
        )
    try:
        result = await cmd_exec(
            [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                path,
            ]
        )
        if result[1] and mime_type.startswith("video"):
            is_video = True
    except Exception as e:
        LOGGER.error(f"Get Document Type: {e}. Mostly File not found! - File: {path}")
        if mime_type.startswith("audio"):
            return (
                False,
                True,
                False
            )
        if (
            not mime_type.startswith("video") and
            not mime_type.endswith("octet-stream")
        ):
            return (
                is_video,
                is_audio,
                is_image
            )
        if mime_type.startswith("video"):
            is_video = True
        return (
            is_video,
            is_audio,
            is_image
        )
    if (
        result[0]
        and result[2] == 0
    ):
        fields = eval(result[0]).get("streams")
        if fields is None:
            LOGGER.error(f"get_document_type: {result}")
            return (
                is_video,
                is_audio,
                is_image
            )
        is_video = False
        for stream in fields:
            if stream.get("codec_type") == "video":
                is_video = True
            elif stream.get("codec_type") == "audio":
                is_audio = True
    return (
        is_video,
        is_audio,
        is_image
    )


async def take_ss(video_file, ss_nb) -> bool:
    duration = (await get_media_info(video_file))[0]
    if duration != 0:
        (
            dirpath,
            name
        ) = video_file.rsplit(
            "/",
            1
        )
        (
            name,
            _
        ) = ospath.splitext(name)
        dirpath = f"{dirpath}/{name}_zeess"
        await makedirs(dirpath, exist_ok=True)
        interval = duration // (ss_nb + 1)
        cap_time = interval
        cmds = []
        for i in range(ss_nb):
            output = f"{dirpath}/SS.{name}_{i:02}.png"
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{cap_time}",
                "-i",
                video_file,
                "-q:v",
                "1",
                "-frames:v",
                "1",
                "-threads",
                f"{cpu_count() // 2}", # type: ignore
                output,
            ]
            cap_time += interval
            cmds.append(cmd_exec(cmd))
        try:
            resutls = await wait_for(
                gather(*cmds),
                timeout=60
            )
            if resutls[0][2] != 0:
                LOGGER.error(
                    f"Error while creating sreenshots from video. Path: {video_file}. stderr: {resutls[0][1]}"
                )
                await rmtree(
                    dirpath,
                    ignore_errors=True
                )
                return False
        except:
            LOGGER.error(
                f"Error while creating sreenshots from video. Path: {video_file}. Error: Timeout some issues with ffmpeg with specific arch!"
            )
            await rmtree(
                dirpath,
                ignore_errors=True
            )
            return False
        return dirpath # type: ignore
    else:
        LOGGER.error("take_ss: Can't get the duration of video")
        return False


async def get_audio_thumbnail(audio_file):
    output_dir = f"{DOWNLOAD_DIR}Thumbnails"
    await makedirs(
        output_dir,
        exist_ok=True
    )
    output = ospath.join(
        output_dir,
        f"{time()}.jpg"
    )
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        audio_file,
        "-an",
        "-vcodec",
        "copy",
        "-threads",
        f"{cpu_count() // 2}", # type: ignore
        output,
    ]
    (
        _,
        err,
        code
    ) = await cmd_exec(cmd)
    if code != 0 or not await aiopath.exists(output):
        LOGGER.error(
            f"Error while extracting thumbnail from audio. Name: {audio_file} stderr: {err}"
        )
        return None
    return output


async def get_video_thumbnail(video_file, duration):
    output_dir = f"{DOWNLOAD_DIR}Thumbnails"
    await makedirs(
        output_dir,
        exist_ok=True
    )
    output = ospath.join(
        output_dir,
        f"{time()}.jpg"
    )
    if duration is None:
        duration = (await get_media_info(video_file))[0]
    if duration == 0:
        duration = 3
    duration = duration // 2
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{duration}",
        "-i",
        video_file,
        "-vf",
        "thumbnail",
        "-q:v",
        "1",
        "-frames:v",
        "1",
        "-threads",
        f"{cpu_count() // 2}", # type: ignore
        output,
    ]
    try:
        (
            _,
            err,
            code
        ) = await wait_for(
            cmd_exec(cmd),
            timeout=60
        )
        if (
            code != 0
            or not await aiopath.exists(output)
        ):
            LOGGER.error(
                f"Error while extracting thumbnail from video. Name: {video_file} stderr: {err}"
            )
            return None
    except:
        LOGGER.error(
            f"Error while extracting thumbnail from video. Name: {video_file}. Error: Timeout some issues with ffmpeg with specific arch!"
        )
        return None
    return output


async def get_multiple_frames_thumbnail(video_file, layout, keep_screenshots):
    ss_nb = layout.split("x")
    ss_nb = int(ss_nb[0]) * int(ss_nb[1])
    dirpath = await take_ss(
        video_file,
        ss_nb
    )
    if not dirpath:
        return None
    output_dir = f"{DOWNLOAD_DIR}Thumbnails"
    await makedirs(
        output_dir,
        exist_ok=True
    )
    output = ospath.join(
        output_dir,
        f"{time()}.jpg"
    )
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-pattern_type",
        "glob",
        "-i",
        f"{escape(dirpath)}/*.png", # type: ignore
        "-vf",
        f"tile={layout}, thumbnail",
        "-q:v",
        "1",
        "-frames:v",
        "1",
        "-f",
        "mjpeg",
        "-threads",
        f"{cpu_count() // 2}", # type: ignore
        output,
    ]
    try:
        (
            _,
            err,
            code
        ) = await wait_for(
            cmd_exec(cmd),
            timeout=60
        )
        if code != 0 or not await aiopath.exists(output):
            LOGGER.error(
                f"Error while combining thumbnails for video. Name: {video_file} stderr: {err}"
            )
            return None
    except:
        LOGGER.error(
            f"Error while combining thumbnails from video. Name: {video_file}. Error: Timeout some issues with ffmpeg with specific arch!"
        )
        return None
    finally:
        if not keep_screenshots:
            await rmtree(
                dirpath,
                ignore_errors=True
            )
    return output


async def split_file(
    path,
    size,
    dirpath,
    file_,
    split_size,
    listener,
    start_time=0,
    i=1,
    inLoop=False,
    multi_streams=True,
):
    if (
        listener.seed and not
        listener.new_dir
    ):
        dirpath = f"{dirpath}/splited_files_zee"
        await makedirs(
            dirpath,
            exist_ok=True
        )
    parts = -(-size // listener.split_size)
    if (
        listener.equal_splits
        and not inLoop
    ):
        split_size = (size // parts) + (size % parts)
    if (
        not listener.as_doc
        and (await get_document_type(path))[0]
    ):
        if multi_streams:
            multi_streams = await is_multi_streams(path)
        duration = (await get_media_info(path))[0]
        (
            base_name,
            extension
        ) = ospath.splitext(file_)
        split_size -= 5000000
        while i <= parts or start_time < duration - 4:
            out_path = f"{dirpath}/{base_name}.part{i:03}{extension}"
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(start_time),
                "-i",
                path,
                "-fs",
                str(split_size),
                "-map",
                "0",
                "-map_chapters",
                "-1",
                "-async",
                "1",
                "-strict",
                "-2",
                "-c",
                "copy",
                out_path,
            ]
            if not multi_streams:
                del cmd[10]
                del cmd[10]
            if listener.is_cancelled:
                return False
            async with subprocess_lock:
                listener.suproc = await create_subprocess_exec(
                    *cmd,
                    stderr=PIPE
                )
            (
                _,
                stderr
            ) = await listener.suproc.communicate()
            if listener.is_cancelled:
                return False
            code = listener.suproc.returncode
            if code == -9:
                listener.is_cancelled = True
                return False
            elif code != 0:
                try:
                    stderr = stderr.decode().strip()
                except:
                    stderr = "Unable to decode the error!"
                try:
                    await remove(out_path)
                except:
                    pass
                if multi_streams:
                    LOGGER.warning(
                        f"{stderr}. Retrying without map, -map 0 not working in all situations. Path: {path}"
                    )
                    return await split_file(
                        path,
                        size,
                        dirpath,
                        file_,
                        split_size,
                        listener,
                        start_time,
                        i,
                        True,
                        False,
                    )
                else:
                    LOGGER.warning(
                        f"{stderr}. Unable to split this video, if it's size less than {listener.max_split_size} will be uploaded as it is. Path: {path}"
                    )
                return False
            out_size = await aiopath.getsize(out_path)
            if out_size > listener.max_split_size:
                dif = out_size - listener.max_split_size
                split_size -= dif + 5000000
                await remove(out_path)
                return await split_file(
                    path,
                    size,
                    dirpath,
                    file_,
                    split_size,
                    listener,
                    start_time,
                    i,
                    True,
                    multi_streams,
                )
            lpd = (await get_media_info(out_path))[0]
            if lpd == 0:
                LOGGER.error(
                    f"Something went wrong while splitting, mostly file is corrupted. Path: {path}"
                )
                break
            elif duration == lpd:
                LOGGER.warning(
                    f"This file has been splitted with default stream and audio, so you will only see one part with less size from orginal one because it doesn't have all streams and audios. This happens mostly with MKV videos. Path: {path}"
                )
                break
            elif lpd <= 3:
                await remove(out_path)
                break
            start_time += lpd - 3
            i += 1
    else:
        out_path = f"{dirpath}/{file_}."
        async with subprocess_lock:
            if listener.is_cancelled:
                return False
            listener.suproc = await create_subprocess_exec(
                "split",
                "--numeric-suffixes=1",
                "--suffix-length=3",
                f"--bytes={split_size}",
                path,
                out_path,
                stderr=PIPE,
            )
        (
            _,
            stderr
        ) = await listener.suproc.communicate()
        if listener.is_cancelled:
            return False
        code = listener.suproc.returncode
        if code == -9:
            listener.is_cancelled = True
            return False
        elif code != 0:
            try:
                stderr = stderr.decode().strip()
            except:
                stderr = "Unable to decode the error!"
            LOGGER.error(f"{stderr}. Split Document: {path}")
    return True


async def create_sample_video(listener, video_file, sample_duration, part_duration):
    (
        dir,
        name
    ) = video_file.rsplit(
        "/",
        1
    )
    output_file = f"{dir}/SAMPLE.{name}"
    segments = [(
        0,
        part_duration
    )]
    duration = (await get_media_info(video_file))[0]
    remaining_duration = duration - (part_duration * 2)
    parts = (sample_duration - (part_duration * 2)) // part_duration
    time_interval = remaining_duration // parts
    next_segment = time_interval
    for _ in range(parts):
        segments.append(
            (
                next_segment,
                next_segment + part_duration
            )
        )
        next_segment += time_interval
    segments.append(
        (
            duration - part_duration,
            duration
        )
    )

    filter_complex = ""
    for (
        i,
        (start, end)
    ) in enumerate(segments):
        filter_complex += (
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]; "
        )
        filter_complex += (
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]; "
        )

    for i in range(len(segments)):
        filter_complex += f"[v{i}][a{i}]"

    filter_complex += f"concat=n={len(segments)}:v=1:a=1[vout][aout]"

    cmd = [
        "ffmpeg",
        "-i",
        video_file,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-threads",
        f"{cpu_count() // 2}", # type: ignore
        output_file,
    ]

    if listener.is_cancelled:
        return False
    async with subprocess_lock:
        listener.suproc = await create_subprocess_exec(
            *cmd,
            stderr=PIPE
        )
    (
        _,
        stderr
    ) = await listener.suproc.communicate()
    if listener.is_cancelled:
        return False
    code = listener.suproc.returncode
    if code == -9:
        listener.is_cancelled = True
        return False
    elif code == 0:
        return output_file
    else:
        try:
            stderr = stderr.decode().strip()
        except:
            stderr = "Unable to decode the error!"
        LOGGER.error(
            f"{stderr}. Something went wrong while creating sample video, mostly file is corrupted. Path: {video_file}"
        )
        if await aiopath.exists(output_file):
            await remove(output_file)
        return False


async def get_mediainfo_link(up_path):
    stdout, __, _ = await cmd_exec(ssplit(f'mediainfo "{up_path}"'))
    tc = f"📌 <h4>{ospath.basename(up_path)}</h4><br><br>"
    if len(stdout) != 0:
        tc += parseinfo(stdout)
    link_id = (await telegraph.create_page(title="MediaInfo X", content=tc))["path"]
    return f"https://graph.org/{link_id}"

async def edit_video_metadata(listener, dir):

    data = listener.metadata
    dir_path = Path(dir)

    if not dir_path.suffix.lower().endswith((
        "mkv",
        "mp4"
    )):
        return dir

    file_name = dir_path.name
    work_path = dir_path.with_suffix(".temp.mkv")

    await is_multi_streams(dir)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        dir,
        "-c",
        "copy",
        "-metadata",
        f"title={data}",
        "-threads",
        f"{cpu_count() // 2}", # type: ignore
    ]

    meta_info = [
        "copyright",
        "description",
        "license",
        "LICENSE",
        "author",
        "summary",
        "comment",
        "artist",
        "album",
        "genre",
        "date",
        "creation_time",
        "language",
        "publisher",
        "encoder",
        "SUMMARY",
        "AUTHOR",
        "WEBSITE",
        "COMMENT",
        "ENCODER",
        "FILENAME",
        "MIMETYPE",
        "PURL",
        "ALBUM"
    ]

    for field in meta_info:
        cmd.extend([
            "-metadata",
            f"{field}="
        ])

    audio_index = 0
    subtitle_index = 0
    first_video = False

    if global_streams:
        for stream in global_streams["stream"]:
            stream_index = stream["index"]
            stream_type = stream["codec_type"]

            if stream_type == "video":
                if not first_video:
                    cmd.extend([
                        "-map",
                        f"0:{stream_index}"
                    ])
                    first_video = True
                cmd.extend([
                    f"-metadata:s:v:{stream_index}",
                    f"title={data}"
                ])

            elif stream_type == "audio":
                cmd.extend([
                    "-map",
                    f"0:{stream_index}",
                    f"-metadata:s:a:{audio_index}",
                    f"title={data}"
                ])
                audio_index += 1

            elif stream_type == "subtitle":
                codec_name = stream.get(
                    "codec_name",
                    "unknown"
                )
                if codec_name not in [
                    "webvtt",
                    "unknown"
                ]:
                    cmd.extend([
                        "-map", f"0:{stream_index}",
                        f"-metadata:s:s:{subtitle_index}",
                        f"title={data}"
                    ])
                    subtitle_index += 1
                else:
                    LOGGER.info(f"Skipping unsupported subtitle metadata modification: {codec_name} for stream {stream_index}")

            else:
                cmd.extend([
                    "-map",
                    f"0:{stream_index}"
                ])

    else:
        LOGGER.info("No streams found. Skipping stream metadata modification.")
        return dir

    cmd.append(work_path)
    LOGGER.info(f"Modifying metadata for file: {file_name}")

    try:
        async with subprocess_lock:
            if listener.is_cancelled:
                if work_path.exists():
                    work_path.unlink()
                return
            listener.suproc = await create_subprocess_exec(
                *cmd,
                stderr=PIPE,
                stdout=PIPE
            )
        (
            _,
            stderr
        ) = await listener.suproc.communicate()

        if listener.suproc.returncode != 0:
            if work_path.exists():
                work_path.unlink()
            if listener.is_cancelled:
                return
            err = stderr.decode().strip()
            LOGGER.error(f"Error modifying metadata for file: {file_name} | {err}")
            return dir

        if work_path.exists():
            work_path.replace(dir_path)
            LOGGER.info(f"Metadata modified successfully for file: {file_name}")
        else:
            LOGGER.error(f"Temporary file {work_path} not found. Metadata modification failed.")

    except (
        RuntimeError,
        OSError
    ) as e:
        LOGGER.error(f"Error modifying metadata: {str(e)}")
        if work_path.exists():
            work_path.unlink()
        return dir
    
    finally:
        if work_path.exists():
            work_path.unlink()

    return dir


async def add_attachment(listener, dir):

    MIME_TYPES = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
    }

    data = listener.m_attachment
    dir_path = Path(dir)

    if not dir_path.suffix.lower().endswith((
        "mkv",
        "mp4"
    )):
        return dir

    file_name = dir_path.name
    work_path = dir_path.with_suffix(".temp.mkv")

    if data:
        if is_telegram_link(data):
            msg = (await get_tg_link_message(data))[0] # type: ignore
            data = (
                await create_thumb(msg)
                if msg.photo or msg.document # type: ignore
                else ""
            )

    data_ext = data.split(".")[-1].lower()
    if not (mime_type := MIME_TYPES.get(data_ext)):
        LOGGER.error(f"Unsupported attachment type: {data_ext}")
        return dir

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        dir,
        "-attach",
        data,
        "-metadata:s:t",
        f"mimetype={mime_type}",
        "-c",
        "copy",
        "-map",
        "0",
        work_path
    ]

    try:
        async with subprocess_lock:
            if listener.is_cancelled:
                if work_path.exists():
                    work_path.unlink()
                return
            listener.suproc = await create_subprocess_exec(
                *cmd,
                stderr=PIPE,
                stdout=PIPE
            )
        (
            _,
            _
        ) = await listener.suproc.communicate()

        if listener.suproc.returncode != 0:
            if work_path.exists():
                work_path.unlink()
            if listener.is_cancelled:
                return
            LOGGER.error(f"Error adding photo attachment to file: {file_name}")
            return dir

        if work_path.exists():
            work_path.replace(dir_path)
            LOGGER.info(f"Photo attachment added successfully to file: {file_name}")
        else:
            LOGGER.error(f"Temporary file {work_path} not found. Adding photo attachment failed.")

    except (
        RuntimeError,
        OSError
    ) as e:
        LOGGER.error(f"Error adding photo attachment: {str(e)}")
        if work_path.exists():
            work_path.unlink()
        return dir
    
    finally:
        if work_path.exists():
            work_path.unlink()

    return dir
