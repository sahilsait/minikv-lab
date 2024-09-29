#! /bin/env python33

# pylint: disable=consider-using-with,broad-exception-caught,too-few-public-methods,raise-missing-from

''' Runs the integration tests for MiniKV '''

import sys
import json
import argparse

from subprocess import CalledProcessError, check_call, Popen
from time import sleep

class TestError(Exception):
    ''' An error indicating a test failed '''

class TestRunner:
    ''' Sets up the replica set for us to run the test on '''

    def __init__(self, num_replicas: int, replication_type: str, loglevel: str):
        self._log: list[str] = []

        self.log("Started Test Runner")

        assert num_replicas > 0
        servers = []

        # Start all servers
        for index in range(num_replicas):
            if index > 0:
                if replication_type == "chain":
                    connect_to = f"-C{index-1}"
                else:
                    raise RuntimeError("No supported")
            else:
                connect_to = None

            server_args = ["python3", "-c" , "import minikv; minikv.run_node();",
                replication_type, "--loglevel="+loglevel, f"--index={index}"]

            if connect_to:
                server_args += [connect_to]

            servers.append(Popen(server_args))
            sleep(0.1)

        self.log(f"Started {num_replicas} replicas")

        self._servers = servers

    def log(self, msg):
        ''' Print a new log message '''
        print(msg)
        self._log.append(msg)

    def get_output(self) -> str:
        ''' Get a log messages as a string '''
        return '\n'.join(self._log)

    def shutdown(self):
        ''' Shut down the test and all servers we set up for it '''
        for server in self._servers:
            server.kill()
            server.wait()

def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument("replication_type",
        choices=["none", "chain", "gossip"])
    parser.add_argument("--fail-early", action='store_true',
        help="Stop after encountering the first failure")
    parser.add_argument("--scale-factor", default=1, type=int,
        help="The factor to increase the number of keys by")
    parser.add_argument("--loglevel", default="warn",
        help="Set the logging verbosity", choices=["warn", "debug", "info"])
    parser.add_argument("--gradescope", action='store_true')

    args = parser.parse_args()

    if args.scale_factor <= 0:
        raise TestError("Invalid scale factor")

    configs = {
        "One Replica": { "num-replicas": 1, },
        "Five Replicas": { "num-replicas": 5, },
    }

    tests = {
        'Insert (Single Client)': test_insert_single_client,
        'Insert (Multi Client)': test_insert_multi_client,
        'Update': test_update,
    }

    output = {
        'tests': [],
        'stdout_visibility': 'visible',
        'extra_data': {
            'scale_factor':args.scale_factor,
            'replication_type': args.replication_type,
        }
    }

    success_count = 0
    failed_tests = []

    for conf_name, conf_values in configs.items():
        if args.fail_early and len(failed_tests) > 0:
            break

        if conf_values['num-replicas'] > 1 and args.replication_type == 'none':
            # Skip...
            continue

        for name, test in tests.items():

            print(f'### Running test "{name}" for config "{conf_name}" ###')
            success = True

            runner = TestRunner(conf_values["num-replicas"], args.replication_type, args.loglevel)

            try:
                test(runner, conf_values, args)
            except Exception as err:
                runner.log(f"ERROR: {err}")
                success = False

            runner.shutdown()
            if success:
                runner.log(f'>> Test "{name}" passed')
                success_count += 1
            else:
                runner.log(f'>> Test "{name}" failed')
                failed_tests.append(name)

            output['tests'].append({
                'name': conf_name + ": " + name,
                'output': runner.get_output(),
                'output_format': 'text',
                'status': 'passed' if success else 'failed',
                'max_score': 10.0,
                'score': 10.0 if success else 0.0,
            })

    print(f"### {success_count} tests passed, {len(failed_tests)} failed")

    if len(failed_tests) > 0:
        print(f"The following tests failed: {', '.join(failed_tests)}")

    if args.gradescope:
        with open('gradescope.json', 'w', encoding='utf-8') as ofile:
            json.dump(output, ofile)
            print("Wrote result to gradescope.json")

    sys.exit(len(failed_tests))

def test_insert_single_client(runner, conf_values, args):
    ''' Test MiniKV with a single client '''

    num_keys = args.scale_factor * 10

    # Load data into the replica cluster
    try:
        check_call(["python3", "-c", "import minikv; minikv.run_client();",
                "fill", "--loglevel="+args.loglevel,
                f"--key-range={num_keys}"])
    except CalledProcessError:
        raise TestError("Failed to load data")

    runner.log("All data written to MiniKV")

    # Check that every node has all data
    for idx in range(conf_values["num-replicas"]):
        runner.log(f"Checking node with id={idx}")

        try:
            check_call(["python3", "-c", "import minikv; minikv.run_client();",
                        "check-values", "--loglevel="+args.loglevel,
                        f"--server-address=localhost:{8080+idx}",
                        f"--key-range={num_keys}"])
        except CalledProcessError:
            raise TestError("Check failed")

def test_update(runner, conf_values, args):
    ''' Test MiniKV with a single client '''

    num_keys = args.scale_factor * 10
    value = "therearethreersinstrawberry"

    check_call(["python3", "-c", "import minikv; minikv.run_client();",
                "fill", "--loglevel="+args.loglevel,
                f"--key-range={num_keys}", "--value-prefix=foobar"])

    runner.log("First pass of data written to MiniKV")

    check_call(["python3", "-c", "import minikv; minikv.run_client();",
                "fill", "--loglevel="+args.loglevel,
                f"--key-range={num_keys}", f"--value-prefix={value}"])

    runner.log("Second pass of data written to MiniKV")

    # Check that every node has all data
    for idx in range(conf_values["num-replicas"]):
        runner.log(f"Checking node with id={idx}")

        try:
            check_call(["python3", "-c", "import minikv; minikv.run_client();",
                    "check-values", "--loglevel="+args.loglevel,
                    f"--server-address=localhost:{8080+idx}",
                    f"--key-range={num_keys}", f"--value-prefix={value}"])
        except CalledProcessError:
            raise TestError("Check failed")


def test_insert_multi_client(runner, conf_values, args):
    ''' Test MiniKV with a multiple concurrent clients '''

    num_clients = 10
    num_keys = args.scale_factor * 1000

    if num_clients > num_keys:
        runner.log("WARNING: key range smaller than number of clients")

    if num_keys % num_clients:
        runner.log("WARNING: key range not a mulitple of the number of clients")

    sub_range = int(num_keys / num_clients)

    # Load data into the replica cluster
    clients = []
    for i in range(num_clients):
        proc = Popen(["python3", "-c", "import minikv; minikv.run_client();",
                "fill", "--loglevel="+args.loglevel, f"--key-range={sub_range}",
                f"--key-offset={sub_range * i}"])
        clients.append(proc)

    for client in clients:
        client.wait()
        if client.returncode != 0:
            raise TestError("Load failed")

    runner.log("All data written to MiniKV")

    # Check that every node has all data
    clients = []
    for idx in range(conf_values["num-replicas"]):
        runner.log(f"Checking node with id={idx}")

        for i in range(num_clients):
            client = Popen(["python3", "-c", "import minikv; minikv.run_client();",
                "check-values", "--loglevel="+args.loglevel,
                f"--server-address=localhost:{8080+idx}",
                f"--key-range={sub_range}",
                f"--key-offset={sub_range * i}"])
            clients.append(client)

    for client in clients:
        client.wait()
        if client.returncode != 0:
            raise TestError("Check failed")

if __name__ == "__main__":
    _main()
