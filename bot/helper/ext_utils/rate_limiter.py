# Reference https://github.com/sanjit-sinha/TelegramBot-Boilerplate/blob/main/TelegramBot/helpers/ratelimiter.py

from functools import wraps

from cachetools import TTLCache
from pyrate_limiter import (BucketFullException, Limiter, MemoryListBucket,
                            RequestRate)

from bot import config_dict
from bot.helper.telegram_helper.filters import CustomFilters


class RateLimiter:
    def __init__(self) -> None:

        # 1 requests per seconds
        self.second_rate = RequestRate(1, 1)

        self.limiter = Limiter(self.second_rate, bucket_class=MemoryListBucket)

    def acquire(self, userid):
        try:
            self.limiter.try_acquire(userid)
            return False
        except BucketFullException:
            return True

ratelimit = RateLimiter()
warned_users = TTLCache(maxsize=128, ttl=60)

def ratelimiter(func):
    @wraps(func)
    def decorator(update, context):
        if not config_dict['ENABLE_RATE_LIMITER']:
            return func(update, context)
        if query := update.callback_query:
            userid = query.from_user.id
        elif message := update.message:
            userid = message.from_user.id
        else:
            return func(update, context)
        if CustomFilters.owner_query(userid) or userid == 1087968824:
            return func(update, context)
        is_limited = ratelimit.acquire(userid)
        if is_limited and userid not in warned_users:
            if query := update.callback_query:
                query.answer("Spam detected! ignoring your all requests for few minutes.", show_alert=True)
                warned_users[userid] = 1
                return
            elif message := update.message:
                message.reply_text("Spam detected! ignoring your all requests for few minutes.")
                warned_users[userid] = 1
                return
            else:
                return func(update, context)
        elif is_limited and userid in warned_users:
            pass
        else:
            return func(update, context)
    return decorator