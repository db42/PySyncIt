import logging
import threading
import time
from node import Node
from persistence import PersistentSet
import subprocess
import os
import rpc

__author__ = 'dushyant'

logger = logging.getLogger('syncIt')

class ClientData(object):
    """
    Data corresponding to each client residing in server object
    """
    def __init__(self, client_uname, client_ip, client_port):
        self.available = False
        self.mfiles = PersistentSet('server-%s.pkl'%(client_uname))
        self.uname = client_uname
        self.ip = client_ip
        self.port = client_port

class Server(Node):
    """ Server class"""
    def __init__(self, role, ip, uname, port, clients):
        super(Server, self).__init__(role, ip, port, uname)
        self.clients = clients

    def pull_file(self, filename, source_uname, source_ip):
        """pull file 'filename' from the source"""
        my_file = Node.get_dest_path(filename, self.my_uname);
        proc = subprocess.Popen(['scp', "%s@%s:%s" % (source_uname, source_ip, filename), my_file])
        return_status = proc.wait()
        logger.debug("returned status %s", return_status)

        #SERVER: Call clients to pull this file
        for client in self.clients:
            if client.ip == source_ip:
                continue
            else:
                # actual call to client to pull file
                rpc.pull_file(client.ip, client.port, filename, self.my_uname, self.my_ip)

    def update_file(self, filename, source_uname, source_ip, source_port):
        """Notify clients that this file 'filename' has been modified by the source"""
        #SERVER: Call clients to pull this file
        my_file = Node.get_dest_path(filename, self.my_uname);
        for client in self.clients:
            if (client.ip, client.port) == (source_ip, source_port):
                continue
            else:
                client.mfiles.add(my_file)
                logger.debug("add file to modified list")

    def sync_files(self):
        while True:
            try:
                time.sleep(10)
                for client in self.clients:
                    logger.debug( "list of files for client %s, availability %s",client.mfiles.list(), client.available)
                    if client.available:
                        for file in client.mfiles.list():
                            # actual call to client to pull file
                            rpc_status = rpc.pull_file(client.ip, client.port, file, self.my_uname, self.my_ip)

                            if rpc_status is None:
                                client.available = False
                                continue
                            client.mfiles.remove(file)
                            logger.debug("actual sync")
            except KeyboardInterrupt:
                break


    def mark_available(self, client_ip, client_port):
        """Mark client as available"""
        logger.debug("mark available call received")
        for client in self.clients:
            if (client_ip, client_port) == (client.ip, client.port):
                client.available = True
                logger.debug("client with ip %s, marked available", client_ip)
                #TODO (see,send) pending modified files for this client
                self.add_client_keys(client)

    def find_available_clients(self):
        for client in self.clients:
            client.available = rpc.find_available(client.ip, client.port)
            logger.debug("client marked available")
            self.add_client_keys(client)

    def get_authfile(self):
        return os.path.join("/home",self.my_uname,".ssh/authorized_keys")

    def add_client_keys(self, client):
        """ Add public keys corresponding to user """
        authfile =  self.get_authfile()
        client_pub_key = rpc.get_client_public_key(client.ip, client.port)

        if client_pub_key is None:
            return

        with open(authfile,'a+') as fp:
            if client_pub_key not in fp.readlines():
                fp.write(client_pub_key + '\n')

    def activate(self):
        """ Activate Server Node """
        sync_thread = threading.Thread(target=self.sync_files)
        sync_thread.start()
        logger.info("Thread 'syncfiles' started ")

        self.find_available_clients()
        self.start_server()

