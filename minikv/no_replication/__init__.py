''' The logic for non-replicated MiniKV '''

from .. import webserver
from ..db import Database

class NoReplication:
    ''' The logic for non-replicated MiniKV '''

    def __init__(self):
        self._database = Database()

    async def get_all(self):
        ''' Return all entries in the database '''
        return self._database.get_all()

    async def get(self, key):
        ''' Read an entry from the database '''
        return self._database.get(key)

    async def put(self, key, value):
        ''' Store a new entry to the database '''
        return self._database.put(key, value)

async def serve(index: int, connect_to: list[int]):
    ''' Run MiniKV with no replication '''

    assert index == 0
    assert len(connect_to) == 0

    logic = NoReplication()
    print("Started MiniKV (no replication)")

    await webserver.serve(logic, index)
