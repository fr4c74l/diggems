import os
import subprocess
import gzip
from cStringIO import StringIO

from django.contrib.staticfiles.storage import StaticFilesStorage

class NginxStaticGZIPStorage(StaticFilesStorage):
    def post_process(self, paths, **options):
        for name in paths:
            gz_name = name + '.gz'

            storage, orig_path = paths[name]
            orig_path = storage.path(name)
            gz_path = storage.path(gz_name)

            if storage.exists(gz_name):
                storage.delete(gz_name)

            # First, gzip with command line tool
            tmp_path = '/tmp' + name
            os.link(orig_path, tmp_path)
            subprocess.call(['gzip', '-9', '-f', tmp_path])
            os.rename(tmp_path, gz_path)
            cmd_size = storage.size(gz_name)

            # Then, gzip in memory
            zcontents = StringIO()
            with gzip.GzipFile(gz_name, 'wb', 9, zcontents) as gzfile:
                gzfile.write(storage.open(name).read())
            embed_size = len(zcontents.getvalue())

            # Get original size, for comparision
            orig_size = storage.size(name)

            min_size = min(orig_size, cmd_size, embed_size)
            if min_size == orig_size:
                storage.delete(gz_name)
                gzipped = False
                print 'Using original'
            elif min_size == cmd_size:
                gzipped = True
                print 'Using command line gzip'
            else:
                zcontents.seek(0)
                storage.save(gz_name, zcontents)
                gzipped = True
                print "Using python's gzip"

            yield name, gz_name, gzipped
