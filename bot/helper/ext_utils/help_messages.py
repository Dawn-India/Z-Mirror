mirror = """
<b>Send link along with command line</b>:

/cmd link

<b>By replying to link/file</b>:

/cmd -n new name -e -up upload destination

<b>NOTE:</b>
1. Commands that start with <b>qb</b> are ONLY for torrents.
"""

yt = """
<b>Send link along with command line</b>:

/cmd link

<b>By replying to link</b>:

/cmd -n new name -z password -opt x:y|x1:y1

Check all supported <a href='https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md'>SITES</a>
Check all yt-dlp API options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert CLI arguments to API options.
"""

clone = """
Send Gdrive link or rclone path along with command or by replying to the link/rc_path by command.

Use -sync to use sync method in rclone.

Example: /cmd rcl/rclone_path -up rcl/rclone_path/rc -sync
"""

new_name = """
<b>Rename</b>: -n

/cmd link -n new_name
Note: Doesn't work with torrents
"""

multi_link = """
<b>Multi links only by replying to the first link/file</b>: -m

/cmd -m 10(number of links/files)
"""

same_dir = """
<b>Move file(s)/folder(s) to new folder</b>: -sd

You can use this arg also to move multiple links/torrents contents to the same directory, so all links will be uploaded together as one task

/cmd link -sd new folder (only one link inside new folder)
/cmd -m 10(number of links/files) -sd folder name (all links contents in one folder)
/cmd -b -sd folder name (reply to batch of message/file(each link on new line))

While using bulk you can also use this arg with different folder name along with the links in message or file batch
Example:
link1 -sd folder1
link2 -sd folder1
link3 -sd folder2
link4 -sd folder2
link5 -sd folder3
link6

so link1 and link2 content will be uploaded from same folder which is folder1
link3 and link4 content will be uploaded from same folder also which is folder2
link5 will uploaded alone inside new folder named folder3
link6 will get uploaded normally alone
"""

thumb = """
<b>Thumbnail for the current task</b>: -t

/cmd link -t tg-message-link(doc or photo)
"""

split_size = """
<b>Split size for the current task</b>: -sp

/cmd link -sp (500mb or 2gb or 4000000000)
Note: Only mb and gb are supported or write in bytes without unit!
"""

upload = """
<b>Upload Destination</b>: -up

/cmd link -up rcl/gdl (To select rclone config/token.pickle, remote & path/ gdrive id or Tg id/username)
You can directly add the upload path: -up remote:dir/subdir or -up (Gdrive_id) or -up id/username
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.

If you want to add path or gdrive manually from your config/token (uploaded from usetting) add mrcc: for rclone and mtp: before the path/gdrive_id without space.
/cmd link -up mrcc:main:dump or -up mtp:gdrive_id or -up b:id/@username/pm(leech by bot) or -up u:id/@username(leech by user) or -up m:id/@username(mixed leech)

In case you want to specify whether using token.pickle or service accounts you can add tp:gdrive_id or sa:gdrive_id or mtp:gdrive_id.
DEFAULT_UPLOAD has no effect on leech cmds.
"""

user_download = """
<b>User Download</b>: link

/cmd tp:link to download using owner token.pickle in case service account enabled.
/cmd sa:link to download using service account in case service account disabled.
/cmd tp:gdrive_id to download using token.pickle and file_id in case service account enabled.
/cmd sa:gdrive_id to download using service account and file_id in case service account disabled.
/cmd mtp:gdrive_id or mtp:link to download using user token.pickle uploaded from usetting
/cmd mrcc:remote:path to download using user rclone config uploaded from usetting
"""

rcf = """
<b>Rclone Flags</b>: -rcf

/cmd link|path|rcl -up path|rcl -rcf --buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude.
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.
"""

bulk = """
<b>Bulk Download</b>: -b

Bulk can be used only by replying to text message or text file contains links separated by new line.

Example:
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -e -n new name -up remote2:path2

Reply to this example by this cmd -> /cmd -b(bulk)

Note: Any arg along with the cmd will be setted to all links
/cmd -b -up remote: -z -sd folder name (all links contents in one zipped folder uploaded to one destination)
so you can't set different upload destinations along with link incase you have added -sd along with cmd
You can set start and end of the links from the bulk like seed, with -b start:end or only end by -b :end or only start by -b start.
The default start is from zero(first link) to inf."""

rlone_dl = """
<b>Rclone Download</b>:

Treat rclone paths exactly like links
/cmd main:dump/ubuntu.iso or rcl(To select config, remote, and path)
Users can add their own rclone from user settings
If you want to add a path manually from your config add mrcc: before the path without space
/cmd mrcc:main:dump/ubuntu.iso
"""

extract_zip = """
<b>Extract/Zip</b>: -e -z

/cmd link -e (extract)
/cmd link -e password (extract password protected)

/cmd link -z password -e (extract and zip password protected)
Note: When both extract and zip are added with cmd, it will extract first and then zip, so always extract first.
"""

join = """
<b>Join Splitted Files</b>: -j

This option will only work before extract and zip, so mostly it will be used with -sd argument (samedir)
By Reply:
/cmd -m 3 -j -sd folder name
/cmd -b -j -sd folder name
If you have a link(folder) that has split files:
/cmd link -j
"""

tg_links = """
<b>TG Links</b>:

Treat links like any direct link
Some links need user access so make sure you have added USER_SESSION_STRING for it.
Three types of links:
Public: https://t.me/channel_name/message_id
Private: tg://openmessage?user_id=xxxxxx&message_id=xxxxx
Super: https://t.me/c/channel_id/message_id
Range: https://t.me/channel_name/first_message_id-last_message_id
Range Example: tg://openmessage?user_id=xxxxxx&message_id=555-560 or https://t.me/channel_name/100-150
Note: Range link will work only by replying cmd to it.
"""

sample_video = """
<b>Sample Video</b>: -sv

Create a sample video for one video or a folder of videos.
/cmd -sv (it will take the default values which are 60sec sample duration and part duration is 4sec).
You can control those values. Example: /cmd -sv 70:5(sample-duration:part-duration) or /cmd -sv :5 or /cmd -sv 70.
"""

screenshot = """
<b>Screenshots</b>: -ss

Create screenshots for one video or folder of videos.
/cmd -ss (it will take the default values which is 10 photos).
You can control this value. Example: /cmd -ss 6.
"""

seed = """
<b>Bittorrent Seed</b>: -d

/cmd link -d ratio:seed_time or by replying to file/link
To specify ratio and seed time add -d ratio:time.
Example: -d 0.7:10 (ratio and time) or -d 0.7 (only ratio) or -d :10 (only time) where time is in minutes.
"""

zip_arg = """
<b>Zip</b>: -z password

/cmd link -z (zip)
/cmd link -z password (zip password protected)

/cmd link -z password -e (extract and zip password protected)
Note: When both extract and zip are added with cmd, it will extract first and then zip, so always extract first.
"""

qual = """
<b>Quality Buttons</b>: -s

In case default quality is added from yt-dlp options using format option and you need to select quality for specific link or links with multi links feature.
/cmd link -s
"""

yt_opt = """
<b>Options</b>: -opt

/cmd link -opt playliststart:^10|fragment_retries:^inf|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{"ffmpeg": ["-threads", "4"]}|wait_for_video:(5, 100)|download_ranges:[{"start_time": 0, "end_time": 10}]

Note: Add `^` before integer or float, some values must be numeric and some string.
Like playlist_items:10 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict.
"""

convert_media = """
<b>Convert Media</b>: -ca -cv

/cmd link -ca mp3 -cv mp4 (convert all audios to mp3 and all videos to mp4)
/cmd link -ca mp3 (convert all audios to mp3)
/cmd link -cv mp4 (convert all videos to mp4)
/cmd link -ca mp3 + flac ogg (convert only flac and ogg audios to mp3)
/cmd link -cv mp4 - webm flv (convert all videos to mp4 except webm and flv)
"""

force_start = """
<b>Force Start</b>: -f -fd -fu

/cmd link -f (force download and upload)
/cmd link -fd (force download only)
/cmd link -fu (force upload directly after download finishes)
"""

gdrive = """
<b>Gdrive</b>: link
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.

/cmd gdriveLink or gdl or gdriveId -up gdl or gdriveId or gd
/cmd tp:gdriveLink or tp:gdriveId -up tp:gdriveId or gdl or gd (to use token.pickle if service account enabled)
/cmd sa:gdriveLink or sa:gdriveId -p sa:gdriveId or gdl or gd (to use service account if service account disabled)
/cmd mtp:gdriveLink or mtp:gdriveId -up mtp:gdriveId or gdl or gd(if you have added upload gdriveId from usetting) (to use user token.pickle that uploaded by usetting)
"""

rclone_cl = """
<b>Rclone</b>: path
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.

/cmd rcl/rclone_path -up rcl/rclone_path/rc -rcf flagkey:flagvalue|flagkey|flagkey:flagvalue
/cmd rcl or rclonePath -up rclonePath or rc or rcl
/cmd mrcc:rclonePath -up rcl or rc(if you have added rclone path from usetting) (to use user config)
"""

name_sub = r"""
<b>Name Substitution</b>: -ns

<b>Name Substitution</b>: -ns
/cmd link -ns script/code/s | mirror/leech | tea/ /s | clone | cpu/ | \[ZEE\]/ZEE | \\text\\/text/s
This will affect on all files. Format: wordToReplace/wordToReplaceWith/sensitiveCase
Word Subtitions. You can add pattern instead of normal text. Timeout: 60 sec
NOTE: You must add \ before any character, those are the characters: \^$.|?*+()[]{}-
1. script will get replaced by code with sensitive case
2. mirror will get replaced by leech
4. tea will get replaced by space with sensitive case
5. clone will get removed
6. cpu will get replaced by space
7. [ZEE] will get replaced by ZEE
8. \text\ will get replaced by text with sensitive case
"""

mixed_leech = """
<b>Mixed Leech</b>: -ml

/cmd link -ml (leech by user and bot session with respect to size)
"""

thumbnail_layout = """
<b>Thumbnail Layout</b>: -tl

/cmd link -tl 3x3 (widthxheight) 3 photos in row and 3 photos in column
"""

leech_as = """
<b>Leech as</b>: -doc -med

/cmd link -doc (Leech as document)
/cmd link -med (Leech as media)
"""

metadata = """
<b>Metadata</b>: -md
/cmd link -md text
It will add text in your video metadata. (MKV & MP4 supports only)


<b>Metadata Attachment</b>: -mda
/cmd link -mda tg-message-link(doc or photo) or any direct link
It will embed thumb in your video. (MKV & MP4 supports only)
"""

YT_HELP_DICT = {
    "main": yt,
    "ʀᴇɴᴀᴍᴇ\nꜰɪʟᴇ": f"{new_name}\nNote: Don't add file extension",
    "ᴢɪᴘ\nꜰɪʟᴇꜱ": zip_arg,
    "Qᴜᴀʟɪᴛʏ\nᴏᴘᴛ": qual,
    "ʏᴛ\nᴏᴘᴛɪᴏɴꜱ": yt_opt,
    "ᴍᴜʟᴛɪ\nʟɪɴᴋ": multi_link,
    "ꜱᴀᴍᴇ\nᴅɪʀᴇᴄᴛᴏʀʏ": same_dir,
    "ᴀᴅᴅ\nᴛʜᴜᴍʙ": thumb,
    "ꜱᴘʟɪᴛ\nꜱɪᴢᴇ": split_size,
    "ᴜᴘʟᴏᴀᴅ\nᴅᴇꜱᴛɪɴᴀᴛɪᴏɴ": upload,
    "ʀᴄʟᴏɴᴇ\nꜰʟᴀɢꜱ": rcf,
    "ʙᴜʟᴋ\nʟɪɴᴋꜱ": bulk,
    "ꜱᴀᴍᴘʟᴇ\nᴠɪᴅᴇᴏ": sample_video,
    "ꜱᴄʀᴇᴇɴ\nꜱʜᴏᴛ": screenshot,
    "ᴄᴏɴᴠᴇʀᴛ\nᴍᴇᴅɪᴀ": convert_media,
    "ꜰᴏʀᴄᴇ\nꜱᴛᴀʀᴛ": force_start,
    "ɴᴀᴍᴇ\nꜱᴜʙꜱᴛɪᴛᴜᴛᴇ": name_sub,
    "ʜʏʙʀɪᴅ\nʟᴇᴇᴄʜ": mixed_leech,
    "ᴛʜᴜᴍʙ\nʟᴀʏᴏᴜᴛ": thumbnail_layout,
    "ʟᴇᴇᴄʜ\nᴛʏᴘᴇ": leech_as,
    "ᴍᴇᴛᴀᴅᴀᴛᴀ\nᴀᴛᴛᴀᴄʜ": metadata,
}

MIRROR_HELP_DICT = {
    "main": mirror,
    "ʀᴇɴᴀᴍᴇ\nꜰɪʟᴇ": new_name,
    "ᴅᴏᴡɴʟᴏᴀᴅ\nᴀᴜᴛʜ": "<b>Direct link authorization</b>: -au -ap\n\n/cmd link -au username -ap password",
    "ᴅᴅʟ\nʜᴇᴀᴅᴇʀꜱ": "<b>Direct link custom headers</b>: -h\n\n/cmd link -h key: value key1: value1",
    "ᴇxᴛʀᴀᴄᴛ\nᴢɪᴘ": extract_zip,
    "ꜱᴇʟᴇᴄᴛ\nꜰɪʟᴇꜱ": "<b>Bittorrent/JDownloader/Sabnzbd File Selection</b>: -s\n\n/cmd link -s or by replying to file/link",
    "ᴛᴏʀʀᴇɴᴛ\nꜱᴇᴇᴅ": seed,
    "ᴍᴜʟᴛɪ\nʟɪɴᴋ": multi_link,
    "ꜱᴀᴍᴇ\nᴅɪʀᴇᴄᴛᴏʀʏ": same_dir,
    "ᴀᴅᴅ\nᴛʜᴜᴍʙ": thumb,
    "ꜱᴘʟɪᴛ\nꜱɪᴢᴇ": split_size,
    "ᴜᴘʟᴏᴀᴅ\nᴅᴇꜱᴛɪɴᴀᴛɪᴏɴ": upload,
    "ʀᴄʟᴏɴᴇ\nꜰʟᴀɢꜱ": rcf,
    "ʙᴜʟᴋ\nʟɪɴᴋꜱ": bulk,
    "ᴊᴏɪɴ\nꜰɪʟᴇꜱ": join,
    "ʀᴄʟᴏɴᴇ\nᴅʟ": rlone_dl,
    "ᴛᴇʟᴇɢʀᴀᴍ\nʟɪɴᴋꜱ": tg_links,
    "ꜱᴀᴍᴘʟᴇ\nᴠɪᴅᴇᴏ": sample_video,
    "ꜱᴄʀᴇᴇɴ\nꜱʜᴏᴛ": screenshot,
    "ᴄᴏɴᴠᴇʀᴛ\nᴍᴇᴅɪᴀ": convert_media,
    "ꜰᴏʀᴄᴇ\nꜱᴛᴀʀᴛ": force_start,
    "ᴜꜱᴇʀ\nᴅᴏᴡɴʟᴏᴀᴅ": user_download,
    "ɴᴀᴍᴇ\nꜱᴜʙꜱᴛɪᴛᴜᴛᴇ": name_sub,
    "ʜʏʙʀɪᴅ\nʟᴇᴇᴄʜ": mixed_leech,
    "ᴛʜᴜᴍʙ\nʟᴀʏᴏᴜᴛ": thumbnail_layout,
    "ʟᴇᴇᴄʜ\nᴛʏᴘᴇ": leech_as,
    "ᴍᴇᴛᴀᴅᴀᴛᴀ\nᴀᴛᴛᴀᴄʜ": metadata,
}

CLONE_HELP_DICT = {
    "main": clone,
    "ᴍᴜʟᴛɪ\nʟɪɴᴋ": multi_link,
    "ʙᴜʟᴋ\nʟɪɴᴋꜱ": bulk,
    "ɢᴏᴏɢʟᴇ\nᴅʀɪᴠᴇ": gdrive,
    "ʀᴄʟᴏɴᴇ\nᴅʟ": rclone_cl,
}

RSS_HELP_MESSAGE = """
Use this format to add feed url:
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

-c command -up mrcc:remote:path/subdir -rcf --buffer-size:8M|key|key:value
-inf For included words filter.
-exf For excluded words filter.
-stv true or false (sensitive filter)

Example: Title https://www.rss-url.com -inf 1080 or 720 or 144p|mkv or mp4|hevc -exf flv or web|xxx
This filter will parse links that its titles contain `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and don't contain (flv or web) and xxx words. You can add whatever you want.

Another example: -inf  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contain (1080 or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080 to avoid wrong matching. If this `10805695` number in the title it will match 1080 if added 1080 without spaces after it.

Filter Notes:
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add a filter like this f: 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web).
3. You can add `or` and `|` as much as you want.
4. Take a look at the title if it has a static special character after or before the qualities or extensions or whatever and use them in the filter to avoid wrong match.
Timeout: 60 sec.
"""

PASSWORD_ERROR_MESSAGE = """
<b>Links require a password!</b>

- Insert <b>::</b> after the link and write the password after the sign.

<b>Example:</b> link::my password
"""
