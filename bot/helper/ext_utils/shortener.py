from base64 import b64encode
from cfscrape import create_scraper
from urllib3 import disable_warnings
from urllib.parse import quote, unquote
from random import choice, random, randrange
from bot import LOGGER, SHORTENER_APIS, SHORTENERES

def short_url(longurl):
    if not SHORTENERES and not SHORTENER_APIS:
        return longurl
    try:
        i = 0 if len(SHORTENERES) == 1 else randrange(len(SHORTENERES))
        _shortener = SHORTENERES[i].strip()
        _shortener_api = SHORTENER_APIS[i].strip()
        cget = create_scraper().get
        disable_warnings()
        try:
            unquote(longurl).encode('ascii')
            if "{" in unquote(longurl) or "}" in unquote(longurl):
                raise TypeError
        except (UnicodeEncodeError, TypeError):
            longurl = cget('http://tinyurl.com/api-create.php', params=dict(url=longurl)).text
        if "shorte.st" in _shortener:
            return cget(f'http://api.shorte.st/stxt/{_shortener_api}/{longurl}', verify=False).text
        elif "linkvertise" in _shortener:
            url = quote(b64encode(longurl.encode("utf-8")))
            linkvertise = [
                f"https://link-to.net/{_shortener_api}/{random() * 1000}/dynamic?r={url}",
                f"https://up-to-down.net/{_shortener_api}/{random() * 1000}/dynamic?r={url}",
                f"https://direct-link.net/{_shortener_api}/{random() * 1000}/dynamic?r={url}",
                f"https://file-link.net/{_shortener_api}/{random() * 1000}/dynamic?r={url}"]
            return choice(linkvertise)
        elif "bitly.com" in _shortener:
            shorten_url = "https://api-ssl.bit.ly/v4/shorten"
            headers = {"Authorization": f"Bearer {_shortener_api}"}
            response = create_scraper().post(shorten_url, json={"long_url": longurl}, headers=headers).json()
            return response["link"]
        elif "ouo.io" in _shortener:
            return cget(f'http://ouo.io/api/{_shortener_api}?s={longurl}', verify=False).text
        elif "adfoc.us" in _shortener:
            return cget(f'http://adfoc.us/api/?key={_shortener_api}&url={longurl}', verify=False).text
        elif "cutt.ly" in _shortener:
            return cget(f'http://cutt.ly/api/api.php?key={_shortener_api}&short={longurl}', verify=False).json()['url']['shortLink']
        else:
            return cget(f'https://{_shortener}/api?api={_shortener_api}&url={quote(longurl)}&format=text').text
    except Exception as e:
        LOGGER.error(e)
        return longurl