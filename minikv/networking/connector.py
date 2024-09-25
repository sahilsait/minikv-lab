''' All connector-related code resides here '''

#pylint: disable=too-many-arguments,too-many-positional-arguments

import asyncio
import struct
import logging

from asyncio.streams import StreamReader, StreamWriter

from .connection import Connection

class Connector:
    '''
        A connector listens for incoming connections from or
        can establish initiate new connections to other connectors
    '''
    def __init__(self,
            identifier: int,
            hostname: str,
            port: int,
            message_type,
            protocol_logic,
        ):
        ''' Creates the connector and starts listening at the specified port '''

        self._identifier = identifier
        self._hostname = hostname
        self._port = port
        self._message_type = message_type
        self._protocol_logic = protocol_logic
        self._tcp_server = None
        self._peers: dict[str, Connection] = {}

    @property
    def identifier(self) -> int:
        ''' The unique identifier of this node '''
        return self._identifier

    @property
    def hostname(self) -> str:
        ''' The hostname we listen for new connections on '''
        return self._hostname

    @property
    def port(self) -> int:
        ''' The TCP port we listen for new connections on '''
        return self._port

    async def start(self):
        ''' Start listening for connections. You should only call this once '''

        assert self._tcp_server is None

        self._tcp_server = await asyncio.start_server(self._handle_connection,
                                                 port=self.port,
                                                 reuse_port=True,
                                                 reuse_address=True)

    async def _handle_connection(self,
            reader: StreamReader,
            writer: StreamWriter):
        logging.info("Got new incoming connection")

        await self._send_identifier(writer)
        peer_id, hostname, port, in_data = await self._receive_identifier(reader)

        # Cannot connect with yourself
        assert self.identifier != peer_id

        # Check for duplicate connections
        if peer_id in self._peers:
            logging.warning("Node with id=%s is already connected to us", peer_id)
            writer.close()
        else:
            peer = Connection(int(peer_id), reader, writer, hostname, port,
                        self._message_type, self._protocol_logic, in_data)
            self._peers[peer_id] = peer
            await self._protocol_logic.handle_incoming_connection(peer)

    async def _send_identifier(self, writer):
        msg = f"{self.identifier}:{self.hostname}:{self.port}"

        header = struct.pack("I", len(msg))
        writer.write(header)
        writer.write(msg.encode('utf-8'))

        await writer.drain()

    async def _receive_identifier(self, reader) -> tuple[str, str, int, bytes]:
        in_data = b''

        while True:
            in_data += await reader.read(4096)
            header_len = struct.calcsize("I")

            if len(in_data) >= header_len:
                header = struct.unpack("I", in_data[:header_len])
                msg_len = header[0]
                total_len = header_len+msg_len

            if len(in_data) >= total_len:
                identifier, host, port = in_data[header_len:total_len].decode('utf-8').split(':')
                return identifier, host, int(port), in_data[total_len:]

    async def connect_to_peer(self, hostname: str, port: int) -> None|Connection:
        """ 
        Establish a connection to another node
        """

        if hostname == self.hostname and port == self.port:
            logging.error("Cannot connect with yourself!")
            return None

        #try:
        reader, writer = await asyncio.open_connection(hostname, port)
        await self._send_identifier(writer)

        peer_id, hostname, port, in_data = await self._receive_identifier(reader)

        # Cannot connect with yourself
        assert self.identifier != peer_id

        # Check for duplicate connections
        if peer_id in self._peers:
            logging.error("Already connected to node with id=%s", peer_id)
            return self._peers[peer_id]

        peer = Connection(int(peer_id), reader, writer, hostname, port,
                self._message_type, self._protocol_logic, in_data)
        self._peers[peer_id] = peer

        return peer

        #except Exception as err:
        #    logging.error("Could not connect with node: %s", err)
        #    return False

    def has_peer(self, peer_id):
        ''' Are we connected to a peer with the specified id? '''

        for node in self._peers:
            if node.identifier == peer_id:
                return True

        return False
