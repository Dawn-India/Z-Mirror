#!/usr/bin/env python3
from logging import ERROR, getLogger
from os import listdir, path as ospath
from pickle import load as pload
from random import randrange
from re import search as re_search
from urllib.parse import parse_qs, urlparse

from google.oauth2 import service_account
from googleapiclient.discovery import build
from tenacity import (retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

from bot import config_dict

LOGGER = getLogger(__name__)
getLogger('googleapiclient.discovery').setLevel(ERROR)


class GoogleDriveHelper:

    def __init__(self, listener=None, name=None):
        self.OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']
        self.G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
        self.G_DRIVE_BASE_DOWNLOAD_URL = "https://drive.google.com/uc?id={}&export=download"
        self.G_DRIVE_DIR_BASE_DOWNLOAD_URL = "https://drive.google.com/drive/folders/{}"
        self.is_downloading = False
        self.is_uploading = False
        self.is_cloning = False
        self.is_cancelled = False
        self.sa_index = 0
        self.sa_count = 1
        self.sa_number = 100
        self.alt_auth = False
        self.listener = listener
        self.service = self.authorize()
        self.name = name
        self.total_files = 0
        self.total_folders = 0
        self.file_processed_bytes = 0
        self.proc_bytes = 0
        self.total_bytes = 0
        self.total_time = 0
        self.status = None
        self.update_interval = 3

    @property
    def speed(self):
        try:
            return self.proc_bytes / self.total_time
        except:
            return 0

    @property
    def processed_bytes(self):
        return self.proc_bytes

    def authorize(self):
        credentials = None
        if config_dict['USE_SERVICE_ACCOUNTS']:
            json_files = listdir("accounts")
            self.sa_number = len(json_files)
            self.sa_index = randrange(self.sa_number)
            LOGGER.info(f"Authorizing with {json_files[self.sa_index]} service account")
            credentials = service_account.Credentials.from_service_account_file(f'accounts/{json_files[self.sa_index]}', scopes=self.OAUTH_SCOPE)
        elif ospath.exists('token.pickle'):
            LOGGER.info("Authorize with token.pickle")
            with open('token.pickle', 'rb') as f:
                credentials = pload(f)
        else:
            LOGGER.error('token.pickle not found!')
            return
        return build('drive', 'v3', credentials=credentials, cache_discovery=False)

    def alt_authorize(self):
        if not self.alt_auth:
            self.alt_auth = True
            if ospath.exists('token.pickle'):
                LOGGER.info("Authorize with token.pickle")
                with open('token.pickle', 'rb') as f:
                    credentials = pload(f)
                return build('drive', 'v3', credentials=credentials, cache_discovery=False)
            else:
                LOGGER.error('token.pickle not found!')

    def switchServiceAccount(self):
        if self.sa_index == self.sa_number - 1:
            self.sa_index = 0
        else:
            self.sa_index += 1
        self.sa_count += 1
        LOGGER.info(f"Switching to {self.sa_index} index")
        self.service = self.authorize()

    @staticmethod
    def getIdFromUrl(link):
        if "folders" in link or "file" in link:
            regex = r"https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)"
            res = re_search(regex, link)
            if res is None:
                raise IndexError("G-Drive ID not found.")
            return res.group(3)
        parsed = urlparse(link)
        return parse_qs(parsed.query)['id'][0]

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def set_permission(self, file_id):
        permissions = {
            'role': 'reader',
            'type': 'anyone',
            'value': None,
            'withLink': True
        }
        return self.service.permissions().create(fileId=file_id, body=permissions, supportsAllDrives=True).execute()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def getFileMetadata(self, file_id):
        return self.service.files().get(fileId=file_id, supportsAllDrives=True, fields='name, id, mimeType, size').execute()

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def getFolderData(self, file_id):
        try:
            meta = self.service.files().get(fileId=file_id, supportsAllDrives=True).execute()
            if meta.get('mimeType', '') == self.G_DRIVE_DIR_MIME_TYPE:
                return meta.get('name')
        except:
            return

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def getFilesByFolderId(self, folder_id):
        page_token = None
        files = []
        while True:
            response = self.service.files().list(supportsAllDrives=True, includeItemsFromAllDrives=True,
                                                 q=f"'{folder_id}' in parents and trashed = false",
                                                 spaces='drive', pageSize=200,
                                                 fields='nextPageToken, files(id, name, mimeType, size, shortcutDetails)',
                                                 orderBy='folder, name', pageToken=page_token).execute()
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            if page_token is None:
                break
        return files

    async def progress(self):
        if self.status is not None:
            chunk_size = self.status.total_size * \
                self.status.progress() - self.file_processed_bytes
            self.file_processed_bytes = self.status.total_size * self.status.progress()
            self.proc_bytes += chunk_size
            self.total_time += self.update_interval

    def escapes(self, estr):
        chars = ['\\', "'", '"', r'\a', r'\b', r'\f', r'\n', r'\r', r'\t']
        for char in chars:
            estr = estr.replace(char, f'\\{char}')
        return estr.strip()

    def get_recursive_list(self, file, rootid):
        rtnlist = []
        if rootid == "root":
            rootid = self.service.files().get(fileId='root', fields='id').execute().get('id')
        x = file.get("name")
        y = file.get("id")
        while (y != rootid):
            rtnlist.append(x)
            file = self.service.files().get(fileId=file.get("parents")[0], supportsAllDrives=True,
                                              fields='id, name, parents').execute()
            x = file.get("name")
            y = file.get("id")
        rtnlist.reverse()
        return rtnlist

    @retry(wait=wait_exponential(multiplier=2, min=3, max=6), stop=stop_after_attempt(3),
           retry=retry_if_exception_type(Exception))
    def create_directory(self, directory_name, dest_id):
        file_metadata = {
            "name": directory_name,
            "description": f'Uploaded by {self.listener.message.from_user.id}',
            "mimeType": self.G_DRIVE_DIR_MIME_TYPE
        }
        if dest_id is not None:
            file_metadata["parents"] = [dest_id]
        file = self.service.files().create(body=file_metadata, supportsAllDrives=True).execute()
        file_id = file.get("id")
        if not config_dict['IS_TEAM_DRIVE']:
            self.set_permission(file_id)
        LOGGER.info(f'Created G-Drive Folder:\nName: {file.get("name")}\nID: {file_id}')
        return file_id

    async def cancel_download(self):
        self.is_cancelled = True
        if self.is_downloading:
            LOGGER.info(f"Cancelling Download: {self.name}")
            await self.listener.onDownloadError('Download stopped by user!')
        elif self.is_cloning:
            LOGGER.info(f"Cancelling Clone: {self.name}")
            await self.listener.onUploadError('your clone has been stopped and cloned data has been deleted!')
        elif self.is_uploading:
            LOGGER.info(f"Cancelling Upload: {self.name}")
            await self.listener.onUploadError('your upload has been stopped and uploaded data has been deleted!')
