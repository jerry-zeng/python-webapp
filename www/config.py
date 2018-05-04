#coding=utf-8

class Dict(dict):
    def __init__(self, keys=(), values=(), **kw):
        super(Dict, self).__init__(**kw)

        for k,v in zip(keys, values):
            self[k] = v


    def __getattr__(self, key):
        try:
            return self[key]
        except:
            return None

    def __setattr__(self, key, value):
        self[key] = value

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

    return r

def toDict(config):
    d = Dict()

    for k, v in config.iteritems():
        if isinstance(v, dict):
            d[k] = toDict(v)
        else:
            d[k] = v

    return d

def load():
    import config_default
    configs = config_default.configs

    try:
        import config_override
        configs = merge(configs, config_override.configs)

    except ImportError, e:
        print e

    configs = toDict(configs)

    return configs


configs = load()
