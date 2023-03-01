from hashlib import sha1
from os import path, remove
from re import search
from urllib.parse import parse_qs, urlparse

from bencoding import bdecode, bencode

from bot import LOGGER


async def extract_link(link, shouldDel=False):
    try:
        if link and link.startswith('magnet:'):
            raw_link = search(r'(?<=xt=urn:(btih|btmh):)[a-zA-Z0-9]+', link).group(0).lower()
        elif "drive.google.com" in urlparse(link).netloc:
            if "folders" in link or "file" in link:
                regex = r"https:\/\/drive\.google\.com\/(?:drive(.*?)\/folders\/|file(.*?)?\/d\/)([-\w]+)"
                res = search(regex, link)
                raw_link = link if res is None else res.group(3)
            raw_link = parse_qs(urlparse(link).query)['id'][0]
        elif path.exists(link):
            with open(link, "rb") as f:
                decodedDict = bdecode(f.read())
            raw_link = str(sha1(bencode(decodedDict[b'info'])).hexdigest())
            if shouldDel:
                remove(link)
        else:
            raw_link = link
    except Exception as e:
        LOGGER.error(e)
        raw_link = link
    return raw_link
