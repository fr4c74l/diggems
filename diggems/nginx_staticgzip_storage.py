import os
import os.path
import subprocess
import gzip
import traceback
from cStringIO import StringIO

from django.contrib.staticfiles.storage import StaticFilesStorage
from django.core.files.base import ContentFile

class NginxStaticGZIPStorage(StaticFilesStorage):
    def post_process(self, paths, **options):
        for name in paths:
            gz_name = name + '.gz'

            try:
                if self.exists(gz_name):
                    if self.modified_time(gz_name) >= self.modified_time(name):
                        continue

                orig_path = self.path(name)
                gz_path = self.path(gz_name)

                if self.exists(gz_name):
                    self.delete(gz_name)

                # First, gzip with command line tool
                tmp_path = os.path.basename(name)
                os.link(orig_path, tmp_path)
                subprocess.call(['gzip', '-9', '-f', tmp_path])
                os.rename(tmp_path + '.gz', gz_path)
                cmd_size = self.size(gz_name)

                # Then, gzip in memory
                zcontents = StringIO()
                gz_filename = os.path.basename(gz_name).encode('utf-8')
                with gzip.GzipFile(gz_filename, 'wb', 9, zcontents) as gzfile:
                    gzfile.write(self.open(name, 'rb').read())
                zcontents = zcontents.getvalue()
                embed_size = len(zcontents)

                # Get original size, for comparision
                orig_size = self.size(name)

                print '"name" -', 'orig size:', orig_size, 'external gzip size:', cmd_size, 'internal gzip size:', embed_size
                min_size = min(orig_size, cmd_size, embed_size)
                if min_size == orig_size:
                    print ' Using original'
                    self.delete(gz_name)
                    gzipped = False
                elif min_size == cmd_size:
                    print ' Using command line gzip'
                    gzipped = True
                else:
                    print " Using python's gzip"
                    self.delete(gz_name)
                    self.save(gz_name, ContentFile(zcontents))
                    subprocess.call(['touch', '-r', orig_path, gz_path])
                    gzipped = True
            except:
                traceback.print_exc()
                raise

            yield name, gz_name, gzipped
