from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import logging
import os
import re
import subprocess
import threading

__author__ = 'dushyant'

logger = logging.getLogger('syncIt')

class Handler(SimpleXMLRPCRequestHandler):
    def _dispatch(self, method, params):
        try:
            print self.server.funcs.items()
            return self.server.funcs[method](*params)
        except:
            import traceback
            traceback.print_exc()
            raise

class Node(object):
    """Base class for client and server"""

    def __init__(self, role , ip, port, uname, watch_dirs):
        self.role = role
        self.my_ip = ip
        self.port = port
        self.my_uname = uname
        self.watch_dirs = watch_dirs

    @staticmethod
    def get_dest_path(filename, dest_uname):
        p = re.compile("(/home/[a-z]*/)")

        destpath = p.sub("/home/%s/" % dest_uname, filename)
        logger.debug("destpath %s" + destpath)
        return destpath


    @staticmethod
    def push_file(filename, dest_uname, dest_ip):
        """push file 'filename' to the destination """
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, Node.get_dest_path(filename, dest_uname))])
        return_status = proc.wait()
        logger.debug("returned status %s",return_status)

    def ensure_dir(self):
        """create directories to be synced if not exist"""
        user_name = self.my_uname
        for dir in self.watch_dirs:
            my_dir = Node.get_dest_path(dir, user_name)
            if not os.path.isdir(my_dir):
                os.makedirs(my_dir)

    def start_server(self):
        """Start RPC Server on each node """
        server = SimpleXMLRPCServer(("0.0.0.0", self.port), allow_none =True)
        server.register_instance(self)
        server.register_introspection_functions()
        rpc_thread = threading.Thread(target=server.serve_forever)
        rpc_thread.start()
        logger.debug("server functions on rpc %s", server.funcs.items())
        logger.info("Started RPC server thread. Listening on port %s..." , self.port)


    def start_sync_thread(self):
        sync_thread = threading.Thread(target=self.sync_files)
        sync_thread.start()
        logger.info("Thread 'syncfiles' started ")

    def activate(self):
        self.ensure_dir()
        self.start_sync_thread()
        self.start_server()

