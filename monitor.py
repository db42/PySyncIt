import argparse
import logging
import ConfigParser
import os

from Server import Server, ClientData
from Client import Client

class FileData(object):
    def __init__(self, file_name, time, owner):
        self.name = file_name
        self.time = time
        self.owner = owner


def ensure_dir(dirs):
    """
    create directories to be synced if not exist
    """
    for dir in dirs:
        if not os.path.isdir(dir):
            os.makedirs(dir)

def main():
    #use argparse to get role, ip, uname
    parser = argparse.ArgumentParser(
        description="""SyncIT""",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument(
        '-ip', help='Specify the ipaddr of this machine')

    parser.add_argument(
        '-port', help='Specify the port of this machine')

    parser.add_argument(
        '-uname', help='Specify the user name of this machine')
    
    parser.add_argument(
        '-role', help='Specify the role of this machine')
    
    args = parser.parse_args()
    
    #Start Logging
    logger = logging.getLogger('syncIt')
    #handler = logging.FileHandler('/tmp/syncIt.log')
    handler = logging.StreamHandler()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info('Logging started')

    config = ConfigParser.ConfigParser()
    config.read('syncit.cfg')

    #Get dirs to watch
    watch_dirs = []
    for key, value in config.items('syncit.dirs'):
        print value
        watch_dirs.append(os.path.expanduser(value))

    ensure_dir(watch_dirs)
    print "dirs " ,watch_dirs
    #TODO try to remove if-else using OO
    if (args.role == 'server'):
        clients = []
        for key, value in config.items('syncit.clients'):
            client_uname, client_ip, client_port = value.split(',')
            clients.append(ClientData(client_uname, client_ip, client_port))
        node = Server(args.role, ip = args.ip, port = args.port, uname = args.uname, clients = clients)
    else:

        server_uname, server_ip, server_port = config.get('syncit.server', 'server', 1).split(',')
        node = Client(role = args.role, ip = args.ip, port = args.port, uname = args.uname, watch_dirs=watch_dirs, server = (server_uname, server_ip, server_port))
    node.activate()
    
if __name__ == "__main__":
    main()
