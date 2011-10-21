# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

# Code mostly taken from:
# http://thejosephturner.com/blog/2011/03/19/https-certificate-verification-in-python-with-urllib2/

import socket
import urllib2
import httplib
import ssl

class VerifiedHTTPSConnection(httplib.HTTPSConnection):
    def connect(self):
        # overrides the version in httplib so that we do
        # certificate verification
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        # wrap the socket using verification with the root
        # certs in trusted_root_certs
        self.sock = ssl.wrap_socket(sock,
                                    self.key_file,
                                    self.cert_file,
                                    cert_reqs=ssl.CERT_REQUIRED,
                                    ca_certs='entrust_ssl_ca.cer')

# wraps https connections with ssl certificate verification
class VerifiedHTTPSHandler(urllib2.HTTPSHandler):
    def __init__(self, connection_class = VerifiedHTTPSConnection):
        self.specialized_conn_class = connection_class
        urllib2.HTTPSHandler.__init__(self)
    def https_open(self, req):
        return self.do_open(self.specialized_conn_class, req)

def secure_url_opener():
    return urllib2.build_opener(VerifiedHTTPSHandler())
