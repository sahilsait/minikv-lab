''' The logic for chain-replicated MiniKV '''

#pylint: disable=too-many-instance-attributes

import logging

from enum import Enum
from asyncio import Lock, Condition

from ..db import Database
from ..constants import PEER_START_PORT
from ..networking import Connector, Connection

class MessageType(Enum):
    ''' Possible types of messages between two nodes '''

    # Forward an update
    FORWARD_PASS = 1
    # Acknowledge an update has been applied
    BACKWARD_PASS = 2

class ChainReplication:
    ''' The main logic for chain-replicated MiniKV '''

    def __init__(self, identifier: int):
        assert identifier < 1000, "identifier should be a small integer"

        self._identifier = identifier
        self._connector = Connector(identifier,
                'localhost', PEER_START_PORT+identifier,
                MessageType, self)
        self._database = Database()
        self._previous: Connection|None = None
        self._next = None
        self._update_lock = Lock()
        self._update_cond = Condition(lock = self._update_lock)
        self._pending_updates: dict[int, dict] = {}

    async def start(self, previous: int|None):
        ''' Start the chain replication logic and connec to the previous node '''
        await self._connector.start()

        if previous is not None:
            print(f"Connecting to predecessor with id={previous}")
            self._previous = await self._connector.connect_to_peer(hostname='localhost',
                port=PEER_START_PORT+previous)

    @property
    def identifier(self) -> int:
        ''' Get the unique id of this node '''
        return self._identifier

    def is_tail(self):
        ''' Is this the tail of the chain? '''
        return self._next is None

    def is_head(self):
        ''' Is this the head of the chain? '''
        return self._previous is None

    async def handle_incoming_connection(self, peer):
        ''' Another node connected to us '''
        assert self._next is None
        logging.info("Node #%i got a new connection from node #%i",
                     self.identifier, peer.identifier)
        self._next = peer

    async def handle_disconnect(self, peer):
        ''' Another node disconnected from us '''
        logging.info("Node #%i lost connection from node #%i",
                     self.identifier, peer.identifier)

    async def handle_message(self, _peer: Connection, msg_type: MessageType, message):
        ''' Process a message from another node '''

        match msg_type:
            case MessageType.FORWARD_PASS:
                # TODO add forward/downward pass logic here
                # Apply the update locally
                self._database.put(message['key'], message['value'])
                
                if self.is_tail():
                    # If this is the tail, start the backward pass
                    await self._previous.send(MessageType.BACKWARD_PASS, message)
                else:
                    # Forward the update to the next node
                    async with self._update_lock:
                        self._pending_updates[message['txn_id']] = message
                    await self._next.send(MessageType.FORWARD_PASS, message)
            
            
            case MessageType.BACKWARD_PASS:
                # TODO add backward/acknowledgement pass logic here
                if self.is_head():
                    # If this is the head, complete the transaction
                    async with self._update_lock:
                        self._pending_updates.pop(message['txn_id'], None)
                        self._update_cond.notify_all()
                else:
                    # Forward the acknowledgment to the previous node
                    async with self._update_lock:
                        self._pending_updates.pop(message['txn_id'], None)
                    await self._previous.send(MessageType.BACKWARD_PASS, message)

    async def get_all(self):
        ''' Return all entries in the database '''
        return self._database.get_all()

    async def get(self, key):
        ''' Read an entry from the database '''
        return self._database.get(key)

    async def put(self, key, value):
        ''' Store a new entry on all nodes in the replica set '''
        assert self.is_head(), "Only the head can receive updates from clients"

        if self.is_tail():
            logging.info("Using fast path to store data. The chain is of length 1.")
            self._database.put(key, value)
        else:
            # TODO add request to pending_updates and wait for it to complete
            self._database.put(key, value)
            
            txn_id = hash(key)
            message = {
                'txn_id': txn_id,
                'key': key,
                'value': value
            }

            async with self._update_lock:
                self._pending_updates[txn_id] = message
                await self._next.send(MessageType.FORWARD_PASS, message)
                # Wait for the update to complete
                await self._update_cond.wait_for(lambda: txn_id not in self._pending_updates)

