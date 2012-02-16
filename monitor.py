import os
from pyinotify import WatchManager, Notifier, ThreadedNotifier, EventsCodes, ProcessEvent
import pyinotify
import subprocess
import re
import time
import threading
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import argparse
import logging
import ConfigParser

SERVER_IP = '10.22.254.60' 
SERVER_UNAME = 'user'
SERVERS = [(SERVER_UNAME, SERVER_IP)]

WATCH_DIR = '~/projects'
KEYSFILE = '~/.ssh/authorized_keys'
CLIENTS = [('dushyant','10.22.6.111'), ('dushyant','10.192.15.205')]

#Find which files to sync
class PTmp(ProcessEvent):
    """ Find which files to sync """
    def __init__(self, mfiles, rfiles, pulledfiles):
        self.mfiles = mfiles
        self.rfiles = rfiles
        self.pulledfiles = pulledfiles
        
    def process_IN_CREATE(self, event):
        filename = os.path.join(event.path, event.name)
        if not self.pulledfiles.__contains__(filename):
            self.mfiles.add(filename)
            print "Create: %s" %  filename
        else:
            pass
            #self.pulledfiles.remove(filename)


    def process_IN_DELETE(self, event):
        filename = os.path.join(event.path, event.name)
        self.rfiles.add(filename)
        try:
            self.mfiles.remove(filename)
        except KeyError:
            pass 
        print "Remove: %s" %  filename
    
    def process_IN_MODIFY(self, event):
        filename = os.path.join(event.path, event.name)
        if not self.pulledfiles.__contains__(filename):
            self.mfiles.add(filename)
            print "Modify: %s" % filename
        else:
            self.pulledfiles.remove(filename)
        

class Node(object):
    """Base class for client and server"""
    
    def __init__(self, role , ip, uname):
        self.role = role
        self.my_ip = ip
        self.my_uname = uname
        
    @staticmethod
    def getdestpath(filename, dest_uname):
        p = re.compile("(/home/[a-z]*/)")
        
#        if (src_role == 'client'):
#            destpath = p.sub(SERVER_PATH, filename)
#        else:
#            destpath = p.sub("/home/%s/" % dest_uname, filename)
        destpath = p.sub("/home/%s/" % dest_uname, filename)
        print destpath
        return destpath

    @staticmethod
    def rpc_pullfile(dest_ip, filename, source_uname, source_ip):
        rpc_connect = xmlrpclib.ServerProxy("http://%s:8000/"% dest_ip, allow_none = True)
        rpc_connect.pullfile(filename, source_uname, source_ip)
    
    @staticmethod
    def rpc_updatefile(dest_ip, filename, source_uname, source_ip):
        rpc_connect = xmlrpclib.ServerProxy("http://%s:8000/"% dest_ip, allow_none = True)
        rpc_connect.updatefile(filename, source_uname, source_ip)
            
    @staticmethod        
    def pushfile(filename, dest_uname, dest_ip):
        """push file 'filename' to the destination """
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, Node.getdestpath(filename, dest_uname))])
        print proc.wait()

    def start_server(self):
        """ Start RPC Server on each node """
        server = SimpleXMLRPCServer(("0.0.0.0", 8000), allow_none =True)
        print "Started RPC server. Listening on port 8000..."
        server.register_instance(self)
        server.serve_forever()

class Server(Node):
    """ Server class"""
    
    def __init__(self, role, ip, uname, clients):
        super(Server, self).__init__(role, ip, uname)
        self.clients = clients
    
    def pullfile(self, filename, source_uname, source_ip):
        """pull file 'filename' from the source"""
        #pull file from the client 'source'
        my_file = Node.getdestpath(filename, self.my_uname);
        proc = subprocess.Popen(['scp', "%s@%s:%s" % (source_uname, source_ip, filename), my_file])
        print proc.wait()
        
        #SERVER: Call clients to pull this file
        for (client_uname, client_ip) in CLIENTS:
            if client_ip == source_ip:
                continue
            else:
                # actual call to client to pull file
                Node.rpc_pullfile(client_ip, filename, self.my_uname, self.my_ip)

    def updatefile(self, filename, source_uname, source_ip):
        """Notify clients that this file 'filename' has been modified by the source"""
        #SERVER: Call clients to pull this file
        my_file = Node.getdestpath(filename, self.my_uname);
        for (client_uname, client_ip) in self.clients:
            if client_ip == source_ip:
                continue
            else:
                # actual call to client to pull file
                Node.rpc_pullfile(client_ip, my_file, self.my_uname, self.my_ip)
    
    @staticmethod
    def addKey(user):
        """ Add public keys corresponding to user """
        authfile = os.path.expanduser(KEYSFILE)
        clientkeyfile = user + '.pub'
        
        with open(clientkeyfile, 'r') as fp:
            clientkey = fp.readline()
            
        with open(authfile,'a+') as fp:
            if clientkey not in fp.readlines():
                fp.write(clientkey + '\n')

    def activate(self):
        """ Activate Server Node """
        self.start_server()
    
class Client(Node):
    """ Client class"""
    
    def __init__(self, role, ip, uname, server):
        super(Client, self).__init__(role, ip, uname)
        self.server = server
        self.mfiles = set() #set of modified files
        self.rfiles = set() #set of removed files
        self.pulledfiles = set()
    
    def pushfile(self, filename, dest_uname, dest_ip):
        """push file 'filename' to the destination"""
        #pull file from the client 'source'
        dest_file = Node.getdestpath(filename, dest_uname)
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, dest_file)])
        print proc.wait()
        #CLIENT: update the pulledfiles set
        #self.pulledfiles.add(my_file)
        
    def pullfile(self, filename, source_uname, source_ip):
        """pull file 'filename' from the source"""
        #pull file from the client 'source'
        my_file = Node.getdestpath(filename, self.my_uname)
        #CLIENT: update the pulledfiles set
        self.pulledfiles.add(my_file)
        proc = subprocess.Popen(['scp', "%s@%s:%s" % (source_uname, source_ip, filename), my_file])
        print proc.wait()


    #Thread to sync all modified files.
    def syncfiles(self):
        """Sync all the files present in the mfiles set and pulled this set"""
        mfiles = self.mfiles
        while True:
            try:
                time.sleep(10)
                for filename in list(mfiles):
                    print filename
                    # Call the server to pull this file
                    server_uname, server_ip = self.server
                    self.pushfile(filename, server_uname, server_ip)
                    Node.rpc_updatefile(server_ip, filename, self.my_uname, self.my_ip)
                    mfiles.remove(filename)
            except KeyboardInterrupt:
                break
            
    #Thread to watch files.
    def watchfiles(self):
        wm = WatchManager()
        # watched events
        mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MODIFY 
        notifier = pyinotify.Notifier(wm, PTmp(self.mfiles, self.rfiles, self.pulledfiles))
    
        wdd = wm.add_watch(os.path.expanduser(WATCH_DIR), mask, rec=False, auto_add=True)
        while True:
            try:
                time.sleep(5)
                notifier.process_events()
                if notifier.check_events():
                    notifier.read_events()
            except KeyboardInterrupt:
                notifier.stop()
                break
        print self.mfiles

    def activate_client(self):
        """ Start threads to find and sync modified files """
        sync_thread = threading.Thread(target=self.syncfiles)
        sync_thread.start()
        print "Thread 'syncfiles' started "
        
        watch_thread = threading.Thread(target=self.watchfiles)
        watch_thread.start()
        print "Thread 'watchfiles' started "
        
    def activate(self):
        """ Activate Client Node """
        self.activate_client()
        self.start_server()
                    
def main():
    #use argparse to get role, ip, uname
    parser = argparse.ArgumentParser(
        description="""SyncIT""",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument(
        '-ip', help='Specify the ipaddr of this machine')
    
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
    
    if (args.role == 'server'):
        clients = []
        for key, value in config.items('syncit.clients'):
            client_uname, client_ip = value.split(',') 
            clients.append((client_uname, client_ip))
            Server.addKey(client_uname)
        node = Server(args.role, ip = args.ip, uname = args.uname, clients = clients)
    else:
        server_uname, server_ip = config.get('syncit.server', 'server', 1).split(',')    
        node = Client(args.role, ip = args.ip, uname = args.uname, server = (server_uname, server_ip))
    node.activate()
    
if __name__ == "__main__":
    main()
