import logging
import socket
import errno
import xmlrpclib
import logging

__author__ = 'dushyant'

logger = logging.getLogger('syncIt')

def safe_rpc(fn):
    """decorator to add try/catch to rpc function calls"""
    def safe_fn(*args):
        try:
            result = fn(*args)
            if result is None:
                result = "success"

            return result
        except socket.error as e:
            if e.errno == errno.ECONNREFUSED:
                logger.critical("Problem connecting to rpc - no rpc server running. function: %s", fn.func_name)
                return None #rpc request failed
            else:
                raise
    return safe_fn

@safe_rpc
def pull_file(dest_ip, dest_port, filename, source_uname, source_ip):
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    rpc_connect.pull_file(filename, source_uname, source_ip)

@safe_rpc
def req_push_file(dest_ip, dest_port, filename, source_uname, source_ip, source_port):
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    rpc_connect.req_push_file(filename, source_uname, source_ip, source_port)

@safe_rpc
def ack_push_file(dest_ip, dest_port, filename, source_uname, source_ip, source_port):
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    rpc_connect.ack_push_file(filename, source_uname, source_ip, source_port)

@safe_rpc
def mark_presence(dest_ip, dest_port, source_ip, source_port):
    """rpc call to marks client as available"""
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    logger.debug("rpc call to mark available")
    logger.debug("available methods on rpc server %s", rpc_connect.system.listMethods())
    rpc_connect.mark_presence(source_ip, source_port)

@safe_rpc
def get_client_public_key(dest_ip, dest_port):
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    return  rpc_connect.get_public_key()

def find_available(dest_ip, dest_port):
    """rpc call to find client's rpc availability"""
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    try:
        rpc_connect.system.listMethods()
        return True
    except socket.error as e:
        if e.errno == errno.ECONNREFUSED:
            return False
        else:
            raise

