# Copyright 2013 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

from geventhttpclient import HTTPClient

_pool = {}

def get_conn(base_url):
    try:
        return _pool[base_url]
    except KeyError:
        cli = HTTPClient.from_url(base_url, ssl_options=dict(ssl_version=ssl.PROTOCOL_TLSv1), connection_timeout=60, network_timeout=60, concurrency=5)
        _pool[base_url] = cli
        return cli
