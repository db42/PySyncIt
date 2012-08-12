import argparse
import logging
import ConfigParser
import os
from node import Node

from server import Server, ClientData
from client import Client

logger = logging.getLogger('syncIt')

def setup_logging():
#    handler = logging.FileHandler('syncIt.log')
    handler = logging.StreamHandler()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def get_watch_dirs(config, user_name):
    watch_dirs = []
    for key, value in config.items('syncit.dirs'):
        dir = os.path.expanduser(value)
        my_dir = Node.get_dest_path(dir, user_name)
        watch_dirs.append(my_dir)
    logger.debug("watched dirs %s", watch_dirs)
    return watch_dirs


def get_clients(config):
    clients = []
    for key, value in config.items('syncit.clients'):
        client_uname, client_ip, client_port = value.split(',')
        clients.append(ClientData(client_uname, client_ip, int(client_port)))
    return clients


def get_server_tuple(config):
    server_uname, server_ip, server_port = config.get('syncit.server', 'server', 1).split(',')
    return (server_uname, server_ip, server_port)


def main():
    #use argparse to get role, ip, port and user name
    parser = argparse.ArgumentParser(
        description="""PySyncIt""",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument(
        '-ip', help='Specify the ip address of this machine')

    parser.add_argument(
        '-port', help='Specify the port of this machine to run rpc server')

    parser.add_argument(
        '-uname', help='Specify the user name of this machine')
    
    parser.add_argument(
        '-role', help='Specify the role of this machine - client or server')
    
    args = parser.parse_args()

    #start logging
    setup_logging()
    logger = logging.getLogger('syncIt')
    logger.info('Logging started')

    #Read config file
    config = ConfigParser.ConfigParser()
    config.read('syncit.cfg')

    if (args.role == 'server'):
        node = Server(args.role, args.ip, int(args.port), args.uname, get_watch_dirs(config, args.uname), get_clients(config))
    else:
        node = Client(args.role, args.ip, int(args.port), args.uname, get_watch_dirs(config, args.uname), get_server_tuple(config))

    node.activate()
    
if __name__ == "__main__":
    main()
