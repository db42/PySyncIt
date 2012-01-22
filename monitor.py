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

CLIENTS = [('dushyant','10.22.6.111'), ('dushyant','10.192.15.205')]

#Find which files to sync
class PTmp(ProcessEvent):
    """ Find which files to sync """
    def __init__(self, mfiles, rfiles, updatedfiles):
        self.mfiles = mfiles
        self.rfiles = rfiles
        self.updatedfiles = updatedfiles
        
    def process_IN_CREATE(self, event):
        filename = os.path.join(event.path, event.name)
        self.mfiles.add(filename)
        print "Create: %s" %  filename

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
        if not self.updatedfiles.__contains__(filename):
            self.mfiles.add(filename)
            print "Modify: %s" % filename
        else:
            self.updatedfiles.remove(filename)
        

class Node(object):
    """Base class for client and server"""
    
    def __init__(self, role , ip, uname):
        self.mfiles = set() #set of modified files
        self.rfiles = set() #set of removed files
        self.updatedfiles = set()
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
    
#    def pushfile(self, filename, server_uname, server_ip):
#        """push file 'filename' to the destination machines"""
#        if (self.role == 'client'):
#            destinations = SERVERS
#        else:
#            destinations = CLIENTS
#
#        for (dest_uname, dest_ip) in destinations:
#            proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, Node.getdestpath(filename, dest_uname))])
#            print proc.wait()

    def pushfile(self, filename, dest_uname, dest_ip):
        """push file 'filename' to the destination """
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, Node.getdestpath(filename, dest_uname))])
        print proc.wait()
    
    def pullfile(self, filename, source_uname, source_ip):
        """pull file 'filename' from the source"""
        #pull file from the client 'source'
        my_file = Node.getdestpath(filename, self.my_uname);
        proc = subprocess.Popen(['scp', "%s@%s:%s" % (source_uname, source_ip, filename), my_file])
        print proc.wait()
        
        if self.role=='server':
        #SERVER: push file to other clients
            for (client_uname, client_ip) in CLIENTS:
                if client_ip == source_ip:
                    continue
                else:
                    #call client pull file
                    proxy = xmlrpclib.ServerProxy("http://%s:8000/"% client_ip, allow_none = True)
                    proxy.pullfile(filename, self.my_uname, self.my_ip)
                    #self.pushfile(my_file, client_uname, client_ip)
        else:
        #CLIENT:
            self.updatefiles.add(my_file) 
        
    #Thread 1    
    def syncfiles(self):
        """Sync all the files present in the mfiles set and update this set"""
        mfiles = self.mfiles
        print "sync"
        while True:
            try:
                time.sleep(10)
                for filename in list(mfiles):
                    print filename
                    #Push this modified file to the server using scp or rsync
                    proxy = xmlrpclib.ServerProxy("http://%s:8000/"% SERVER_IP, allow_none = True)
                    proxy.pullfile(filename, self.my_uname, self.my_ip)

#                    self.pushfile(filename, SERVER_UNAME, SERVER_IP)
                    mfiles.remove(filename)
            except KeyboardInterrupt:
                break
            
    #Thread 2
    def watchfiles(self):
        wm = WatchManager()
        # watched events
        mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MODIFY 
        notifier = pyinotify.Notifier(wm, PTmp(self.mfiles, self.rfiles, self.updatedfiles))
    
        wdd = wm.add_watch('/home/dushyant/projects', mask, rec=False, auto_add=True)
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
        
    def start(self):
        thread2 = threading.Thread(target=self.syncfiles)
#        thread2.daemon = True
        thread2.start()
        print "Thread 'syncfiles' started "
        
        thread1 = threading.Thread(target=self.watchfiles)
#        thread1.daemon = True
        thread1.start()
        print "Thread 'watchfiles' started "
        
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
    
    logger.log('Logging started')
    
    node = Node(args.role, ip = args.ip, uname = args.uname)
    
    if (node.role == 'client'):
        #CLIENT will start watch and sync demons
        node.start()

    #Each node will start RPC Server
    server = SimpleXMLRPCServer(("0.0.0.0", 8000), allow_none =True)
    logger.info("Listening on port 8000...")
    server.register_instance(node)
    server.serve_forever()
    
#    print "started 1"
#    thread2 = threading.Thread(target=fun2)
##    thread2.daemon = True
#    thread2.start()
#    print "started 2"
#    thread1 = threading.Thread(target=node.watchfiles())
##    thread1.daemon = True
#    thread1.start()

if __name__ == "__main__":
    main()
