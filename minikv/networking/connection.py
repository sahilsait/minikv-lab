''' All logic for a connection to another peer resides here '''

#pylint: disable=too-many-arguments,too-many-instance-attributes

import pickle
import asyncio
import logging
import struct

from asyncio.streams import StreamReader, StreamWriter
from asyncio import Lock

class Connection:
    ''' Manages the connection to another node '''

    def __init__(self,
            identifier: int,
            reader: StreamReader,
            writer: StreamWriter,
            host: str,
            port: int,
            message_type: type,
            protocol_logic,
            in_data: bytes):

        self._identifier = identifier  # Make sure the ID is a string
        self._host = host
        self._message_type = message_type
        self._protocol_logic = protocol_logic
        self._port = int(port)
        self._reader = reader
        self._writer = writer
        self._send_lock = Lock()

        self._receive_task = asyncio.create_task(self._receive_loop(in_data))

    @property
    def hostname(self) -> str:
        ''' The hostname (domain name or IP) of the connect peer '''
        return self._host

    @property
    def port(self) -> int:
        ''' The TCP port we connected to '''
        return self._port

    @property
    def identifier(self) -> int:
        ''' The unqiue identifier of the connected peer '''
        return self._identifier

    async def _receive_loop(self, in_data: bytes):
        """
           This will check for new data from the connected peer,
           until it disconnects.
        """
        buffer = in_data  # Hold the stream that comes in!

        while not self._reader.at_eof():
            chunk = b''

            #try:
            chunk = await self._reader.read(4096)
            #except Exception as err:
            #    logging.error(f'Unexpected connection error: {err}')
            #    break

            if len(chunk) == 0:
                break

            logging.debug("Got data of length %i", len(chunk))

            buffer += chunk
            header_len = struct.calcsize("IH")

            while len(buffer) >= header_len:
                header = struct.unpack("IH", buffer[:header_len])
                msg_len = header[0]

                try:
                    msg_type = self._message_type(header[1])
                except ValueError:
                    logging.error("Got an invalid message type")
                    return

                total_len = header_len+msg_len

                assert total_len <= len(buffer)

                if msg_len > 0:
                    if len(buffer) < total_len:
                        # Did not receive full message yet...
                        break

                    # Remove message from buffer and keep the rest
                    msg = buffer[header_len:total_len]
                    buffer = buffer[total_len:]

                    msg = pickle.loads(msg)

                    await self._protocol_logic.handle_message(self, msg_type, msg)
                else:
                    buffer = buffer[header_len:]
                    await self._protocol_logic.handle_message(self, msg_type, None)

        self._protocol_logic.handle_disconnect(self)
        logging.debug("Connection to peer closed")

    async def disconnect(self):
        ''' Close the connection to this peer '''

        try:
            self._writer.close()
            self._receive_task.cancel()
            await self._writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError):
            pass

    async def send(self, msg_type, payload):
        ''' Send a message to the connect peer '''

        payload = pickle.dumps(payload)
        payload_len = len(payload)

        header = struct.pack("IH", payload_len, msg_type.value)

        # Make sure only one task writes to the socket at a time
        async with self._send_lock:
            #try:
            self._writer.write(header+payload)
            await self._writer.drain()
            #except Exception as err:
            #    logging.debug("Error sending data to node: %s", err)
            #    await self.disconnect()
