# Copyright 2011 Lucas Clemente Vella
# Software under Affero GPL license, see LICENSE.txt

FB_APP_ID = '264111940275149'

def fb_stuff(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    return {'FB_APP_ID': FB_APP_ID,
            'PROTOCOL': protocol}
