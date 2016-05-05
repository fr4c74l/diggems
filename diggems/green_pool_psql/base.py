from django.db.backends.postgresql.base import DatabaseWrapper as OrigDW
from diggems.settings import DB_POOL_MAX_CONN
from gevent.lock import Semaphore

import psycopg2.pool

# A green connection pool
class GreenConnectionPool(psycopg2.pool.AbstractConnectionPool):
    def __init__(self, minconn, maxconn, *args, **kwargs):
        self.semaphore = Semaphore(maxconn)
        psycopg2.pool.AbstractConnectionPool.__init__(self, minconn, maxconn, *args, **kwargs)

    def getconn(self):
        self.semaphore.acquire()
        conn = self._getconn()

        # Turns close into putconn
        conn.orig_close = conn.close
        conn.close = lambda : self.putconn(conn)
        return conn

    def putconn(self, conn):
        # Revert close to default behavior
        conn.close = conn.orig_close

        self._putconn(conn)
        self.semaphore.release()

    # Not sure what to do about this one...
    closeall = psycopg2.pool.AbstractConnectionPool._closeall

pools = {}

class DatabaseWrapper(OrigDW):
    def get_new_connection(self, conn_params):
        try:
            connection = self.pool.getconn()
        except AttributeError:
            global pools
            try:
                self.pool = pools[self.alias]
            except KeyError:
                self.pool = GreenConnectionPool(1, DB_POOL_MAX_CONN, **conn_params)
                pools[self.alias] = self.pool
            connection = self.pool.getconn()

        # Unfortunatelly, the following had to be copy-pasted
        # from Django's implementation
        options = self.settings_dict['OPTIONS']
        try:
            self.isolation_level = options['isolation_level']
        except KeyError:
            self.isolation_level = connection.isolation_level
        else:
            # Set the isolation level to the value from OPTIONS.
            if self.isolation_level != connection.isolation_level:
                connection.set_session(isolation_level=self.isolation_level)

        return connection
