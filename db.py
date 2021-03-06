import os
from contextlib import contextmanager

import threading
import asyncpg
from config import postgres_config


MIN_CONNECTION_POOL_SIZE = 1
MAX_CONNECTION_POOL_SIZE = 10

_pool_holder = threading.local()
params = postgres_config()

async def get_pool():
    global _pool_holder
    pool = getattr(_pool_holder, "pool", None)
    if pool is None:
        pool = await asyncpg.create_pool(
            **params,
            min_size=MIN_CONNECTION_POOL_SIZE,
            max_size=MAX_CONNECTION_POOL_SIZE
        )
        setattr(_pool_holder, "pool", pool)
    return pool

async def close_pool():
    global _pool_holder
    pool = getattr(_pool_holder, "pool", None)
    if pool is not None:
        await pool.close()
        setattr(_pool_holder, "pool", None)

# Database API

async def execute(sql, *args):
    pool = await get_pool()
    async with pool.acquire() as con:
        return await con.execute(sql, *args)


async def fetch(sql, *args):
    pool = await get_pool()
    async with pool.acquire() as con:
        return await con.fetch(sql, *args)

async def fetchrow(sql, *args):
    pool = await get_pool()
    async with pool.acquire() as con:
        return await con.fetchrow(sql, *args)

async def fetchval(sql, *args):
    pool = await get_pool()
    async with pool.acquire() as con:
        return await con.fetchval(sql, *args)

async def explain(sql, *params, tx=None):
    db_obj = tx if tx is not None else __import__(__name__)
    rows = await db_obj.fetch("EXPLAIN " + sql, *params)
    return "\n".join(map(lambda r: r["QUERY PLAN"], rows))

class transaction:
    def __init__(self, readonly = False):
        self.readonly = readonly
        self.pool = None
        self.con = None
        self.tx = None

    async def __aenter__(self):
        self.pool = await get_pool()
        self.con = await self.pool.acquire()
        self.tx = self.con.transaction(readonly=self.readonly, isolation='serializable' if self.readonly else 'read_committed')
        await self.tx.start()
        return self.con

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            await self.tx.rollback()
        else:
            await self.tx.commit()

        await self.pool.release(self.con)
