''' Database logic '''

import logging

from threading import Lock

class Database:
    ''' Stores key/value pairs in memory '''

    def __init__(self):
        self._lock = Lock()
        self._data = {}

    def get(self, key: str) -> str|None:
        ''' Get the value of the entry with the specified key '''

        with self._lock:
            result = self._data.get(key, None)
            logging.debug('Got get request for key "%s". Result was "%s".', key, str(result))

        return result

    def put(self, key: str, value: str) -> None:
        ''' Store a new entry or update an existing one '''

        with self._lock:
            logging.debug('Got put request to store "%s" for key "%s"', value, key)
            self._data[key] = value

    def get_all(self) -> list[tuple[str, str]]:
        ''' Get a list of all key-value pairs '''

        with self._lock:
            return list(self._data.items())
