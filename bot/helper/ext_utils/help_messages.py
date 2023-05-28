YT_HELP_MESSAGE = """

<b>Send link along with command line:</b>
<code>/{cmd}</code> s <b>LINK</b> n: newname pswd: xx(zip) opt: x:y|x1:y1

<b>By replying to link:</b>
<code>/{cmd}</code> n: newname pswd: xx(zip) opt: x:y|x1:y1

<b>Upload Custom Drive</b>
<code>/{cmd}</code> <b>LINK</b> or by replying to file/link <b>id:</b> <code>drive_folder_link</code> or <code>drive_id</code> <b>index:</b> <code>https://anything.in/0:</code>
drive_id must be folder id and index must be url else it will not accept
This options should be always after n: or pswd:

<b>Quality Buttons:</b>
Incase default quality added from yt-dlp options using format option and you need to select quality for specific link or <b>LINK</b>s with multi links feature.
<code>/cmd</code> s link
This option should be always before n:, pswd: and opt:

<b>Options Example:</b> opt: playliststart:^69|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{{"ffmpeg": ["-threads", "4"]}}|wait_for_video:(5, 100)

<b>Multi links only by replying to first link:</b>
<code>/{cmd}</code> 69(number of links)
Number should be always before n:, pswd: and opt:

<b>Multi links within same upload directory only by replying to first link:</b>
<code>/{cmd}</code> 69(number of links) m:folder_name
Number and m:folder_name should be always before n:, pswd: and opt:

<b>Options Note:</b> Add `^` before integer, some values must be integer and some string.
Like playlist_items:69 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict.

<b>Rclone Upload</b>:
<code>/{cmd}</code> <b>LINK</b> up: <code>rcl</code> (To select config, remote and path)
You can directly add the upload path. up: remote:dir/subdir
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
If you want to add path manually from your config (uploaded from usetting) add <code>mrcc:</code> before the path without space
<code>/{cmd}</code> <b>LINK</b> up: <code>mrcc:</code>main:dump

<b>Rclone Flags</b>:
<code>/{cmd}</code> <b>LINK</b> up: path|rcl rcf: --buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.

<b>Bulk Download</b>:
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file). Options that came after link should be added along with and after link and not with cmd.

Example:
<code>/cmd</code> b
<b>LINK</b> n: newname up: remote1:path1
<b>LINK</b> pswd: pass(zip/unzip) opt: ytdlpoptions up: remote2:path2
Reply to this example by this cmd for example <code>/cmd</code> b(bulk) m:folder_name(same dir)
You can set start and end of the links from the bulk with b:start:end or only end by b::end or only start by b:start. The default start is from zero(first link) to inf.

<b>NOTES:</b>
1. When use cmd by reply don't add any option in link msg! Always add them after cmd msg!
2. Options (<b>b, s, m: and multi</b>) should be added randomly before link and before any other option.
3. Options (<b>n:, pswd: and opt:</b>) should be added randomly after the link if link along with the cmd or after cmd if by reply.
4. You can always add video quality from yt-dlp api options.
5. Don't add file extension while rename using `n:`

Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://graph.org/Script-to-convert-cli-arguments-to-api-options-05-28'>SCRIPT</a> to convert cli arguments to api options.

<b>Powered By @Z_Mirror</b>
"""

MIRROR_HELP_MESSAGE = """

<b><i>Mirror:</i></b> <code>/{cmd}</code> <b>LINK</b>
<i>Or reply to the link/file with:</i> <code>/{cmd}</code>

<b><i>Rename:</i></b> <code>/{cmd}</code> <b>LINK</b> <code>n:</code> <b>New_Name</b>
<i>Or reply to the link/file with:</i> <code>/{cmd}</code> <code>n:</code> <b>New_Name</b>

<b><i><u>Upload Custom Drive</u></i></b>
<code>/{cmd} <b>LINK</b> </code> or by replying to file/link <b>id:</b> <code>drive_folder_link</code> or <code>drive_id</code> <b>index:</b> <code>https://anything.in/0:</code>

drive_id must be folder id and index must be url else it will not accept
This options should be always after n: or pswd:

<b><i><u>Direct link authorization</u></i></b>
<code>/{cmd}</code> <b>LINK</b> n: newname pswd: xx(zip/unzip)
<b>username</b>
<b>password</b>

<b><i>Torrent select:</i></b> <code>/{cmd}</code> <b>s</b> <b>LINK</b>
<i>Or reply to the file/link with</i> <code>/{cmd}</code> <b>s</b>
This option should be always before <b>n: or pswd: </b>

<b>Torrent seed</b>: <code>/{cmd}</code> <b>d</b> <b>LINK</b> 
<i>Or reply to the file/link with</i> <code>/{cmd}</code> <b>d</b>

To specify ratio and seed time add d:ratio:time. Ex: d:0.7:69 (ratio and time) or d:0.7 (only ratio) or d::69 (only time) where time in minutes.
Those options should be always before n: or pswd:

<b>Multi mirror:</b> (Reply to the first link or file)
<code>/{cmd}</code> <b>5</b>(*Here '5' is the number of links/files)
Number should be always before n: or pswd:

<b>Same DIR:</b> (Download multiple links or files or unzip in a single folder)
<code>/{cmd}</code> <b>5</b>(*Here '5' is the number of links/files) <b>m:</b>folder_name
Number and <code>m:folder_name</code> (<b>folder_name without space</b>) should be always before <b>n: or pswd: </b>

<b>Rclone Download</b>: (Use rclone paths same as links)
<code>/{cmd}</code> <b>main:dump/ubuntu.iso</b> or <code>rcl</code> (To select config, remote and path)

Users can add their own rclone config from user settings.
If you want to add path manually from your config then add <code>mrcc:</code> before the path without <b>space</b>.
<code>/{cmd}</code> <code>mrcc:</code>main:/dump/ubuntu.iso

<b><i><u>Download using TG Links</u></i></b>
Some links need user access so sure you must add USER_SESSION_STRING for it.
<code>/{cmd}</code> tg_link

Three types of TG links:
<b>Public:</b> <code>https://t.me/channel_name/message_id</code>
<b>Private:</b> <code>tg://openmessage?user_id=xxxxxx&message_id=xxxxx</code>
<b>Super:</b> <code>https://t.me/c/channel_id/message_id</code>

<b><i><u>Rclone Upload</u></i></b>
<code>/{cmd}</code> <b>LINK</b> <b>up: </b><code>rcl</code> (To select rclone config, remote and path)

You can directly add the upload path: <code>up: remote:dir/subdir</code>
If <code>DEFAULT_UPLOAD</code> is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If <code>DEFAULT_UPLOAD</code> is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
If you want to add path manually from your config (uploaded from usetting) add <code>mrcc:</code> before the path without space.
<code>/{cmd}</code> <b>LINK</b> <b>up: </b><code>mrcc:</code>main:dump

<b><i><u>Rclone Flags</u></i></b>
<code>/{cmd}</code> <b>LINK</b> path/rcl up: path/rcl rcf: --buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.

<b><i><u>Bulk Download</u></i></b>
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file). Options that came after link should be added along with and after link and not with cmd.

<b>Example:</b> Reply with <code>/{cmd}</code> <b>b</b>
<b>LINK</b> n: newname up: remote1:path1
<b>LINK</b> pswd: pass(zip/unzip) up: remote2:path2 \\n{{username}}\\n{{password}}(authentication)(last option)
Reply to this example by this cmd for example <code>/cmd</code> b(bulk) d:2:10(seed) m:folder_name(same dir)
You can set start and end of the links from the bulk with b:start:end or only end by b::end or only start by b:start. The default start is from zero(first link) to inf.

<b>NOTES:</b>
1. When use cmd by reply don't add any option in link msg! Always add them after cmd msg!
2. Options (<b>n: and pswd:</b>) should be added randomly after the link if link along with the cmd and after any other option
3. Options (<b>d, s, m:, b and multi</b>) should be added randomly before the link and before any other option.
4. Commands that start with <b>qb</b> are ONLY for torrents.
5. (n:) option doesn't work with torrents.

<b>Powered By @Z_Mirror</b>
"""


RSS_HELP_MESSAGE = """

Use this format to add feed url:
Title1 <b>LINK</b> (required)
Title2 <b>LINK</b> c: cmd inf: xx exf: xx opt: options like(up, rcf, pswd) (optional)
Title3 <b>LINK</b> c: cmd d:ratio:time opt: up: gd

c: command + any mirror option before <b>LINK</b> like seed option.
opt: any option after <b>LINK</b> like up, rcf and pswd(zip).
inf: For included words filter.
exf: For excluded words filter.

Example: Title https://www.rss-url.com inf: 1080 or 720 or 144p|mkv or mp4|hevc exf: flv or web|xxx opt: up: mrcc:remote:path/subdir rcf: --buffer-size:8M|key|key:value
This filter will parse links that it's titles contains `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and doesn't conyain (flv or web) and xxx` words. You can add whatever you want.

Another example: inf:  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contains ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080 to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without spaces after it.

Filter Notes:
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add filter like this f: 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web)."
3. You can add `or` and `|` as much as you want."
4. Take look on title if it has static special character after or before the qualities or extensions or whatever and use them in filter to avoid wrong match.
Timeout: 60 sec.

<b>Powered By @Z_Mirror</b>
"""

CLONE_HELP_MESSAGE = """

Send Gdrive, Gdtot, Filepress, Filebee, Appdrive, Gdflix link or rclone path along with command or by replying to the link/rc_path by command

<b>Multi links only by replying to first gdlink or rclone_path:</b>
<code>/{cmd}</code> 69(number of links/pathies)
<b>Gdrive:</b>
<code>/{cmd}</code> gdrivelink

<b>Upload Custom Drive</b>
<code>/{cmd}</code> <b>LINK</b> or by replying to <b>LINK</b> <b>id:</b> <code>drive_folder_link</code> or <code>drive_id</code> <b>index:</b> <code>https://anything.in/0:</code>
drive_id must be folder id and index must be url else it will not accept

<b>Rclone:</b>
<code>/{cmd}</code> rcl or rclone_path up: rcl or rclone_path rcf: flagkey:flagvalue|flagkey|flagkey:flagvalue
Notes:
if up: not specified then rclone destination will be the RCLONE_PATH from config.env

<b>Powered By @Z_Mirror</b>
"""

CAT_SEL_HELP_MESSAGE = """

Reply to an active /{cmd} which was used to start the download or add gid along with /{cmd}
This command mainly for change category incase you decided to change category from already added download.
But you can always use /{mir} with to select category before download start.

<b>Upload Custom Drive</b>
<code>/{cmd}</code> <b>id:</b><code>drive_folder_link</code> or <code>drive_id</code> <b>index:</b><code>https://anything.in/0:</code> gid or by replying to active download
drive_id must be folder id and index must be url else it will not accept

<b>Powered By @Z_Mirror</b>
"""

TOR_SEL_HELP_MESSAGE = """

Reply to an active <code>/{cmd}</code> which was used to start the qb-download or add gid along with cmd\n\n
This command mainly for selection incase you decided to select files from already added torrent.
But you can always use <code>/{mir}</code> with arg `s` to select files before download start.

<b>Powered By @Z_Mirror</b>
"""