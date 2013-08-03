from django import template
from django.utils.safestring import mark_safe
import hashlib

register = template.Library()

@register.filter()
def mugshot(profile, size=50):
    gravatar_url = "http://www.gravatar.com/avatar"
    hashid = hashlib.md5(profile.id).hexdigest()
    return ('%s/%s.jpg?d=identicon&s=%s' % (gravatar_url, hashid, size))
