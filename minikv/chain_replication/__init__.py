''' Implementation for chain-replicated MiniKV '''

import logging

from asyncio import Lock, Condition
from random import randint

from .. import webserver
from ..db import Database
from ..constants import PEER_START_PORT
from ..networking import Connector, Connection

from .logic import ChainReplication

async def serve(index: int, connect_to: list[int]):
    ''' Run MiniKV with chain replication '''

    assert len(connect_to) <= 1

    if len(connect_to) == 0:
        previous = None
    else:
        previous = connect_to[0]

    logic = ChainReplication(index)
    await logic.start(previous)
    print(f"Started MiniKV node with id={index} (chain replication)")

    await webserver.serve(logic, index)
