import socket
import errno
import xmlrpclib

__author__ = 'dushyant'

def safeRPC(fn):
    def saveFn(*args):
        """
        decorator to add try/catch to rpc function calls
        """
        try:
            fn(*args)
        except socket.error as e:
            if e.errno == errno.ECONNREFUSED:
                print "Problem connecting to rpc - no rpc server running. function:", fn.func_name
            else:
                raise

    return saveFn

@safeRPC
def pullfile(dest_ip, dest_port, filename, source_uname, source_ip):
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    rpc_connect.pullfile(filename, source_uname, source_ip)

@safeRPC
def updatefile(dest_ip, dest_port, filename, source_uname, source_ip):
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    print filename + source_ip + source_uname
    print rpc_connect.system.listMethods()
    rpc_connect.updatefile(filename, source_uname, source_ip)

@safeRPC
def mark_available(dest_ip, dest_port, source_ip):
    """
    rpc call to marks client as available
    """
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    print "rpc call to mark available"
    print rpc_connect.system.listMethods()
    rpc_connect.mark_available(source_ip)


def findAvailable(dest_ip, dest_port):
    """
    rpc call to find client's rpc availability
    """
    rpc_connect = xmlrpclib.ServerProxy("http://%s:%s/"% (dest_ip, dest_port), allow_none = True)
    try:
        rpc_connect.system.listMethods()
        return True
    except socket.error as e:
        if e.errno == errno.ECONNREFUSED:
            return False
        else:
            raise

