''' Entry point for MiniKV '''

import logging
import argparse
import asyncio

from sys import argv

from . import client
from . import chain_replication
from . import no_replication

from .client import run as run_client

def run_node():
    ''' Main function that picks a backend, spawns asyncio, and runs the node '''

    # Invoked by test runner?
    if argv[0] == "-c":
        argv[0] = "python"

    parser = argparse.ArgumentParser()
    parser.add_argument('replication_type', default='none',
        choices=['client', 'none', 'chain', 'gossip'])
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--loglevel", default="info",
        help="Set the logging verbosity", choices=["warn", "debug", "info"])
    parser.add_argument("-C", "--connect-to", default="", required=False,
        help="Addresses of other nodes to connect to, separated by a comma.")

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper())

    if args.connect_to:
        connect_to = [int(x) for x in args.connect_to.split(',')]
    else:
        connect_to = []

    assert args.index >= 0

    asyncio.run(_execute_backend(args.replication_type, args.index, connect_to))

async def _execute_backend(replication_type: str, index: int, connect_to: list[int]):
    match replication_type:
        case "none":
            await no_replication.serve(index, connect_to)
        case "chain":
            await chain_replication.serve(index, connect_to)
        case _:
            print(f"Unexpected replication type: {replication_type}")

if __name__ == '__main__':
    run_node()
