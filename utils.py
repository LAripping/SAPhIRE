import time
import re
import json
import urlparse

import global_vars
from Token import Token, IgnoredTokenException


def filter_by(fdomain):
    """
    :param fdomain: If this value is not found in the URl of any request, remove it
    """
    for e in list(global_vars.req_resp):
        u = urlparse.urlparse(e['request']['url'])
        if fdomain not in u.netloc + u.path:
            global_vars.req_resp.remove(e)
            if global_vars.debug:
                print '[+] Filtered out entry with url: %s' % u.netloc + u.path



def sort_list_of_dicts_by_key(list, dictkey):
    return sorted(list, key=lambda d: d[dictkey])



def tokenize_json(json_dict, token_type, token_time):
    """
    :param json_dict: Python object to walk
    and make a new token for every item

    :param token_type: The type for the token to create
    :param token_time: The saphireTime for the token to create

    :return The number of tokens recognized 
    """
    recognized = 0

    all_strings = []
    walk(json_dict, all_strings)                                    # break the dict
    all_strings = list(set(all_strings))                            # unique-ify
    for el in all_strings:
        if isinstance(el, bool):
            continue                                                # ignore True/False
        try:
            t = Token(token_type, token_time, ('', unicode(el)))
            t.match_and_insert(global_vars.tokens)
            recognized += 1
        except IgnoredTokenException:
            continue

    return recognized





"""
def dict_generator(indict, pre=None):
    # from this question: https://stackoverflow.com/questions/12507206/python-recommended-way-to-walk-complex-dictionary-structures-imported-from-json
    # works in ALMOST all cases... replaced by a home-made one below.
    pre = pre[:] if pre else []
    if isinstance(indict, dict):
        for key, value in indict.items():
            if isinstance(value, dict):
                for d in dict_generator(value, pre + [key]):
                    yield d
            elif isinstance(value, list) or isinstance(value, tuple):
                for v in value:
                    for d in dict_generator(v, pre + [key]):
                       yield d
            else:
                yield pre + [key, value]
    else:
        yield indict
"""




def walk(x,all_strings):
    """
    Recursive function to walk a json dict adding all Keys, Values and their Values to an array

    :param x: could be bool | u | int/float | list/tuple | dict
    :param all_strings: the array we incrementally fill with with all tokens
    """
    if isinstance(x, dict):
        for (k,v) in x.items():                                     # keys must be strings
            all_strings.append(k)
            walk(v,all_strings)
    elif isinstance(x,list) or isinstance(x,tuple):
        for el in x:
            walk(el,all_strings)
    else:
        all_strings.append(unicode(x))





def get_json(body):
    """
    Extract JSON from response body, ignoring possible JSON-hijacking defenses.
    Cases I've seen:
        - ')]}\',\n{"tags": [{"name": "Medium",...  (google)
        - "for (;;); {\"t\":\"batched\",\"bat...    (facebook)
        - "while(1);[['u',[...                      (google)
        - &&&START&&& {...                          (older google)
    and all of them work by attaching code/junk in fron of the actual object, so the proposed
    solution is to look for a JSON starting in the first 20 characters, not just the first one
    """

    for i in range(20):
        try:
            json_resp = json.loads(body[i:])
            if global_vars.debug:
                print "[+] Extracted JSON starting from pos %d: %s..." % (i, json.dumps(json_resp)[:30])
            return json_resp
        except ValueError:
            pass




def timestamp_to_hartime(ts_string):
    """
    :param ts_string: something like u'1513235543670
    :return: u'2017-11-28T20:14:53'
    """
    time_struct = time.gmtime(int(ts_string))
    return time.strftime("%Y-%m-%dT%H:%M:%S", time_struct)



def hartime_to_saphire(time_string):
    """about time:

    > time_string = "2017-11-28T20:14:53.852Z" or "2017-12-14T09:12:08.737+02:00" on Firefox HARs

    > time_struct = time.strptime( time_string.split('.')[0], "%Y-%m-%dT%H:%M:%S")
    time.struct_time(tm_year=2017, tm_mon=11, tm_mday=28, tm_hour=20, tm_min=14, tm_sec=53, tm_wday=1, tm_yday=332, tm_isdst=-1)

    > timestamp = str( time.mktime(time_struct) ).split('.')[0]
    1511892893

    > mili_re = r"[0-9]*"

    > mili = re.findall( mili_re, time_string.split('.')[1] )[0]
    852

    > float(timestamp+'.'+mili)
    1511892893.852
    """
    time_struct = time.strptime( time_string.split('.')[0], "%Y-%m-%dT%H:%M:%S")
    timestamp = str(time.mktime(time_struct)).split('.')[0]
    mili_re = r"[0-9]*"
    mili = re.findall(mili_re, time_string.split('.')[1] )[0]
    return float(timestamp+'.'+mili)
