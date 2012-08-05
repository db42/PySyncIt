import logging
import rpc
from pyinotify import WatchManager, ProcessEvent
import pyinotify
import subprocess
import time
import threading
import os
from Node import Node
from PersistentSet import PersistentSet

__author__ = 'dushyant'

logger = logging.getLogger('syncIt')

#Find which files to sync
class PTmp(ProcessEvent):
    """    Find which files to sync    """
    def __init__(self, mfiles, rfiles, pulledfiles):
        self.mfiles = mfiles
        self.rfiles = rfiles
        self.pulledfiles = pulledfiles

    def process_IN_CREATE(self, event):
        filename = os.path.join(event.path, event.name)
        if not self.pulledfiles.__contains__(filename):
            self.mfiles.add(filename)
            logger.info("Created file: %s" ,  filename)
        else:
            pass
            self.pulledfiles.remove(filename)

    def process_IN_DELETE(self, event):
        filename = os.path.join(event.path, event.name)
        self.rfiles.add(filename)
        try:
            self.mfiles.remove(filename)
        except KeyError:
            pass
        logger.info("Removed file: %s" , filename)

    def process_IN_MODIFY(self, event):
        filename = os.path.join(event.path, event.name)
        if not self.pulledfiles.__contains__(filename):
            self.mfiles.add(filename)
            logger.info("Modified file: %s" , filename)
        else:
            self.pulledfiles.remove(filename)

class Client(Node):
    """ Client class"""

    def __init__(self, role, ip, port, uname, watch_dirs, server):
        super(Client, self).__init__(role, ip, port, uname)
        self.server = server
        self.mfiles = PersistentSet(pkl_filename = 'client.pkl') #set() #set of modified files
        self.rfiles = set() #set of removed files
        self.pulled_files = set()
        self.watch_dirs = watch_dirs
        self.server_available = True

    def pushfile(self, filename, dest_uname, dest_ip):
        """
        push file 'filename' to the destination
        """
        dest_file = Node.getdestpath(filename, dest_uname)
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, dest_file)])
        returnStatus = proc.wait()
        logger.debug("returned status %s", returnStatus)
        #CLIENT: update the pulledfiles set
        #self.pulledfiles.add(my_file)

    def pullfile(self, filename, source_uname, source_ip):
        """
        pull file 'filename' from the source
        """
        #pull file from the client 'source'
        my_file = Node.getdestpath(filename, self.my_uname)
        #CLIENT: update the pulledfiles set
        self.pulled_files.add(my_file)
        proc = subprocess.Popen(['scp', "%s@%s:%s" % (source_uname, source_ip, filename), my_file])
        returnStatus = proc.wait()
        logger.debug("returned status %s", returnStatus)

    def getPublicKey(self):
        """
        Return public key of this client
        """
        pubKey = None
        pubKeyDirName = os.path.join("/home",self.my_uname,".ssh")
        logger.debug("public key directory %s", pubKeyDirName)
        for tuple in os.walk(pubKeyDirName):
            dirname, dirnames, filenames = tuple
            break
        logger.debug("public key dir files %s", filenames)
        for filename in filenames:

            if '.pub' in filename:
                pubKeyFilePath = os.path.join(dirname, filename)
                logger.debug("public key file %s", pubKeyFilePath)
                pubKey = open(pubKeyFilePath,'r').readline()
                logger.debug("public key %s", pubKey)

        return pubKey

    def findModified(self):
        """
        find all those files which have been modified when sync demon was not running
        """
        for directory in self.watch_dirs:
            dirwalk = os.walk(directory)

            for tuple in dirwalk:
                dirname, dirnames, filenames = tuple
                break

            for filename in filenames:
                file_path = os.path.join(dirname,filename)
                logger.debug("checked file if modified before client was running: %s", file_path)
                mtime = os.path.getmtime(file_path)
                #TODO save and restore last_synctime
                if mtime > self.mfiles.getModifiedTimestamp():
                    logger.debug("modified before client was running %s", file_path)
                    self.mfiles.add(file_path)

    #Thread to sync all modified files.
    def syncfiles(self):
        """Sync all the files present in the mfiles set and push this set"""
        mfiles = self.mfiles
        while True:
            try:
                time.sleep(10)
                for filename in mfiles.list():
                    logger.info("push file to server %s" , filename)
                    # Call the server to pull this file
                    server_uname, server_ip, server_port = self.server
                    self.pushfile(filename, server_uname, server_ip)
                    rpc.updatefile(server_ip, server_port, filename, self.my_uname, self.my_ip)
                    mfiles.remove(filename)


                self.mfiles.updateModifiedTimestamp()
            except KeyboardInterrupt:
                break

    #Thread to watch files.
    def watchfiles(self):
        wm = WatchManager()
        # watched events
        mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MODIFY
        notifier = pyinotify.Notifier(wm, PTmp(self.mfiles, self.rfiles, self.pulled_files))

        logger.debug("watched dir %s",self.watch_dirs)
        for watch_dir in self.watch_dirs:
            wm.add_watch(os.path.expanduser(watch_dir), mask, rec=False, auto_add=True)
        while True:
            try:
                time.sleep(5)
                notifier.process_events()
                if notifier.check_events():
                    notifier.read_events()
            except KeyboardInterrupt:
                notifier.stop()
                break

    def activate_client(self):
        """ Start threads to find and sync modified files """
        sync_thread = threading.Thread(target=self.syncfiles)
        sync_thread.start()
        logger.info("Thread 'syncfiles' started ")

        watch_thread = threading.Thread(target=self.watchfiles)
        watch_thread.start()
        logger.info("Thread 'watchfiles' started ")

    def activate(self):
        """ Activate Client Node """
        #Mark availability
        server_uname, server_ip, server_port = self.server

        self.activate_client()
        rpc_thread = threading.Thread(target=self.start_server)
        rpc_thread.start()
#        self.start_server()

        logger.debug("client call to mark available to the server")
        rpc.mark_available(server_ip, server_port, self.my_ip)
        logger.debug("find modified files")
        #Find Modified
        #TODO
        self.findModified()
