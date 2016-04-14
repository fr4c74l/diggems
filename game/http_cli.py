# Copyright 2013 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

import requests
from diggems.settings import MAX_REQS_CONNS

class Session(requests.Session):
    def request(self, *args, **kargs):
        r = self.request(*args, **kargs)
        r.raise_for_status()
        return r

session = Session()
session.mount('https://',
    requests.adapters.HTTPAdapter(pool_connections=2,
        pool_maxsize=MAX_REQS_CONNS))
session.mount('http://',
    requests.adapters.HTTPAdapter(pool_connections=2,
        pool_maxsize=MAX_REQS_CONNS))
