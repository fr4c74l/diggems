from __future__ import absolute_import
from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter()
def json_dump(data):
    return mark_safe(json.dumps(data))
