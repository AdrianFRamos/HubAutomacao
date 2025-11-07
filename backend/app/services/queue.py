import rq
import redis
from app.core.config import settings

redis_conn = redis.from_url(settings.REDIS_URL)
queue = rq.Queue("runs", connection=redis_conn)
