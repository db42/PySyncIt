# PySyncIt

PySyncIt is a simple tool to keep folders in sync between machines connected on a network.

## Running PySyncIt

PySyncIt is written only for Linux.

### Dependency

All you need is python installed on your system and you are ready to go. However, there may be some python modules that you need to install.

External Python Modules:

```
pyinotify
```

### Running

1. Setting up configuration file:
A sample configuration file has been provided to set various parameters (username and ip address) of server and client machines.

2. Copy public keys of clients to server machine. Name the key file corresponding to a client machine with username <user1> as <user1.pub> and keep that file in the same PySyncIt folder.

3. Run Monitor.py
#### Client

```
python monitor.py -ip 10.192.168.2 -uname user2 -role client
```

#### Server

```
python monitor.py -ip 10.192.168.1 -uname user1 -role server
```
