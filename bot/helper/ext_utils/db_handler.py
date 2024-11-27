from aiofiles import open as aiopen
from aiofiles.os import (
    path as aiopath,
    makedirs
)
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from pymongo.errors import PyMongoError

from bot import (
    bot_name,
    user_data,
    rss_dict,
    LOGGER,
    BOT_ID,
    config_dict,
    aria2_options,
    qbit_options,
)


class DbManager:
    def __init__(self):
        self._return  = False
        self._db = None
        self._conn = None

    async def connect(self):
        try:
            if config_dict["DATABASE_URL"]:
                if self._conn is not None:
                    await self._conn.close()
                self._conn = AsyncIOMotorClient(
                    config_dict["DATABASE_URL"], server_api=ServerApi("1")
                )
                self._db = self._conn.zee
                self._return = False
            else:
                self._return = True

        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self._return  = True

    async def disconnect(self):
        if self._conn is not None:
            await self._conn.close()
        self._conn = None
        self._return = True

    async def db_load(self):
        if self._db is None:
            await self.connect()
        if self._return :
            return
        # Save bot settings
        try:
            await self._db.settings.config.replace_one( # type: ignore
                {"_id": BOT_ID},
                config_dict,
                upsert=True
            )
        except Exception as e:
            LOGGER.error(f"DataBase Collection Error: {e}")
            return
        # Save Aria2c options
        if await self._db.settings.aria2c.find_one({"_id": BOT_ID}) is None: # type: ignore
            await self._db.settings.aria2c.update_one( # type: ignore
                {"_id": BOT_ID},
                {"$set": aria2_options},
                upsert=True
            )
        # Save qbittorrent options
        if await self._db.settings.qbittorrent.find_one({"_id": BOT_ID}) is None: # type: ignore
            await self.save_qbit_settings()
        # Save nzb config
        if await self._db.settings.nzb.find_one({"_id": BOT_ID}) is None: # type: ignore
            async with aiopen(
                "sabnzbd/SABnzbd.ini",
                "rb+"
            ) as pf:
                nzb_conf = await pf.read()
            await self._db.settings.nzb.update_one( # type: ignore
                {"_id": BOT_ID},
                {"$set": {"SABnzbd__ini": nzb_conf}},
                upsert=True
            )
        # User Data
        if await self._db.users[BOT_ID].find_one(): # type: ignore
            rows = self._db.users[BOT_ID].find({}) # type: ignore
            # return a dict ==> {_id, is_sudo, is_auth, as_doc, thumb, yt_opt, media_group, equal_splits, split_size, rclone, rclone_path, token_pickle, gdrive_id, leech_dest, lperfix, lprefix, excluded_extensions, user_transmission, index_url, default_upload}
            async for row in rows:
                uid = row["_id"]
                del row["_id"]
                thumb_path = f"Thumbnails/{uid}.jpg"
                rclone_config_path = f"rclone/{uid}.conf"
                token_path = f"tokens/{uid}.pickle"
                if row.get("thumb"):
                    if not await aiopath.exists("Thumbnails"):
                        await makedirs("Thumbnails")
                    async with aiopen(
                        thumb_path,
                        "wb+"
                    ) as f:
                        await f.write(row["thumb"])
                    row["thumb"] = thumb_path
                if row.get("rclone_config"):
                    if not await aiopath.exists("rclone"):
                        await makedirs("rclone")
                    async with aiopen(
                        rclone_config_path,
                        "wb+"
                    ) as f:
                        await f.write(row["rclone_config"])
                    row["rclone_config"] = rclone_config_path
                if row.get("token_pickle"):
                    if not await aiopath.exists("tokens"):
                        await makedirs("tokens")
                    async with aiopen(
                        token_path,
                        "wb+"
                    ) as f:
                        await f.write(row["token_pickle"])
                    row["token_pickle"] = token_path
                user_data[uid] = row
        # Rss Data
        if await self._db.rss[BOT_ID].find_one(): # type: ignore
            # return a dict ==> {_id, title: {link, last_feed, last_name, inf, exf, command, paused}
            rows = self._db.rss[BOT_ID].find({}) # type: ignore
            async for row in rows:
                user_id = row["_id"]
                del row["_id"]
                rss_dict[user_id] = row

    async def update_deploy_config(self):
        if self._return :
            return
        current_config = dict(dotenv_values("config.env"))
        await self._db.settings.deployConfig.replace_one( # type: ignore
            {"_id": BOT_ID},
            current_config,
            upsert=True
        )

    async def update_config(self, dict_):
        if self._return :
            return
        await self._db.settings.config.update_one( # type: ignore
            {"_id": BOT_ID},
            {"$set": dict_},
            upsert=True
        )

    async def update_aria2(self, key, value):
        if self._return :
            return
        await self._db.settings.aria2c.update_one( # type: ignore
            {"_id": BOT_ID},
            {"$set": {key: value}},
            upsert=True
        )

    async def update_qbittorrent(self, key, value):
        if self._return :
            return
        await self._db.settings.qbittorrent.update_one( # type: ignore
            {"_id": BOT_ID},
            {"$set": {key: value}},
            upsert=True
        )

    async def save_qbit_settings(self):
        if self._return :
            return
        await self._db.settings.qbittorrent.replace_one( # type: ignore
            {"_id": BOT_ID},
            qbit_options,
            upsert=True
        )

    async def update_private_file(self, path):
        if self._return :
            return
        if await aiopath.exists(path):
            async with aiopen(path, "rb+") as pf:
                pf_bin = await pf.read()
        else:
            pf_bin = ""
        path = path.replace(".", "__")
        await self._db.settings.files.update_one( # type: ignore
            {"_id": BOT_ID},
            {"$set": {path: pf_bin}},
            upsert=True
        )
        if path == "config.env":
            await self.update_deploy_config()

    async def update_nzb_config(self):
        async with aiopen(
            "sabnzbd/SABnzbd.ini",
            "rb+"
        ) as pf:
            nzb_conf = await pf.read()
        await self._db.settings.nzb.replace_one( # type: ignore
            {"_id": BOT_ID},
            {"SABnzbd__ini": nzb_conf},
            upsert=True
        )

    async def update_user_data(self, user_id):
        if self._return :
            return
        data = user_data.get(
            user_id,
            {}
        )
        if data.get("thumb"):
            del data["thumb"]
        if data.get("rclone_config"):
            del data["rclone_config"]
        if data.get("token_pickle"):
            del data["token_pickle"]
        await self._db.users[BOT_ID].replace_one( # type: ignore
            {"_id": user_id},
            data,
            upsert=True
        )

    async def update_user_doc(self, user_id, key, path=""):
        if self._return :
            return
        if path:
            async with aiopen(
                path,
                "rb+"
            ) as doc:
                doc_bin = await doc.read()
        else:
            doc_bin = ""
        await self._db.users[BOT_ID].update_one( # type: ignore
            {"_id": user_id},
            {"$set": {key: doc_bin}},
            upsert=True
        )

    async def rss_update_all(self):
        if self._return :
            return
        for user_id in list(rss_dict.keys()):
            await self._db.rss[BOT_ID].replace_one( # type: ignore
                {"_id": user_id},
                rss_dict[user_id],
                upsert=True
            )

    async def rss_update(self, user_id):
        if self._return :
            return
        await self._db.rss[BOT_ID].replace_one( # type: ignore
            {"_id": user_id},
            rss_dict[user_id],
            upsert=True
        )

    async def rss_delete(self, user_id):
        if self._return :
            return
        await self._db.rss[BOT_ID].delete_one({"_id": user_id}) # type: ignore

    async def add_incomplete_task(self, cid, link, tag):
        if self._return :
            return
        await self._db.tasks[BOT_ID].insert_one( # type: ignore
            {
                "_id": link,
                "cid": cid,
                "tag": tag
            }
        )

    async def rm_complete_task(self, link):
        if self._return :
            return
        await self._db.tasks[BOT_ID].delete_one({"_id": link}) # type: ignore

    async def get_incomplete_tasks(self):
        notifier_dict = {}
        if self._return :
            return notifier_dict
        if await self._db.tasks[BOT_ID].find_one(): # type: ignore
            # return a dict ==> {_id, cid, tag}
            rows = self._db.tasks[BOT_ID].find({}) # type: ignore
            async for row in rows:
                if row["cid"] in list(notifier_dict.keys()):
                    if row["tag"] in list(notifier_dict[row["cid"]]):
                        notifier_dict[row["cid"]][row["tag"]].append(row["_id"])
                    else:
                        notifier_dict[row["cid"]][row["tag"]] = [row["_id"]]
                else:
                    notifier_dict[row["cid"]] = {row["tag"]: [row["_id"]]}
        await self._db.tasks[BOT_ID].drop() # type: ignore
        return notifier_dict  # return a dict ==> {cid: {tag: [_id, _id, ...]}}

    async def trunc_table(self, name):
        if self._return :
            return
        await self._db[name][BOT_ID].drop() # type: ignore

    async def add_download_url(self, url: str, tag: str):
        if self._return :
            return
        suffix = config_dict["CMD_SUFFIX"]
        download = {
            "_id": url,
            "tag": tag,
            "botname": bot_name,
            "suffix": suffix
        }
        await self._db.download_links.update_one( # type: ignore
            {"_id": url},
            {"$set": download},
            upsert=True
        )

    async def check_download(self, url: str):
        if self._return :
            return
        exist = await self._db.download_links.find_one({"_id": url}) # type: ignore
        return exist

    async def clear_download_links(self, botName=None):
        if self._return :
            return
        if not botName:
            botName = bot_name
        await self._db.download_links.delete_many({"botname": botName}) # type: ignore

    async def remove_download(self, url: str):
        if self._return :
            return
        await self._db.download_links.delete_one({"_id": url}) # type: ignore

    async def update_user_tdata(self, user_id, token, time):
        if self._return :
            return
        await self._db.access_token.update_one( # type: ignore
            {"_id": user_id},
            {"$set": {"token": token, "time": time}},
            upsert=True
        )

    async def update_user_token(self, user_id, token, inittime):
        if self._return :
            return
        await self._db.access_token.update_one( # type: ignore
            {"_id": user_id},
            {"$set": {"token": token, "inittime": inittime}},
            upsert=True
        )

    async def get_token_expire_time(self, user_id):
        if self._return :
            return None
        user_data = await self._db.access_token.find_one({"_id": user_id}) # type: ignore
        if user_data:
            return user_data.get("time")
        return None

    async def get_user_token(self, user_id):
        if self._return :
            return None
        user_data = await self._db.access_token.find_one({"_id": user_id}) # type: ignore
        if user_data:
            return user_data.get("token")
        return None

    async def get_token_init_time(self, user_id):
        if self._return :
            return None
        user_data = await self._db.access_token.find_one({"_id": user_id}) # type: ignore
        if user_data:
            return user_data.get("inittime")
        return None

    async def delete_all_access_tokens(self):
        if self._return :
            return
        await self._db.access_token.delete_many({}) # type: ignore


database = DbManager()
