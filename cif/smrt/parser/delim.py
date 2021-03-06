from cif.smrt.parser.pattern import Pattern
import re
from pprint import pprint


class Delim(Pattern):

    def __init__(self, *args, **kwargs):
        super(Delim, self).__init__(*args, **kwargs)

    def process(self, rule, feed, data, limit=10000000):
        cols = rule.defaults['values']

        defaults = rule.defaults

        if rule.feeds[feed].get('defaults'):
            for d in rule.feeds[feed].get('defaults'):
                defaults[d] = rule.feeds[feed]['defaults'][d]

        max = 0
        rv = []
        for l in data:
            if l == '' or self.is_comment(l):
                continue

            m = self.pattern.split(l)
            if len(cols):
                obs = defaults

                for idx, col in enumerate(cols):
                    if col is not None:
                        obs[col] = m[idx]
                obs.pop("values", None)
                rv.append(obs)

            max += 1
            if max >= limit:
                break
        return rv

Plugin = Delim