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

    def pullfile(self, filename, source_uname, source_ip):
        """pull file 'filename' from the source"""
        my_file = Node.getdestpath(filename, self.my_uname);
        proc = subprocess.Popen(['scp', "%s@%s:%s" % (source_uname, source_ip, filename), my_file])
        returnStatus = proc.wait()
        logger.debug("returned status %s", returnStatus)

        #SERVER: Call clients to pull this file
        for client in self.clients:
            if client.ip == source_ip:
                continue
            else:
                # actual call to client to pull file
                rpc.pullfile(client.ip, client.port, filename, self.my_uname, self.my_ip)

    def updatefile(self, filename, source_uname, source_ip):
        """Notify clients that this file 'filename' has been modified by the source"""
        #SERVER: Call clients to pull this file
        my_file = Node.getdestpath(filename, self.my_uname);
        for client in self.clients:
            if client.ip == source_ip:
                continue
            else:
                client.mfiles.add(my_file)
                logger.debug("add file to modified list")

    def syncFiles(self):
        while True:
            try:
                time.sleep(10)
                for client in self.clients:
                    logger.debug( "list of files for client %s, availability %s",client.mfiles.list(), client.available)
                    if client.available:
                        for file in client.mfiles.list():
                            # actual call to client to pull file
                            rpc.pullfile(client.ip, client.port, file, self.my_uname, self.my_ip)
                            client.mfiles.remove(file)
                            logger.debug("actual sync")
            except KeyboardInterrupt:
                break


    def mark_available(self, client_ip):
        """Mark client as available"""
        logger.debug("mark available call received")
        for client in self.clients:
            if client_ip == client.ip:
                client.available = True
                logger.debug("client with ip %s, marked available", client_ip)
                #TODO (see,send) pending modified files for this client
                self.addClientKeys(client)

    def findAvailable(self):
        for client in self.clients:
            client.available = rpc.findAvailable(client.ip, client.port)
            logger.debug("client marked available")
            self.addClientKeys(client)

    def getAuthFile(self):
        return os.path.join("/home",self.my_uname,".ssh/authorized_keys")

    def addClientKeys(self, client):
        """ Add public keys corresponding to user """
        authfile =  self.getAuthFile()
        clientPublicKey = rpc.getClientPublicKey(client.ip, client.port)

        if clientPublicKey is None:
            return

        with open(authfile,'a+') as fp:
            if clientPublicKey not in fp.readlines():
                fp.write(clientPublicKey + '\n')

    def activate(self):
        """ Activate Server Node """
        sync_thread = threading.Thread(target=self.syncFiles)
        sync_thread.start()
        logger.info("Thread 'syncfiles' started ")

        self.findAvailable()
        self.start_server()

