''' A simple client that fetches data or writes to the database using HTTP '''

#pylint: disable=too-many-branches,too-many-statements

import argparse
import sys
import json
import logging

from sys import argv
from string import ascii_lowercase
from random import randint, choice
from requests import Session

class RequestSender:
    ''' Maintains a connection to the MiniKV server '''

    def __init__(self, address):
        self._address = address
        self._session = Session()

    @property
    def base_url(self) -> str:
        ''' The start of the URL we use for all requests '''
        return f"http://{self._address}"

    def write(self, key, value):
        ''' Write a new entry to the database '''
        result = self._session.post(f"{self.base_url}/put?key={key}",
            data=json.dumps({'value': value}), timeout=2.0)
        result.raise_for_status()

    def read(self, key) -> str:
        ''' Read an entry from the database '''
        result = self._session.get(f"{self.base_url}/get?key={key}",
            timeout=2.0)
        result.raise_for_status()
        return result.json()["value"]

def run():
    ''' Main logic of the client '''

    # Invoked by test runner?
    if argv[0] == "-c":
        argv[0] = "python"

    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['test', 'fill', 'check-values', 'random-ops'])
    parser.add_argument('--server-address', default="127.0.0.1:8080")
    parser.add_argument('--key-offset', default=0, type=int,
            help="Start the key range at an offset, not 0")
    parser.add_argument('--key-range', default=1000, type=int)
    parser.add_argument('--value-prefix', default="value", type=str)
    parser.add_argument('--write-chance', default=50, type=int)
    parser.add_argument('--num-ops', default=1000, type=int)
    parser.add_argument("--loglevel", default="info",
        help="Set the logging verbosity", choices=["warn", "debug", "info"])

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper())

    if args.key_range <= 0:
        print("ERROR: Key range must be a positive number")
        sys.exit(1)

    if args.key_offset < 0:
        print("ERROR: Key offset cannot be negative")
        sys.exit(1)

    if args.write_chance < 0 or args.write_chance > 100:
        print("ERROR: Write chance must be in [0;100]")
        sys.exit(1)

    key_range = range(args.key_offset, args.key_offset+args.key_range)
    rsender = RequestSender(args.server_address)

    def make_key(idx):
        ''' Generate an entries key from its index '''
        return f"key{idx}"

    def make_value(idx):
        ''' Generate an entries value from its index '''
        return f"{args.value_prefix}{idx}"

    match args.mode:
        case "test":
            print("Running test")

            entries = {}

            for i in key_range:
                key = make_key(i)
                value = make_value(i)
                rsender.write(key, value)
                entries[key] = value

            for i in key_range:
                key = make_key(i)
                val = rsender.read(key)
                assert val == entries[key]

            print("Test successful!")

        case "fill":
            for i in key_range:
                rsender.write(make_key(i), make_value(i))

        case "check-values":
            for i in key_range:
                key = make_key(i)
                expected = make_value(i)

                result = rsender.read(key)
                if result != expected:
                    print(f'Invalid value for key "{key}". '
                          f'Expected "{expected}", but got "{result}".')
                    sys.exit(1)

        case "random-ops":
            for _ in range(args.num_ops):
                index = randint(0, args.key_range-1)
                key = make_key(index)
                rval = randint(0,100)
                if rval < args.write_chance:
                    rsender.write(key, "foobar")
                else:
                    result = rsender.read(key)
                    expected = make_value(index)
                    if result != expected:
                        print(f'Invalid value for key "{key}". '
                              f'Expected "{expected}", but got "{result}".')
                        sys.exit(1)
