import logging
import rpc
from pyinotify import WatchManager, ProcessEvent
import pyinotify
import subprocess
import time
import threading
import os
from node import Node
from persistence import PersistentSet

__author__ = 'dushyant'

logger = logging.getLogger('syncIt')

#Find which files to sync
class PTmp(ProcessEvent):
    """    Find which files to sync    """
    def __init__(self, mfiles, rfiles, pulledfiles):
        self.mfiles = mfiles
        self.rfiles = rfiles
        self.pulled_files = pulledfiles

    def process_IN_CREATE(self, event):
        filename = os.path.join(event.path, event.name)
        if not self.pulled_files.__contains__(filename):
            self.mfiles.add(filename)
            logger.info("Created file: %s" ,  filename)
        else:
            pass
            self.pulled_files.remove(filename)

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
        if not self.pulled_files.__contains__(filename):
            self.mfiles.add(filename)
            logger.info("Modified file: %s" , filename)
        else:
            self.pulled_files.remove(filename)

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

    def push_file(self, filename, dest_uname, dest_ip):
        """
        push file 'filename' to the destination
        """
        dest_file = Node.get_dest_path(filename, dest_uname)
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, dest_file)])
        return_status = proc.wait()
        logger.debug("returned status %s", return_status)
        #CLIENT: update the pulledfiles set
        #self.pulledfiles.add(my_file)

    def pull_file(self, filename, source_uname, source_ip):
        """
        pull file 'filename' from the source
        """
        #pull file from the client 'source'
        my_file = Node.get_dest_path(filename, self.my_uname)
        #CLIENT: update the pulledfiles set
        self.pulled_files.add(my_file)
        proc = subprocess.Popen(['scp', "%s@%s:%s" % (source_uname, source_ip, filename), my_file])
        return_status = proc.wait()
        logger.debug("returned status %s", return_status)

    def get_public_key(self):
        """
        Return public key of this client
        """
        pubkey = None
        pubkey_dirname = os.path.join("/home",self.my_uname,".ssh")
        logger.debug("public key directory %s", pubkey_dirname)
        for tuple in os.walk(pubkey_dirname):
            dirname, dirnames, filenames = tuple
            break
        logger.debug("public key dir files %s", filenames)
        for filename in filenames:

            if '.pub' in filename:
                pubkey_filepath = os.path.join(dirname, filename)
                logger.debug("public key file %s", pubkey_filepath)
                pubkey = open(pubkey_filepath,'r').readline()
                logger.debug("public key %s", pubkey)

        return pubkey

    def find_modified(self):
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
                if mtime > self.mfiles.get_modified_timestamp():
                    logger.debug("modified before client was running %s", file_path)
                    self.mfiles.add(file_path)

    #Thread to sync all modified files.
    def sync_files(self):
        """Sync all the files present in the mfiles set and push this set"""
        mfiles = self.mfiles
        while True:
            try:
                time.sleep(10)
                for filename in mfiles.list():
                    logger.info("push file to server %s" , filename)
                    # Call the server to pull this file
                    server_uname, server_ip, server_port = self.server
                    self.push_file(filename, server_uname, server_ip)
                    rpc.update_file(server_ip, server_port, filename, self.my_uname, self.my_ip, self.port)
                    mfiles.remove(filename)


                self.mfiles.update_modified_timestamp()
            except KeyboardInterrupt:
                break

    #Thread to watch files.
    def watch_files(self):
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
        sync_thread = threading.Thread(target=self.sync_files)
        sync_thread.start()
        logger.info("Thread 'syncfiles' started ")

        watch_thread = threading.Thread(target=self.watch_files)
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
        rpc.mark_available(server_ip, server_port, self.my_ip, self.port)
        logger.debug("find modified files")
        #Find Modified
        #TODO
        self.find_modified()
