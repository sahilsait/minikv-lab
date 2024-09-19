# MiniKV Lab

MiniKV is a very simple key-value store written in Python with asyncio.

## Development Setup
### Prerequisites
You need to have a UNIX-like system to complete this project.
This means you will either need to 1) set up Windows subsystem for Linux, 2) use a Linux Distribution, or 3) use a Mac.

Then, ensure that you have git, Python, pip, and Make installed. For example, on Ubuntu you would run the following

```bash
sudo apt install git python3 python3-pip make
```

### Forking the Repository

Note, it is important that you use a private repository for your solution, so that other student do not see it.
To create a private copy of the repository of this repository you need to do the following.

Log into GitHub and click + at the top right. Then, choose "Import Repository" and insert the following:

* The URL for your source repository: https://github.com/kaimast/minikv-lab.git
* Repository name: minikv-lab 
* Privacy: private

Then, click begin import. This will take a while but evenutally you will have your own repository to work with.

### Python Environment
Ideally, you will use a Python virtual environment to keep your local machine clean, but it is not strictly requirement.
Take a look [here](https://docs.python.org/3/library/venv.html) how to set up a virtual environment.

Then you can install MiniKV, which will also install its dependencies, using `make install`.
You might also want to install pylint and mypy (`pip install pylint mypy`), so you can run lint checks.

### Verify Installation
This project already implements a key-value store that provides no replication
Now you should be able to test that implementation without any issues.

To run tests simply enter `make test-no-replication` and it should say `### 3 tests passed, 0 failed` on the very last line.

## Project Setup 
You are now tasked with implementing chain replication.
We already provide you with skeleton code that starts up nodes and connects them with other nodes in the chain.
Simply run `./test-runner.py chain --fail-early` to see what happens.

All skeleton code you need to modify sits in `minikv/chain_replication/logic.py`.
Try to understand the code that is already there and add the missing code where there are `TODO` statements.

You should only modify files within `minikv/chain_replication`, do not modify the Makefile, test scripts, or client code.

## MiniKV Chain Replication Protocol
Here is a quick outline how updates are supposed to work in MinkKV.
This is more or less how we talked about the protocol in class.

The client sends an update request to the head of the chain.
The head should assign this request some unique identifier (e.g., a random integer), apply the update locally, and keep track of it until it has been applied to all nodes in the chain.
The unique id is needed as there might be multiple concurrent updates to the same key.

The request then travels through the chain (forward pass).
Every node, applies the update to their local state, stores the pending request, and forwards the update to its successor.
The tail node is a special case, where the pending request is not stored, because it does not have a successor.
Instead, the tail node initiates the acknowledgement (or backward) pass.

When receiving a backward pass message, nodes remove the request from their set of pending updates and notify their predecessor.
Once the head receives an acknowledgement/backward pass message, it will reply to the client that the update was successful.

## Background and Tips
### Coding Style
Because object members are always public in Python, it is good practice to prefix private variables and functions with an underscore.
You will see this commonly on the code. E.g., `ChainReplication._identifier` is the unique identifier of a node and should not be accessed directly. Instead, one should use the `ChainReplication.identifier` [property](https://docs.python.org/3/library/functions.html#property).

### Asyncio
[Asyncio](https://docs.python.org/3/library/asyncio.html) enables handling many concurrent network connections efficiently.
It spawns a task, similar to a thread, for each active network connection and switches between tasks whenver new data is received.

You do not have to interact with asyncio directly much but the code being asynchronous means you will see this a lot.
```python
await webserver.serve(logic, index)
```
This line is from the noreplication implementation of MiniKV, and starts a webserver.
The await instruction means this line will block until the webserver terminates.
Any function marked with `async` can be waited for using `await`.

*How is this different from just calling a function?*
async/await allows running other things while we are waiting for a particular task to complete.
This is particularly important in I/O bound tasks like a webserver or something that performs distributed consensus.

*Why not just use threads?*
Threads work fine for CPU-bound tasks, albeit threading in Python is a little hard to get right.
For I/O bound tasks, async frameworks like asyncio allow handling many open connections with a single system call.
This makes such implementations much more efficient. Subjectively, they are also more elegant to write code for than manually dealing with threads.

### Client API
MiniKV has a simple HTTP-based API. You most likely will not use this API directly, but clients rely on it to retrieve data using the `/get` and store data using the `/put` HTTP calls.
You can also simply go to the default address `/` and it will serve you a website listing all stored entries.
Feel free to take a look at `minikv/webserver.py` to see what it does.

### Node Connections
There already is code for you in `minikv/networking` to connect with other replica and send messages between them.
This logic uses a binary protocol for efficiency, not HTTP.

What you need to know is how to interact with this code.
The networking logic will invoke callback functions defined by replication logic, which is what is located in `logic.py`, which then can handle ceratain events, such as incoming messages, or new connections.

We already give you the code that handles incoming connection. You only need to complete the `handle_message` function.
This function is supplied with three argument. The node that sent the message, the message type, and the message content.

### Client Connections
At setup, a node also spawns a webserver clients can connect to.
Whenever there is a client request, it will invoke `ChainReplication.get` and `ChainReplication.put` respectively.

We already implemented get operations, and you only need to add code to `ChainReplication.put`.

### Concurrency
In the code, there is already a `ChainReplication._update_cond` and `ChainReplication._update_lock`.
The former can be used to notify when a pending update has been processed and the latter to manage concurrent accesses to `ChainReplicatoin._pending_updates`.
If you do not remember how to use a condition variable, you can take a look at [this chapter of OSTEP](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-cv.pdf).
The book covers condition variables in C, but they behave more or less the same in Python.

There are two tests that run multiple clients concurrently.
If you do not lock while modifying the set of pending updates, your code might work fine with a single client but experience issues when there are concurent requests.

Note, that `Database` is already thread-safe, so you do not need to worry about enforcing exclusive access to it.

### Lint Checks
Lint checks are usueful to detect potential issues with your code before running it.
This is especially useful in Python as there are no compile-time checks.

The code is already set up in a way that allows running checks using [pylint](https://www.pylint.org/) and [mypy](https://mypy.readthedocs.io/en/stable/index.html).
Simply enter `make lint` and it should generate some useful output.

Note, mypy will perform type checks. You see type annotations all over the code, which is what that is for.
Python, by default, does not perform type checks, but they are useful to prevent common errors.
[Here](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html) is a good overview if you are curious, but you can also ignore type checks entirely.

### Quick Iteration
There are "quick" tests that should complete much quicker. To run them enter `make quick-test-chain-replication`.

### Cleanup
If you get errors such as `Address already in use`, the tests might not have shut down everything correctly.

First you can check is any python processes are still running with the following command.
`ps -A | grep python`
You can then terminate individual processes using `kill PID` where PID is the process identifier.

If you are in a virtual machine, or sure there are no other Python applications running, a quicker, but more agressive way, to clean up is `killall python make -9`.
This will stop *all*  all Python and Make processes currently running.

## Submission and Grading
Run `make test-chain-replication` to verify tests are passing. There are no hidden tests, if these pass and upload the zipfile correctly, you should get the full score.
Then run `make zipball` to create a zipfile and upload it to Gradscope.

If you find any error with the assignments and you are the first person to tell me, I will give you *bonus points*. So start early :)
