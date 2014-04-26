import random
from django import template
from django.conf import settings

register = template.Library()

class RandomAd(template.Node):
    def __init__(self, avail_ads):
        self.avail_ads = avail_ads
        self.ad_ids = avail_ads.keys()

    def render(self, context):
        try:
            used = context['_used_ad']
        except KeyError:
            used = set()
            context['_used_ad'] = used

        num_ads = len(self.ad_ids)
        chosen = random.randrange(num_ads)
        if len(used) < num_ads:
            orig_chosen = chosen
            while self.ad_ids[chosen] in used:
                chosen = (chosen + 1) % num_ads

                # this should never need to be used, but
                # I want to be sure this never gets into
                # an infinite loop
                if orig_chosen == chosen:
                    break
        chosen = self.ad_ids[chosen]
        used.add(chosen)
        return self.avail_ads[chosen]

@register.tag(name='place_ad')
def do_place_ad(parser, token):
    avail_ads = {}
    for ad in settings.ADS_IDS:
        t = template.loader.get_template('ads/{}.html'.format(ad))
        c = template.Context({'id': settings.ADS_IDS[ad]})
        avail_ads[ad] = t.render(c)
    return RandomAd(avail_ads)
