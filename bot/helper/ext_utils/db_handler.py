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
    DATABASE_URL,
    user_data,
    rss_dict,
    LOGGER,
    bot_id,
    config_dict,
    aria2_options,
    qbit_options,
)


class DbManager:
    def __init__(self):
        self._err = False
        self._db = None
        self._conn = None
        self._connect()

    def _connect(self):
        try:
            self._conn = AsyncIOMotorClient(
                DATABASE_URL,
                server_api=ServerApi("1")
            )
            self._db = self._conn.zee
        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self._err = True

    async def db_load(self):
        if self._err:
            return
        # Save bot settings
        try:
            await self._db.settings.config.replace_one( # type: ignore
                {"_id": bot_id},
                config_dict,
                upsert=True
            )
        except Exception as e:
            LOGGER.error(f"DataBase Collection Error: {e}")
            self._conn.close # type: ignore
            return
        # Save Aria2c options
        if await self._db.settings.aria2c.find_one({"_id": bot_id}) is None: # type: ignore
            await self._db.settings.aria2c.update_one( # type: ignore
                {"_id": bot_id},
                {"$set": aria2_options},
                upsert=True
            )
        # Save qbittorrent options
        if await self._db.settings.qbittorrent.find_one({"_id": bot_id}) is None: # type: ignore
            await self.save_qbit_settings()
        # Save nzb config
        if await self._db.settings.nzb.find_one({"_id": bot_id}) is None: # type: ignore
            async with aiopen(
                "sabnzbd/SABnzbd.ini",
                "rb+"
            ) as pf:
                nzb_conf = await pf.read()
            await self._db.settings.nzb.update_one( # type: ignore
                {"_id": bot_id},
                {"$set": {"SABnzbd__ini": nzb_conf}},
                upsert=True
            )
        # User Data
        if await self._db.users.find_one(): # type: ignore
            rows = self._db.users.find({}) # type: ignore
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
        if await self._db.rss[bot_id].find_one(): # type: ignore
            # return a dict ==> {_id, title: {link, last_feed, last_name, inf, exf, command, paused}
            rows = self._db.rss[bot_id].find({}) # type: ignore
            async for row in rows:
                user_id = row["_id"]
                del row["_id"]
                rss_dict[user_id] = row
        self._conn.close # type: ignore

    async def update_deploy_config(self):
        if self._err:
            return
        current_config = dict(dotenv_values("config.env"))
        await self._db.settings.deployConfig.replace_one( # type: ignore
            {"_id": bot_id},
            current_config,
            upsert=True
        )
        self._conn.close # type: ignore

    async def update_config(self, dict_):
        if self._err:
            return
        await self._db.settings.config.update_one( # type: ignore
            {"_id": bot_id},
            {"$set": dict_},
            upsert=True
        )
        self._conn.close # type: ignore

    async def update_aria2(self, key, value):
        if self._err:
            return
        await self._db.settings.aria2c.update_one( # type: ignore
            {"_id": bot_id},
            {"$set": {key: value}},
            upsert=True
        )
        self._conn.close # type: ignore

    async def update_qbittorrent(self, key, value):
        if self._err:
            return
        await self._db.settings.qbittorrent.update_one( # type: ignore
            {"_id": bot_id},
            {"$set": {key: value}},
            upsert=True
        )
        self._conn.close # type: ignore

    async def save_qbit_settings(self):
        if self._err:
            return
        await self._db.settings.qbittorrent.replace_one( # type: ignore
            {"_id": bot_id},
            qbit_options,
            upsert=True
        )
        self._conn.close # type: ignore

    async def update_private_file(self, path):
        if self._err:
            return
        if await aiopath.exists(path):
            async with aiopen(path, "rb+") as pf:
                pf_bin = await pf.read()
        else:
            pf_bin = ""
        path = path.replace(".", "__")
        await self._db.settings.files.update_one( # type: ignore
            {"_id": bot_id},
            {"$set": {path: pf_bin}},
            upsert=True
        )
        if path == "config.env":
            await self.update_deploy_config()
        else:
            self._conn.close # type: ignore

    async def update_nzb_config(self):
        async with aiopen(
            "sabnzbd/SABnzbd.ini",
            "rb+"
        ) as pf:
            nzb_conf = await pf.read()
        await self._db.settings.nzb.replace_one( # type: ignore
            {"_id": bot_id},
            {"SABnzbd__ini": nzb_conf},
            upsert=True
        )

    async def update_user_data(self, user_id):
        if self._err:
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
        await self._db.users.replace_one( # type: ignore
            {"_id": user_id},
            data,
            upsert=True
        )
        self._conn.close # type: ignore

    async def update_user_doc(self, user_id, key, path=""):
        if self._err:
            return
        if path:
            async with aiopen(
                path,
                "rb+"
            ) as doc:
                doc_bin = await doc.read()
        else:
            doc_bin = ""
        await self._db.users.update_one( # type: ignore
            {"_id": user_id},
            {"$set": {key: doc_bin}},
            upsert=True
        )
        self._conn.close # type: ignore

    async def rss_update_all(self):
        if self._err:
            return
        for user_id in list(rss_dict.keys()):
            await self._db.rss[bot_id].replace_one( # type: ignore
                {"_id": user_id},
                rss_dict[user_id],
                upsert=True
            )
        self._conn.close # type: ignore

    async def rss_update(self, user_id):
        if self._err:
            return
        await self._db.rss[bot_id].replace_one( # type: ignore
            {"_id": user_id},
            rss_dict[user_id],
            upsert=True
        )
        self._conn.close # type: ignore

    async def rss_delete(self, user_id):
        if self._err:
            return
        await self._db.rss[bot_id].delete_one({"_id": user_id}) # type: ignore
        self._conn.close # type: ignore

    async def add_incomplete_task(self, cid, link, tag):
        if self._err:
            return
        await self._db.tasks[bot_id].insert_one( # type: ignore
            {
                "_id": link,
                "cid": cid,
                "tag": tag
            }
        )
        self._conn.close # type: ignore

    async def rm_complete_task(self, link):
        if self._err:
            return
        await self._db.tasks[bot_id].delete_one({"_id": link}) # type: ignore
        self._conn.close # type: ignore

    async def get_incomplete_tasks(self):
        notifier_dict = {}
        if self._err:
            return notifier_dict
        if await self._db.tasks[bot_id].find_one(): # type: ignore
            # return a dict ==> {_id, cid, tag}
            rows = self._db.tasks[bot_id].find({}) # type: ignore
            async for row in rows:
                if row["cid"] in list(notifier_dict.keys()):
                    if row["tag"] in list(notifier_dict[row["cid"]]):
                        notifier_dict[row["cid"]][row["tag"]].append(row["_id"])
                    else:
                        notifier_dict[row["cid"]][row["tag"]] = [row["_id"]]
                else:
                    notifier_dict[row["cid"]] = {row["tag"]: [row["_id"]]}
        await self._db.tasks[bot_id].drop() # type: ignore
        self._conn.close # type: ignore
        return notifier_dict  # return a dict ==> {cid: {tag: [_id, _id, ...]}}

    async def trunc_table(self, name):
        if self._err:
            return
        await self._db[name][bot_id].drop() # type: ignore
        self._conn.close # type: ignore

    async def add_download_url(self, url: str, tag: str):
        if self._err:
            return
        download = {
            "_id": url,
            "tag": tag,
            "botname": bot_name
        }
        await self._db.download_links.update_one( # type: ignore
            {"_id": url},
            {"$set": download},
            upsert=True
        )
        self._conn.close # type: ignore

    async def check_download(self, url: str):
        if self._err:
            return
        exist = await self._db.download_links.find_one({"_id": url}) # type: ignore
        self._conn.close # type: ignore
        return exist

    async def clear_download_links(self, botName=None):
        if self._err:
            return
        if not botName:
            botName = bot_name
        await self._db.download_links.delete_many({"botname": botName}) # type: ignore
        self._conn.close # type: ignore

    async def remove_download(self, url: str):
        if self._err:
            return
        await self._db.download_links.delete_one({"_id": url}) # type: ignore
        self._conn.close # type: ignore

    async def update_user_tdata(self, user_id, token, time):
        if self._err:
            return
        await self._db.access_token.update_one( # type: ignore
            {"_id": user_id},
            {"$set": {"token": token, "time": time}},
            upsert=True
        )
        self._conn.close # type: ignore

    async def update_user_token(self, user_id, token):
        if self._err:
            return
        await self._db.access_token.update_one( # type: ignore
            {"_id": user_id},
            {"$set": {"token": token}},
            upsert=True
        )
        self._conn.close # type: ignore

    async def get_token_expire_time(self, user_id):
        if self._err:
            return None
        user_data = await self._db.access_token.find_one({"_id": user_id}) # type: ignore
        if user_data:
            return user_data.get("time")
        self._conn.close # type: ignore
        return None

    async def get_user_token(self, user_id):
        if self._err:
            return None
        user_data = await self._db.access_token.find_one({"_id": user_id}) # type: ignore
        if user_data:
            return user_data.get("token")
        self._conn.close # type: ignore
        return None

    async def delete_all_access_tokens(self):
        if self._err:
            return
        await self._db.access_token.delete_many({}) # type: ignore
        self._conn.close # type: ignore