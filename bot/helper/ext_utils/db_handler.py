from os import environ, makedirs
from os import path as ospath

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from bot import (DATABASE_URL, LOGGER, aria2_options, bot_id, botname,
                 config_dict, qbit_options, rss_dict, user_data)


class DbManger:
    def __init__(self):
        self.__err = False
        self.__db = None
        self.__conn = None
        self.__connect()

    def __connect(self):
        try:
            self.__conn = MongoClient(DATABASE_URL)
            self.__db = self.__conn.z
        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self.__err = True

    def db_load(self):
        if self.__err:
            return
        # Save bot settings
        self.__db.settings.config.update_one({'_id': bot_id}, {'$set': config_dict}, upsert=True)
        # Save Aria2c options
        if self.__db.settings.aria2c.find_one({'_id': bot_id}) is None:
            self.__db.settings.aria2c.update_one({'_id': bot_id}, {'$set': aria2_options}, upsert=True)
        # Save qbittorrent options
        if self.__db.settings.qbittorrent.find_one({'_id': bot_id}) is None:
            self.__db.settings.qbittorrent.update_one({'_id': bot_id}, {'$set': qbit_options}, upsert=True)
        # User Data
        if self.__db.users[bot_id].find_one():
            rows = self.__db.users[bot_id].find({})
            # return a dict ==> {_id, is_sudo, is_auth, as_doc, thumb, yt_ql, media_group, equal_splits, split_size}
            for row in rows:
                uid = row['_id']
                del row['_id']
                path = f"Thumbnails/{uid}.jpg"
                if row.get('thumb'):
                    if not ospath.exists('Thumbnails'):
                        makedirs('Thumbnails')
                    with open(path, 'wb+') as f:
                        f.write(row['thumb'])
                    row['thumb'] = path
                user_data[uid] = row
            LOGGER.info("Users data has been imported from Database")
        # Rss Data
        if self.__db.rss[bot_id].find_one():
            rows = self.__db.rss[bot_id].find({})  # return a dict ==> {_id, link, last_feed, last_name, filters}
            for row in rows:
                title = row['_id']
                del row['_id']
                rss_dict[title] = row
            LOGGER.info("Rss data has been imported from Database.")
        self.__conn.close()

    def update_config(self, dict_):
        if self.__err:
            return
        self.__db.settings.config.update_one({'_id': bot_id}, {'$set': dict_}, upsert=True)
        self.__conn.close()

    def load_configs(self):
        if self.__err:
            return
        if db_dict := self.__db.settings.config.find_one({'_id': bot_id}):
            del db_dict['_id']
            for key, value in db_dict.items():
                environ[key] = str(value)
        if pf_dict := self.__db.settings.files.find_one({'_id': bot_id}):
            del pf_dict['_id']
            for key, value in pf_dict.items():
                if value:
                    file_ = key.replace('__', '.')
                    with open(file_, 'wb+') as f:
                        f.write(value)

    def update_aria2(self, key, value):
        if self.__err:
            return
        self.__db.settings.aria2c.update_one({'_id': bot_id}, {'$set': {key: value}}, upsert=True)
        self.__conn.close()

    def update_qbittorrent(self, key, value):
        if self.__err:
            return
        self.__db.settings.qbittorrent.update_one({'_id': bot_id}, {'$set': {key: value}}, upsert=True)
        self.__conn.close()

    def update_private_file(self, path):
        if self.__err:
            return
        if ospath.exists(path):
            with open(path, 'rb+') as pf:
                pf_bin = pf.read()
        else:
            pf_bin = ''
        path = path.replace('.', '__')
        self.__db.settings.files.update_one({'_id': bot_id}, {'$set': {path: pf_bin}}, upsert=True)
        self.__conn.close()

    def update_user_data(self, user_id):
        if self.__err:
            return
        data = user_data[user_id]
        if data.get('thumb'):
            del data['thumb']
        self.__db.users[bot_id].update_one({'_id': user_id}, {'$set': data}, upsert=True)
        self.__conn.close()

    def update_thumb(self, user_id, path=None):
        if self.__err:
            return
        if path:
            with open(path, 'rb+') as image:
                image_bin = image.read()
        else:
            image_bin = ''
        self.__db.users[bot_id].update_one({'_id': user_id}, {'$set': {'thumb': image_bin}}, upsert=True)
        self.__conn.close()

    def rss_update(self, title):
        if self.__err:
            return
        self.__db.rss[bot_id].update_one({'_id': title}, {'$set': rss_dict[title]}, upsert=True)
        self.__conn.close()

    def rss_delete(self, title):
        if self.__err:
            return
        self.__db.rss[bot_id].delete_one({'_id': title})
        self.__conn.close()

    def add_incomplete_task(self, cid, link, tag):
        if self.__err:
            return
        self.__db.tasks[bot_id].insert_one({'_id': link, 'cid': cid, 'tag': tag})
        self.__conn.close()

    def rm_complete_task(self, link):
        if self.__err:
            return
        self.__db.tasks[bot_id].delete_one({'_id': link})
        self.__conn.close()

    def get_incomplete_tasks(self):
        notifier_dict = {}
        if self.__err:
            return notifier_dict
        if self.__db.tasks[bot_id].find_one():
            rows = self.__db.tasks[bot_id].find({})  # return a dict ==> {_id, cid, tag}
            for row in rows:
                if row['cid'] in list(notifier_dict.keys()):
                    if row['tag'] in list(notifier_dict[row['cid']]):
                        notifier_dict[row['cid']][row['tag']].append(row['_id'])
                    else:
                        notifier_dict[row['cid']][row['tag']] = [row['_id']]
                else:
                    usr_dict = {row['tag']: [row['_id']]}
                    notifier_dict[row['cid']] = usr_dict
        self.__db.tasks[bot_id].drop()
        self.__conn.close()
        return notifier_dict # return a dict ==> {cid: {tag: [_id, _id, ...]}}

    def trunc_table(self, name):
        if self.__err:
            return
        self.__db[name][bot_id].drop()
        self.__conn.close()

    def add_download_url(self, url: str, tag: str):
        if self.__err:
            return
        download = {'_id': url, 'tag': tag, 'botname': botname}
        self.__db.download_links.update_one({'_id': url}, {'$set': download}, upsert=True)
        self.__conn.close()

    def check_download(self, url:str):
        if self.__err:
            return
        exist = self.__db.download_links.find_one({'_id': url})
        self.__conn.close()
        return exist

    def clear_download_links(self, bot_name=None):
        if self.__err:
            return
        if not bot_name:
            bot_name = botname
        self.__db.download_links.delete_many({'botname': bot_name})
        self.__conn.close()

    def remove_download(self, url: str):
        if self.__err:
            return
        self.__db.download_links.delete_one({'_id': url})
        self.__conn.close()

if DATABASE_URL:
    DbManger().db_load()