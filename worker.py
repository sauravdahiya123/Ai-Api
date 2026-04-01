# from rq import Worker, Queue, Connection
# import redis

# redis_conn = redis.Redis()

# with Connection(redis_conn):
#     worker = Worker([Queue("crawler")])
#     worker.work()