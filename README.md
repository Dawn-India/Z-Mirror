This is a Telegram Bot written in Python for mirroring files on the Internet to your Google Drive or Telegram.


## Deploy on Heroku

[![Deploy on Heroku](https://www.herokucdn.com/deploy/button.svg)](https://gitlab.com/Dawn-India/Z-Mirror/-/tree/hr_deploy?ref_type=heads#deploy-to-heroku)

## Deploy on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://gitlab.com/Dawn-India/Z-Mirror/-/tree/hr_deploy?ref_type=heads#deploy-to-railway)


# Available features in this REPO:

### Aria2c

- Select files from Torrent before and while downloading.
- Seed torrents to specific ratio and time.
- Netrc support.
- Direct link authentication for specific link while using the bot (it will work even if only username or password).
- Improve aria.sh.
- Fix all download listener functions and status.
- Edit Global Options while bot running from bot settings.

### Rclone

- Download and Upload using rclone with and without service accounts.
- Ability to choose config, remote and path from list with buttons.
- Ability to set rclone flags for each task or globally from config.
- Rclone.conf for each user.
- Clone server-side.
- Rclone serve for combine remote to use it as index from all remotes.

### qBittorrent

- Qbittorrent support.
- Select files from Torrent before and while downloading.
- Seed torrents to specific ratio and time.
- Edit Global Options while bot running from bot settings.

### Yt-dlp

- Switch from youtube-dl to yt-dlp and fix all conflicts.
- Yt-dlp quality buttons.
- Ability to use specific yt-dlp option for each task.
- Custom default yt-dlp options for each user.
- Fix download progress.
- Embed original thumbnail and add it for leech.
- All supported audio formats.

### TG Download/Upload

- Leech support(Upload to Telegram).
- Splitting.
- Thumbnail for each user.
- Leech filename prefix for each user.
- Set upload as document or as media for each user.
- 4GB file upload with premium account also available in DM feature.
- Upload all files to specific superGroup/channel.
- Leech Split size and equal split size settings for each user.
- Ability to leech splitted file parts in media group. Setting for each user.
- Download using premium account if available.
- Download restricted messages (document or link) by tg private/public/super links.
- Auto remove unwanted filenames.

### Google

- Stop duplicates for all tasks except yt-dlp tasks.
- Download from Google Drive.
- Counting Google Drive files/folders.
- Search in multiple Drive folder/TeamDrive.
- Recursive Search (only with `root` or TeamDrive ID, folder ids will be listed with non-recursive method). Based on [Sreeraj](https://github.com/SVR666) searchX-bot.
- Use Token.pickle if file not found with Service Account, for all Gdrive functions.
- Random Service Account for each task.

### Limits
- Storage threshold limit 
- Leech limit
- Clone limit
- Mega limits
- Torrent limits
- Direct download limits
- Yt-dlp limits
- Google drive limits
- User task limits
- Ratelimiter

### Group Features
- Force subscribe module
- Chat restrictions
- Message filters
- Bot DM support
- Stop duplicate tasks
- Enable/Disable drive links
- Enable/Disable leech function
- Mirror/Clone log chat
- Token system for shortners

### Status

- Clone Status
- Extract Status
- Archive Status
- Split Status
- Seed Status
- Status Pages for unlimited tasks.
- Ability to cancel upload/clone/archive/extract/split.
- Cancel all buttons for choosing specific tasks status to cancel.
- Fix flooding issues.
- Fix overall upload and download speed.

### Database

- Mongo Database support.
- Store bot settings.
- Store user settings including thumbnails and rclone config in database.
- Store private files.
- Store RSS data.
- Store incompleted task messages.

### Torrents Search

- Torrent search support.
- Search on torrents with Torrent Search API.
- Search on torrents with variable plugins using qBittorrent search engine.

### Archives

- Zip instead of tar.
- Using 7-zip tool to extract all supported types.
- Extract rar, zip and 7z within folder or splits with or without password.
- Zip file/folder with or without password.

### RSS

- Rss feed. Based on this repository [rss-chan](https://github.com/hyPnOtICDo0g/rss-chan).
- Filters added.
- Edit any feed while running: pause, resume, edit command and edit filters.
- Rss for each user with tag.
- Sudo settings to control users feeds.
- All functions have been improved using buttons from one command.

### Overall

- Docker image support for linux `amd64, arm64/v8, arm/v7`
- Switch from sync to async.
- SWitch from python-telegram-bot to pyrogram.
- Edit variables and overwrite the private files while bot running.
- Update bot at startup and with restart command using `UPSTREAM_REPO`.
- Improve Telegraph. Based on [Sreeraj](https://github.com/SVR666) loaderX-bot.
- Mirror/Leech/Ytdl/Clone/Count/Del by reply.
- Mirror/Leech/Clone multi links/files with one command.
- Custom name for all links except torrents. For files you should add extension except yt-dlp links.
- Extensions Filter for the files to be uploaded/cloned.
- View Link button. Extra button to open index link in broswer instead of direct download for file.
- Queueing System for all tasks.
- Ability to zip/unzip multi links in same directory. Mostly helpful in unziping tg file parts.
- Bulk download from telegram txt file or text message contains links seperated by new line.
- Join splitted files that have splitted before by split linux pkg.
- Almost all repository functions have been improved and many other details can't mention all of them.
- Many bugs have been fixed.
- Mirror direct download links, Torrent, Mega.nz and Telegram files to Google Drive.
- Copy files from someone's Drive to your Drive.
- Download/Upload progress, Speeds and ETAs.
- Mirror all youtube-dl supported links.
- Docker support.
- Uploading to Team Drive.
- Index Link support.
- Service Account support.
- Delete files from Drive.
- Multiple Trackers support.
- Shell and Executor.
- Add sudo users.
- Extract password protected files.
- Extract these filetypes.
  > ZIP, RAR, TAR, 7z, ISO, WIM, CAB, GZIP, BZIP2, APM, ARJ, CHM, CPIO, CramFS, DEB, DMG, FAT, HFS, LZH, LZMA, LZMA2, MBR, MSI, MSLZ, NSIS, NTFS, RPM, SquashFS, UDF, VHD, XAR, Z, TAR.XZ
- Direct links Supported:
  > mediafire (file/folders), hxfile.co, streamtape.com, streamsb.net, feurl.com, upload.ee, pixeldrain.com, racaty.net, 1fichier.com, 1drv.ms (Only works for file not folder or business account), filelions.com, streamwish.com, send.cm (file/folders), solidfiles.com, linkbox.to (file/folders), shrdsk.me (sharedisk.io), akmfiles.com, wetransfer.com, streamvid.net, gofile.io (file/folders), easyupload.io, mdisk.me (with ytdl), terabox.com (file/folders) (you need to add cookies txt with name) [terabox.txt](https://github.com/ytdl-org/youtube-dl#how-do-i-pass-cookies-to-youtube-dl).


### Extra
- Category wise drive uploads - [Click Here](https://github.com/Dawn-India/Z-Mirror#multi-category-ids) for more info.

# How to deploy?

## Prerequisites

### 1. Installing requirements

- Clone this repo:

```
git clone https://github.com/Dawn-India/Z-Mirror Z-Mirror/ && cd Z-Mirror
```

- For Debian based distros

```
sudo apt install python3 python3-pip
```

Install Docker by following the [Official docker docs](https://docs.docker.com/engine/install/#server).
Or you can use the convenience script: `curl -fsSL https://get.docker.com |  bash`


- For Arch and it's derivatives:

```
sudo pacman -S docker python
```

- Install dependencies for running setup scripts:

```
pip3 install -r requirements-cli.txt
```

------

### 2. Setting up config file

```
cp config_sample.env config.env
```

- Remove the first line saying:

```
_____REMOVE_THIS_LINE_____=True
```

Fill up rest of the fields. Meaning of each field is discussed below. **NOTE**: All values must be filled between quotes, even if it's `Int`, `Bool` or `List`.

**1. Required Fields**

- `BOT_TOKEN`: The Telegram Bot Token that you got from [@BotFather](https://t.me/BotFather). `Str`
- `OWNER_ID`: The Telegram User ID (not username) of the Owner of the bot. `Int`
- `TELEGRAM_API`: This is to authenticate your Telegram account for downloading Telegram files. You can get this from <https://my.telegram.org>. `Int`
- `TELEGRAM_HASH`: This is to authenticate your Telegram account for downloading Telegram files. You can get this from <https://my.telegram.org>. `Str`

**2. Optional Fields**

- `USER_SESSION_STRING`: To download/upload from your telegram account and to send rss. To generate session string use this command `python3 generate_string_session.py` after mounting repo folder for sure. `Str`. **NOTE**: You can't use bot with private message. Use it with superGroup.
- `DATABASE_URL`: Your Mongo Database URL (Connection string). Follow this [Generate Database](https://github.com/Dawn-India/Z-Mirror#generate-database) to generate database. Data will be saved in Database: auth and sudo users, users settings including thumbnails for each user, rss data and incomplete tasks. **NOTE**: You can always edit all settings that saved in database from the official site -> (Browse collections). `Str`
- `DOWNLOAD_DIR`: The path to the local folder where the downloads should be downloaded to. `Str`
- `CMD_SUFFIX`: commands index number. This number will added at the end all commands. `Str`|`Int`
- `AUTHORIZED_CHATS`: Fill user_id and chat_id of groups/users you want to authorize. Separate them by space. `Int`
- `SUDO_USERS`: Fill user_id of users whom you want to give sudo permission. Separate them by space. `Int`
- `DEFAULT_UPLOAD`: Whether `rc` to upload to `RCLONE_PATH` or `gd` to upload to `GDRIVE_ID`. Default is `gd`. Read More [HERE](https://github.com/Dawn-India/Z-Mirror#upload).`Str`
- `STATUS_UPDATE_INTERVAL`: Time in seconds after which the progress/status message will be updated. Recommended `10` seconds at least. `Int`
- `AUTO_DELETE_MESSAGE_DURATION`: Interval of time (in seconds), after which the bot deletes it's message and command message which is expected to be viewed instantly. **NOTE**: Set to `-1` to disable auto message deletion. `Int`
- `STATUS_LIMIT`: Limit the no. of tasks shown in status message with buttons. Default is `8`. **NOTE**: Recommended limit is `4` tasks. `Int`
- `EXTENSION_FILTER`: File extensions that won't upload/clone. Separate them by space. `Str`
- `INCOMPLETE_TASK_NOTIFIER`: Get incomplete task messages after restart. Require database and superGroup. Default is `False`. `Bool`
- `FILELION_API`: Filelion api key to mirror Filelion links. Get it from [Filelion](https://filelions.com/?op=my_account). `str`
- `STREAMWISH_API`: Streamwish api key to mirror Streamwish links. Get it from [Streamwish](https://streamwish.com/?op=my_account). `str`
- `YT_DLP_OPTIONS`: Default yt-dlp options. Check all possible options [HERE](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184) or use this [script](https://graph.org/Script-to-convert-cli-arguments-to-api-options-05-28) to convert cli arguments to api options. Format: key:value|key:value|key:value. Add `^` before integer or float, some numbers must be numeric and some string. `str`
  - Example: "format:bv*+mergeall[vcodec=none]|nocheckcertificate:True"
- `USE_SERVICE_ACCOUNTS`: Whether to use Service Accounts or not, with google-api-python-client. For this to work see [Using Service Accounts](https://github.com/Dawn-India/Z-Mirror#generate-service-accounts-what-is-service-account) section below. Default is `False`. `Bool`

### GDrive Tools

- `GDRIVE_ID`: This is the Folder/TeamDrive ID of the Google Drive OR `root` to which you want to upload all the mirrors using google-api-python-client. `Str`
- `IS_TEAM_DRIVE`: Set `True` if uploading to TeamDrive using google-api-python-client. Default is `False`. `Bool`
- `INDEX_URL`: Refer to <https://gitlab.com/ParveenBhadooOfficial/Google-Drive-Index>. `Str`
- `STOP_DUPLICATE`: Bot will check file/folder name in Drive incase uploading to `GDRIVE_ID`. If it's present in Drive then downloading or cloning will be stopped. (**NOTE**: Item will be checked using name and not hash, so this feature is not perfect yet). Default is `False`. `Bool`

### Rclone

- `RCLONE_PATH`: Default rclone path to which you want to upload all the files/folders using rclone. `Str`
- `RCLONE_FLAGS`: key:value|key|key|key:value . Check here all [RcloneFlags](https://rclone.org/flags/). `Str`
- `RCLONE_SERVE_URL`: Valid URL where the bot is deployed to use rclone serve. Format of URL should be `http://myip`, where `myip` is the IP/Domain(public) of your bot or if you have chosen port other than `80` so write it in this format `http://myip:port` (`http` and not `https`). `Str`
- `RCLONE_SERVE_PORT`: Which is the **RCLONE_SERVE_URL** Port. Default is `8080`. `Int`
- `RCLONE_SERVE_USER`: Username for rclone serve authentication. `Str`
- `RCLONE_SERVE_PASS`: Password for rclone serve authentication. `Str`

### Update

- `UPSTREAM_REPO`: Your github repository link, if your repo is private add `https://username:{githubtoken}@github.com/{username}/{reponame}` format. Get token from [Github settings](https://github.com/settings/tokens). So you can update your bot from filled repository on each restart. `Str`.
  - **NOTE**: Any change in docker or requirements you need to deploy/build again with updated repo to take effect. DON'T delete .gitignore file. For more information read [THIS](https://github.com/Dawn-India/Z-Mirror#upstream-repo-recommended).
- `UPSTREAM_BRANCH`: Upstream branch for update. Default is `master`. `Str`

### Leech

- `LEECH_SPLIT_SIZE`: Size of split in bytes. Default is `2GB`. Default is `4GB` if your account is premium. `Int`
- `AS_DOCUMENT`: Default type of Telegram file upload. Default is `False` mean as media. `Bool`
- `EQUAL_SPLITS`: Split files larger than **LEECH_SPLIT_SIZE** into equal parts size (Not working with zip cmd). Default is `False`. `Bool`
- `MEDIA_GROUP`: View Uploaded splitted file parts in media group. Default is `False`. `Bool`.
- `LEECH_FILENAME_PREFIX`: Add custom word to leeched file name. `Str`
- `DUMP_CHAT_ID`: Chat ID to where leeched files would be uploaded. `Int`. **NOTE**: Only available for superGroup/channel. Add `-100` before channel/superGroup id. In short don't add bot id or your id!
- `LEECH_REMOVE_UNWANTED`: Remove unwanted filenames separated with `|` from leeched files. Example: `mltb|jmdkh|wzml`. `Str`
- `USER_DUMP`: Chat ID to where leeched files would be uploaded. `Int`. **NOTE**: Only available for superGroup/channel. Add bot as `admin` and Add `-100` before channel/superGroup id. In short don't add bot id or your id!

### qBittorrent/Aria2c

- `TORRENT_TIMEOUT`: Timeout of dead torrents downloading with qBittorrent and Aria2c in seconds. `Int`
- `BASE_URL`: Valid BASE URL where the bot is deployed to use torrent web files selection. Format of URL should be `http://myip`, where `myip` is the IP/Domain(public) of your bot or if you have chosen port other than `80` so write it in this format `http://myip:port` (`http` and not `https`). `Str`
- `BASE_URL_PORT`: Which is the **BASE_URL** Port. Default is `80`. `Int`
- `WEB_PINCODE`: Whether to ask for pincode before selecting files from torrent in web or not. Default is `False`. `Bool`.
  - **Qbittorrent NOTE**: If your facing ram issues then set limit for `MaxConnections`, decrease `AsyncIOThreadsCount`, set limit of `DiskWriteCacheSize` to `32` and decrease `MemoryWorkingSetLimit` from qbittorrent.conf or bsetting command.

### RSS

- `RSS_DELAY`: Time in seconds for rss refresh interval. Recommended `900` second at least. Default is `900` in sec. `Int`
- `RSS_CHAT_ID`: Chat ID where rss links will be sent. If you want message to be sent to the channel then add channel id. Add `-100` before channel id. `Int`
  - **RSS NOTES**: `RSS_CHAT_ID` is required, otherwise monitor will not work. You must use `USER_STRING_SESSION` --OR-- *CHANNEL*. If using channel then bot should be added in both channel and group(linked to channel) and `RSS_CHAT_ID` is the channel id, so messages sent by the bot to channel will be forwarded to group. Otherwise with `USER_STRING_SESSION` add group id for `RSS_CHAT_ID`. If `DATABASE_URL` not added you will miss the feeds while bot offline.

### MEGA

- `MEGA_EMAIL`: E-Mail used to sign-in on [mega.io](https://mega.io) for using premium account. `Str`
- `MEGA_PASSWORD`: Password for [mega.io](https://mega.io) account. `Str`

### Queue System

- `QUEUE_ALL`: Number of parallel tasks of downloads and uploads. For example if 20 task added and `QUEUE_ALL` is `8`, then the summation of uploading and downloading tasks are 8 and the rest in queue. `Int`. **NOTE**: if you want to fill `QUEUE_DOWNLOAD` or `QUEUE_UPLOAD`, then `QUEUE_ALL` value must be greater than or equal to the greatest one and less than or equal to summation of `QUEUE_UPLOAD` and `QUEUE_DOWNLOAD`.
- `QUEUE_DOWNLOAD`: Number of all parallel downloading tasks. `Int`
- `QUEUE_UPLOAD`: Number of all parallel uploading tasks. `Int`

### Torrent Search

- `SEARCH_API_LINK`: Search api app link. Get your api from deploying this [repository](https://github.com/Ryuk-me/Torrent-Api-py). `Str`
  - Supported Sites:
    > is dynamic and depend on `http://example.com/api/v1/sites` this endpoint
- `SEARCH_LIMIT`: Search limit for search api, limit for each site and not overall result limit. Default is zero (Default api limit for each site). `Int`
- `SEARCH_PLUGINS`: List of qBittorrent search plugins (github raw links). I have added some plugins, you can remove/add plugins as you want. Main Source: [qBittorrent Search Plugins (Official/Unofficial)](https://github.com/qbittorrent/search-plugins/wiki/Unofficial-search-plugins). `List`

### Limits

- `STORAGE_THRESHOLD`: To leave specific storage free and any download will lead to leave free storage less than this value will be cancelled. Don't add unit, the default unit is `GB`.
- `LEECH_LIMIT`:  To limit the Torrent/Direct/ytdlp leech size. Don't add unit, the default unit is `GB`.
- `CLONE_LIMIT`: To limit the size of Google Drive folder/file which you can clone. Don't add unit, the default unit is `GB`.
- `MEGA_LIMIT`: To limit the size of Mega download. Don't add unit, the default unit is `GB`.
- `TORRENT_LIMIT`: To limit the size of torrent download. Don't add unit, the default unit is `GB`.
- `DIRECT_LIMIT`: To limit the size of direct link download. Don't add unit, the default unit is `GB`.
- `YTDLP_LIMIT`: To limit the size of ytdlp download. Don't add unit, the default unit is `GB`.
- `GDRIVE_LIMIT`: To limit the size of Google Drive folder/file link for leech, Zip, Unzip. Don't add unit, the default unit is `GB`.

### Group Features

- `FSUB_IDS`: Fill chat_id of groups/channel you want to force subscribe. Separate them by space. `Int`
  - it will apply only for member
  - **Note**: Bot should be added in the filled chat_id as admin.
- `USER_MAX_TASKS`: Maximum number of tasks for each group member at a time. `Int`
- `REQUEST_LIMITS`: Maximum number of requests for each group member. `Int`
  - it will not accept any command/callback of user and it will mute that member for 1 minute.
- `ENABLE_MESSAGE_FILTER`: If enabled then bot will not download files with captions or forwarded. `Bool`
- `STOP_DUPLICATE_TASKS`: To enable stop duplicate task across multiple bots. `Bool`
  - **Note**: All bot must have added same database link.
- `DISABLE_DRIVE_LINK`: To disable google drive link button in case you need it. `Bool`
- `TOKEN_TIMEOUT`: Token timeout for each group member in sec. `Int`
  - **Note**: This token system is linked with url shortners, users will have to go through ads to use bot commands (if `shorteners.txt` added, Read more about shortners.txt [Here](https://github.com/Dawn-India/Z-Mirror#multi-shortener) ).

### Extra Features

- `SET_COMMANDS`: To set bot commands automatically on every startup. Default is `False`. `Bool`
  - **Note**: You can set commands manually according to your needs few commands are available [here](#bot-commands-to-be-set-in-botfatherhttpstmebotfather)
- `DISABLE_LEECH`: It will disable leech functionality. Default is `False`. `Bool`
- `DM_MODE`: If then bot will send Mirrored/Leeched files in user's DM. Default is `off`. `Str`
  - **Note**: if value is `mirror` it will send only mirrored files in DM. if value is `leech` so it will send leeched files in DM. if value is `all` it will send Mirrored/Leeched files in DM
- `DELETE_LINKS`: It will delete links on download start. Default is `False`. `Bool`
- `LOG_CHAT_ID`: Fill chat_id of the group/channel. It will send mirror/clone links in the log chat. `Int`
  - **Note**: Bot should be added in the log chat as admin.

------

### 3. Build And Run the Docker Image

Make sure you still mount the app folder and installed the docker from official documentation.

- There are two methods to build and run the docker:
  1. Using official docker commands.
  2. Using docker-compose. (Recommended)

------

#### Build And Run The Docker Image Using Official Docker Commands

- Start Docker daemon (SKIP if already running, mostly you don't need to do this):

```
sudo dockerd
```

- Build Docker image:

```
sudo docker build . -t z_mirror
```

- Run the image:

```
sudo docker run -p 80:80 -p 8080:8080 z_mirror
```

- To stop the running image:

```
sudo docker ps
```

```
sudo docker stop id
```

----

#### Build And Run The Docker Image Using docker-compose

**NOTE**: If you want to use ports other than 80 and 8080 for torrent file selection and rclone serve respectively, change it in [docker-compose.yml](docker-compose.yml) also.

- Install docker compose

```
sudo apt install docker-compose
```

- Build and run Docker image:

```
sudo docker-compose up --build
```

- To stop the running image:

```
sudo docker-compose stop
```

- To run the image:

```
sudo docker-compose start
```

- To get latest log from already running image (after mounting the folder):

```
sudo docker compose up
```

- Tutorial video from Tortoolkit repo for docker-compose and checking ports

<p><a href="https://youtu.be/c8_TU1sPK08"> <img src="https://img.shields.io/badge/See%20Video-black?style=for-the-badge&logo=YouTube" width="160""/></a></p>

------

#### Docker Notes

**IMPORTANT NOTES**:

1. Set `BASE_URL_PORT` and `RCLONE_SERVE_PORT` variables to any port you want to use. Default is `80` and `8080` respectively.
2. You should stop the running image before deleting the container and you should delete the container before the image.
3. To delete the container (this will not affect on the image):

```
sudo docker container prune
```

4. To delete the images:

```
sudo docker image prune -a
```

5. Check the number of processing units of your machine with `nproc` cmd and times it by 4, then edit `AsyncIOThreadsCount` in qBittorrent.conf.

------


# Extras

## Bot commands to be set in [@BotFather](https://t.me/BotFather)

```
mirror - or /m Mirror
qbmirror - or /qbm Mirror torrent using qBittorrent
leech - or /l Leech
qbleech - or /qbl Leech torrent using qBittorrent
clone - Copy file/folder to Drive
count - Count file/folder from Drive
ytdl - or /yt Mirror yt-dlp supported link
ytdlleech - or /ytl Leech through yt-dlp supported link
usetting - User settings
bsettings - Bot settings
status - Get Mirror Status message
sall - Get all bot mirror status
btsel - Select files from torrent
rss - Rss menu
list - Search files in Drive
search - Search for torrents with API
cancel - Cancel a task
cancelall - Cancel all tasks
stats - Bot Usage Stats
s - All bot usage stats
ping - or /p to Ping the Bot
help - All cmds with description
```

------

## Getting Google OAuth API credential file and token.pickle

**NOTES**

- Old authentication changed, now we can't use bot or replit to generate token.pickle. You need OS with a local browser. For example `Termux`.
- Windows users should install python3 and pip. You can find how to install and use them from google or from this [telegraph](https://telegra.ph/Create-Telegram-Mirror-Leech-Bot-by-Deploying-App-with-Heroku-Branch-using-Github-Workflow-12-06) from [Wiszky](https://github.com/vishnoe115) tutorial.
- You can ONLY open the generated link from `generate_drive_token.py` in local browser.

1. Visit the [Google Cloud Console](https://console.developers.google.com/apis/credentials)
2. Go to the OAuth Consent tab, fill it, and save.
3. Go to the Credentials tab and click Create Credentials -> OAuth Client ID
4. Choose Desktop and Create.
5. Publish your OAuth consent screen App to prevent **token.pickle** from expire
6. Use the download button to download your credentials.
7. Move that file to the root of mirrorbot, and rename it to **credentials.json**
8. Visit [Google API page](https://console.developers.google.com/apis/library)
9. Search for Google Drive Api and enable it
10. Finally, run the script to generate **token.pickle** file for Google Drive:

```
pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib
python3 generate_drive_token.py
```

------

## Getting rclone.conf

1. Install rclone from [Official Site](https://rclone.org/install/)
2. Create new remote(s) using `rclone config` command.
3. Copy rclone.conf from .config/rclone/rclone.conf to repo folder

------

## Upload

- `RCLONE_PATH` is like `GDRIVE_ID` a default path for mirror. In additional to those variables `DEFAULT_UPLOAD` to choose the default tool whether it's rclone or google-api-python-client.
- If `DEFAULT_UPLOAD` = 'rc' then you must fill `RCLONE_PATH` with path as default one or with `rcl` to select destination path on each new task.
- If `DEFAULT_UPLOAD` = 'gd' then you must fill `GDRIVE_ID` with folder/TD id.
- rclone.conf can be added before deploy like token.pickle to repo folder root or use bsetting to upload it as private file.
- If rclone.conf uploaded from usetting or added in `rclone/{user_id}.conf` then `RCLONE_PATH` must start with `mrcc:`.
- Whenever you want to write path manually to use user rclone.conf that added from usetting then you must add the `mrcc:` at the beginning.
- So in short, up: has 4 possible values which is: gd(Upload to GDRIVE_ID), rc(Upload to RCLONE_PATH), rcl(Select Rclone Path) and rclone_path(remote:path(owner rclone.conf) or mrcc:remote:path(user rclone.conf))

------

## UPSTREAM REPO (Recommended)

- `UPSTREAM_REPO` variable can be used for edit/add any file in repository.
- You can add private/public repository link to grab/overwrite all files from it.
- You can skip adding the privates files like token.pickle or accounts folder before deploying, simply fill `UPSTREAM_REPO` private one in case you want to grab all files including private files.
- If you added private files while deploying and you have added private `UPSTREAM_REPO` and your private files in this private repository, so your private files will be overwritten from this repository. Also if you are using database for private files, then all files from database will override the private files that added before deploying or from private `UPSTREAM_REPO`.
- If you filled `UPSTREAM_REPO` with the official repository link, then be carefull incase any change in requirements.txt your bot will not start after restart. In this case you need to deploy again with updated code to install the new requirements or simply by changing the `UPSTREAM_REPO` to you fork link with that old updates.
- In case you you filled `UPSTREAM_REPO` with your fork link be carefull also if you fetched the commits from the official repository.
- The changes in your `UPSTREAM_REPO` will take affect only after restart.

------

## Bittorrent Seed

- Using `-d` argument alone will lead to use global options for aria2c or qbittorrent.

### Qbittorrent

- Global options: `GlobalMaxRatio` and `GlobalMaxSeedingMinutes` in qbittorrent.conf, `-1` means no limit, but you can cancel manually.
  - **NOTE**: Don't change `MaxRatioAction`.

### Aria2c

- Global options: `--seed-ratio` (0 means no limit) and `--seed-time` (0 means no seed) in aria.sh.

------

## Using Service Accounts for uploading to avoid user rate limit

>For Service Account to work, you must set `USE_SERVICE_ACCOUNTS` = "True" in config file or environment variables.
>**NOTE**: Using Service Accounts is only recommended while uploading to a Team Drive.

### 1. Generate Service Accounts. [What is Service Account?](https://cloud.google.com/iam/docs/service-accounts)

Let us create only the Service Accounts that we need.

**Warning**: Abuse of this feature is not the aim of this project and we do **NOT** recommend that you make a lot of projects, just one project and 100 SAs allow you plenty of use, its also possible that over abuse might get your projects banned by Google.

>**NOTE**: If you have created SAs in past from this script, you can also just re download the keys by running:

```
python3 gen_sa_accounts.py --download-keys $PROJECTID
```

>**NOTE:** 1 Service Account can upload/copy around 750 GB a day, 1 project can make 100 Service Accounts so you can upload 75 TB a day.

>**NOTE:** All people can copy `2TB/DAY` from each file creator (uploader account), so if you got error `userRateLimitExceeded` that doesn't mean your limit exceeded but file creator limit have been exceeded which is `2TB/DAY`.

#### Two methods to create service accounts

Choose one of these methods

##### 1. Create Service Accounts in existed Project (Recommended Method)

- List your projects ids

```
python3 gen_sa_accounts.py --list-projects
```

- Enable services automatically by this command

```
python3 gen_sa_accounts.py --enable-services $PROJECTID
```

- Create Sevice Accounts to current project

```
python3 gen_sa_accounts.py --create-sas $PROJECTID
```

- Download Sevice Accounts as accounts folder

```
python3 gen_sa_accounts.py --download-keys $PROJECTID
```

##### 2. Create Service Accounts in New Project

```
python3 gen_sa_accounts.py --quick-setup 1 --new-only
```

A folder named accounts will be created which will contain keys for the Service Accounts.

### 2. Add Service Accounts

#### Two methods to add service accounts

Choose one of these methods

##### 1. Add Them To Google Group then to Team Drive (Recommended)

- Mount accounts folder

```
cd accounts
```

- Grab emails form all accounts to emails.txt file that would be created in accounts folder
- `For Windows using PowerShell`

```
$emails = Get-ChildItem .\**.json |Get-Content -Raw |ConvertFrom-Json |Select -ExpandProperty client_email >>emails.txt
```

- `For Linux`

```
grep -oPh '"client_email": "\K[^"]+' *.json > emails.txt
```

- Unmount acounts folder

```
cd ..
```

Then add emails from emails.txt to Google Group, after that add this Google Group to your Shared Drive and promote it to manager and delete email.txt file from accounts folder

##### 2. Add Them To Team Drive Directly

- Run:

```
python3 add_to_team_drive.py -d SharedTeamDriveSrcID
```

------

## Generate Database

1. Go to `https://mongodb.com/` and sign-up.
2. Create Shared Cluster.
3. Press on `Database` under `Deployment` Header, your created cluster will be there.
5. Press on connect, choose `Allow Access From Anywhere` and press on `Add IP Address` without editing the ip, then create user.
6. After creating user press on `Choose a connection`, then press on `Connect your application`. Choose `Driver` **python** and `version` **3.6 or later**.
7. Copy your `connection string` and replace `<password>` with the password of your user, then press close.

------

## Multi Drive List

To use list from multi TD/folder. Run driveid.py in your terminal and follow it. It will generate **list_drives.txt** file or u can simply create `list_drives.txt` file in working directory and fill it, check below format:

```
DriveName folderID/tdID or `root` IndexLink(if available)
DriveName folderID/tdID or `root` IndexLink(if available)
```

Example:

```
TD1 root https://example.dev
TD2 0AO1JDB1t3i5jUk9PVA https://example.dev
```
-----

## Multi Category IDs

![image](https://graph.org/file/d8ed66fcb30116010b252.jpg)

To use upload in categorywise TD/folder. Run driveid.py in your terminal and follow it. It will generate **drive_folder** file than rename it to `categories.txt` or u can simply create
`categories.txt` file in working directory and fill it, check below format:
```
categoryName folderID/tdID IndexLink(if available)
categoryName folderID/tdID IndexLink(if available)
```
Example:
```
Root 0AO1JDB1t3i5jUk9PVA https://example.dev/0:
Movies 1H4w824ZhOt4rs14XPajDja0dAdFp1glI https://example.dev/0:/movies
Series 1H4w434ZhOt4rs14XPajDja0dAdFp1glI https://example.dev/0:/series
```
Now when you use /mirror or /clone cmd, you will see category options. Using that u can upload files categorywise in TD/Folder.

## Multi Shortener

To use multiple shorteners to maintain CPM! it will use random shorteners to generate short links.
you can simply create `shorteners.txt` file in working directory and fill it, check below format:
```
shortener_Domain shortener_Api
```
Example:
```
urlshortx.com 91fc872f9882144c27eecdc22d16f7369766f297
ouo.io LYT0zBn1
```
- Supported URL Shorteners:
>exe.io, gplinks.in, shrinkme.io, urlshortx.com, shortzon.com, bit.ly, shorte.st, linkvertise.com, ouo.io, cutt.ly
-----
### Extra Buttons

- Four buttons are already added, Drive Link, Index Link and View Link, You can add up to four extra buttons if you don't know what are the below entries.
You can simply create `buttons.txt` file in working directory and fill it, check below format:
```
button_name button_url
```
Example:
```
Owner https://telegram.me/z_mirror
Updates https://telegram.me/z_mirror
```
- **Note**: If you want to add space in button name use `_` for add space

-----

## Yt-dlp and Aria2c Authentication Using .netrc File

For using your premium accounts in yt-dlp or for protected Index Links, create .netrc file according to following format:

**Note**: Create .netrc and not netrc, this file will be hidden, so view hidden files to edit it after creation.

Format:

```
machine host login your_username password your_password
```

Example:

```
machine instagram login dawn_in password wtf@69
```

**Instagram Note**: You must login even if you want to download public posts and after first try you must confirm that this was you logged in from different ip(you can confirm from phone app).

**Youtube Note**: For `youtube` authentication use [cookies.txt](https://github.com/ytdl-org/youtube-dl#how-do-i-pass-cookies-to-youtube-dl) file.

Using Aria2c you can also use built in feature from bot with or without username. Here example for index link without username.

```
machine example.workers.dev password index_password
```

Where host is the name of extractor (eg. instagram, Twitch). Multiple accounts of different hosts can be added each separated by a new line.

-----
