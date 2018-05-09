#coding=utf-8

import time, datetime, re

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


_TIMEDELTA_ZERO = datetime.timedelta(0)

# timezone as UTC+8:00, UTC-10:00

_REG_TIME_ZONE = re.compile("^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$")

class UTC(datetime.tzinfo):
    def __init__(self, utc):
        utc = str( utc.strip().upper() )
        mt = _REG_TIME_ZONE.match(utc)
        if mt:
            minus = mt.group(1) == "-"
            hour = int( mt.group(2) )
            min = int( mt.group(3) )
            if minus:
                hour = -hour
                min = -min

            self._utcOffset = datetime.timedelta(hours=hour, minutes=min)
            self._tzname = "UTC%s" % utc

        else:
            raise ValueError('bad utc time zone')

    def utcoffset(self, dt):
        return self._utcOffset

    def tzname(self, dt):
        return self._tzname

    def dst(self, dt):
        return _TIMEDELTA_ZERO

    def __str__(self):
        return "UTC tzinfo (%s)" % self._tzname

    __repr__ = __str__
