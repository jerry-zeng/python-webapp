#coding=utf-8

import config_default


def merge(defaults, overrides):
    r = {}
    for k,v in defaults.iteritems():
        if k in overrides:
            if isinstance(v, dict):
                r[k] = merge(v, overrides[k])
            else:
                r[k] = overrides[k]
        else:
            r[k] = v

configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)

except ImportError, e:
    print e


