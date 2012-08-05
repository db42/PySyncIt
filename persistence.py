import os
import pickle
import errno
import time

__author__ = 'dushyant'


class PersistentSet(object):
    """
    override set to add persistence using pickle
    """
    def __init__(self, pkl_filename):
        self.pkl_filename = pkl_filename
        self.timestamp = None
        try:
            pkl_object = open(self.pkl_filename, 'rb')
            self.set = pickle.load(pkl_object)
        except:
            self.set = set()

    def add(self, element):
        self.set.add(element)
        pkl_object = open(self.pkl_filename, 'wb')
        pickle.dump(self.set, pkl_object)
        pkl_object.close()

    def remove(self, element):
        self.set.remove(element)
        pkl_object = open(self.pkl_filename, 'wb')
        pickle.dump(self.set, pkl_object)
        pkl_object.close()

    def list(self):
        return list(self.set)

    def get_modified_timestamp(self):
        try:
            pkl_object = open(self.pkl_filename, 'rb')
        except IOError as e:
            if e.errno == errno.ENOENT:
                return 0
            else:
                raise
        try:
            pickle.load(pkl_object)
            timestamp = pickle.load(pkl_object)
            return timestamp
        except EOFError:
            return 0
#        try:
#            return os.path.getmtime(self.pkl_filename)
#        except OSError as e:
#            if e.errno == errno.ENOENT: #file doesn't exit
#                return 0
#            else:
#                raise

    def update_modified_timestamp(self):
        """
        update last sync time
        """
        pkl_object = open(self.pkl_filename, 'wb')
        pickle.dump(self.set, pkl_object)
        #push current time
        pickle.dump(time.time, pkl_object)
        pkl_object.close()

