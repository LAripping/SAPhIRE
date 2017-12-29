#!/usr/bin/python
#encoding=utf8

import base64
import json
import urllib
import urlparse
import termcolor
import os
import string
import re
import argparse
import time
import bs4
import unicodedata
import enchant
import enchant.tokenize
import pprint
import StringIO




def isolate_requests(har_file):
    global req_resp, debug, harfile_pagetime

    har = {}
    with open(har_file) as harfile:
        har = json.load( harfile )

    harfile_pagetime = har['log']['pages'][0]['startedDateTime']    # needed later on

    req_resp = har['log']['entries']
    if debug:
        print "[+] Read %d entries" % len(req_resp)

    fdomain = raw_input("Filter by domain? (ENTER for no): ")
    if fdomain:
        for e in list(req_resp):                                    # iterating over a copy
            u = urlparse.urlparse(e['request']['url'])
            if fdomain not in u.netloc+u.path:
                req_resp.remove(e)
                if debug: 
                    print '[+] Filtered out entry with url: %s' % u.netloc+u.path



    no_data = raw_input("Ignore media/fonts/css/... junk? (Y/n): ")
    if no_data in ["", "y", "Y"]:
        junk_ext = [".ttf", ".woff", ".otf", ".eot",                # fonts
                    ".css", ".sass",                                # styles
                    ".img", ".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif", ".bmp", ".ico",
                    ".pdf",                                         # img / doc
                    ]                                               # media
        junk_ext += [ j.upper() for j in junk_ext ]                 # ...and .JPG has been seen


        for e in list(req_resp):
            if 'data:' in e['request']['url']:
                req_resp.remove(e)
                if debug: 
                    print '[+] Ingoring entry with url: '+ e['request']['url']
                continue

            for j in junk_ext:
                if j in e['request']['url']:
                    req_resp.remove(e)
                    if debug: 
                        print '[+] Ingoring entry with url: '+ e['request']['url']

    return






def dict_generator(indict, pre=None):
    # from this question: https://stackoverflow.com/questions/12507206/python-recommended-way-to-walk-complex-dictionary-structures-imported-from-json
    # works in ALMOST all cases... replaced by a home-made one.
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



def walk(x,all_strings):
    """
    Recursive function to walk a json dict adding all Keys, Values and their Values to an array

    :param x: could be bool | u | int/float | list/tuple | dict
    :param all_strings: the array we incrementally fill with with all tokens
    """
    if isinstance(x, dict):
        for (k,v) in x.items():
            # keys must be strings
            all_strings.append(k)
            walk(v,all_strings)
    elif isinstance(x,list) or isinstance(x,tuple):
        for el in x:
            walk(el,all_strings)
    else:
        all_strings.append(unicode(x))







def recognize_tokens():
    global req_resp, tokens, colors, debug

    if debug: 
        print "[+] %d Entries in for token recognition" % len(req_resp)
        
    common_headers = []
    with open('common_headers.txt') as infile:
        for line in infile:
            common_headers.append( line.lower().replace('\n','') if '#' not in line else None )
        if debug:
            print "[+] Read in "+str(len(common_headers))+' common headers to ignore'

    for e in req_resp:
        recognized = 0

        try:
            ###### url params
            for p in e['request']['queryString']:
                t = Token('url', e['saphireTime'], (p['name'],p['value'])  )
                t.match_and_insert(tokens)
                recognized += 1
        except KeyError:
            pass

        try:
            ###### cookies
            if e['request']['cookies'] != []:
                for c in e['request']['cookies']:
                    t = Token('cookie', e['saphireTime'], (c['name'],c['value']) )
                    t.match_and_insert(tokens)
                    recognized += 1
            else:                                                   # check the header
                cookie_string = [ h['value'] for h in e['request']['headers'] if h['name'].lower()=='cookie' ][0]
                for c in cookie_string.split('; '):
                    t = Token('cookie', e['saphireTime'], (c.split('=')[0] ,c.split('=')[1]) )
                    t.match_and_insert(tokens)
                    recognized += 1
        except KeyError:
            pass
        except IndexError:
            pass

        try:
            ###### form fields
            if e['request']['method'] == 'POST':
                header_values = [ h['value'] for h in e['response']['headers']]
                for v in header_values:
                    if 'application/x-www-form-urlencoded' in v:    # TODO what about application/form-multipart
                        if e['request']['postData']['params'] != []:
                            for f in e['request']['postData']['params']:
                                t = Token('form', e['saphireTime'], (f['name'],f['value']) )
                                t.match_and_insert(tokens)
                                recognized += 1
                        else:
                            for f in e['request']['postData']['text'].split('&'):
                                t = Token('form', e['saphireTime'], (f.split('=')[0],f.split('=')[1]) )
                                t.match_and_insert(tokens)
                                recognized += 1

                    if   'application/json' in v \
                      or 'application/x-javascript' in v \
                      or 'text/javascript' in v:
                        body = e['request']['postData']['text']
                        post_json = get_json(body)
                        e['request']['saphireJson'] = post_json  # add the full dict, might need later...
                        count = tokenize_json(post_json, 'json', e['saphireTime'])
                        recognized += count
        except KeyError:
            pass

        try:
            ###### headers
            for h in e['request']['headers']:
                h['name'] = h['name'].lower()
                h['value']= h['value']
                if h['name'] in common_headers:
                    continue
                t = Token('req_header', e['saphireTime'], (h['name'],h['value']) )
                t.match_and_insert(tokens)
                recognized += 1
        except KeyError:
            pass

        try:
            for h in e['response']['headers']:
                h['name'] = h['name'].lower()
                h['value']= h['value']
                if h['name'] in common_headers:
                    continue
                t = Token('rsp_header', e['saphireTime'], (h['name'],h['value']) )
                t.match_and_insert(tokens)
                recognized += 1

            if str(e['response']['status'])[0]=='3':
                location = [ h['value'] for h in e['response']['headers'] if h['name'].lower()=='location' ][0]
                t = Token('rsp_header', e['saphireTime'], ('location',location))
                t.match_and_insert(tokens)
                recognized += 1
        except KeyError:
            pass
        except IndexError:
            pass


        try:
            ###### json in resp body
            header_values = [ h['value'] for h in e['response']['headers']]
            for v in header_values:

                if 'application/json' in v \
                        or 'application/x-javascript' in v \
                        or 'text/javascript' in v:
                    body = e['response']['content']['text']
                    resp_json = get_json(body)
                    e['response']['saphireJson'] = resp_json        # add the full dict, might need later...
                    count = tokenize_json(resp_json,'json', e['saphireTime'])
                    recognized += count
        except KeyError:
            pass


        try:
            ###### resp cookies
            if e['response']['cookies'] != []:
                for c in e['response']['cookies']:
                    t = Token('set_cookie', e['saphireTime'], (c['name'], c['value']))
                    t.match_and_insert(tokens)
                    recognized += 1
            else:
                cookie_string = [ h['value'] for h in e['response']['headers'] if h['name'].lower()=='set-cookie' ][0]
                for c in cookie_string.split('\n'):
                    t = Token('set_cookie', e['saphireTime'], (c.split('=')[0] ,c.split('=')[1].split('; ')[0]) )
                    t.match_and_insert(tokens)
                    recognized += 1
        except KeyError:
            pass
        except IndexError:
            pass


        try:
            ###### html input fields
            if 'text/html'== e['response']['content']['mimeType']:  # this also appears on XHTML
                html = e['response']['content']['text']
                soup = bs4.BeautifulSoup(html, 'html.parser')
                for form_input in  soup.find_all('input'):
                    input_type = form_input.attrs['type']
                    input_name = form_input.attrs['name']
                    input_id = ''
                    try:                                            # 'id' scraping optional
                        input_id = form_input.attrs['id']
                    except KeyError:
                        pass
                    tuple = (input_type,input_name,input_id) if input_id else (input_type, input_name)
                    t = Token('html', e['saphireTime'], tuple)
                    t.match_and_insert(tokens)
                    recognized += 1
        except KeyError:
            pass


        try:
            ###### JWTs                                             # discovered from match_and_insert > smart_decode call from the prev. ones
            jwt_header  = e['request']['saphireJWT']['header']
            count =  tokenize_json(jwt_header, 'jwt_header', e['saphireTime'])
            recognized += count
        except KeyError:
            pass

        try:
            jwt_payload = e['request']['saphireJWT']['payload']
            count = tokenize_json(jwt_payload, 'jwt_payload', e['saphireTime'])
            recognized += count
        except KeyError:
            pass

        try:
            jwt_header = e['response']['saphireJWT']['header']
            count = tokenize_json(jwt_header, 'jwt_header', e['saphireTime'])
            recognized += count
        except KeyError:
            pass

        try:
            jwt_payload = e['response']['saphireJWT']['payload']
            count = tokenize_json(jwt_payload, 'jwt_payload', e['saphireTime'])
            recognized += count
        except KeyError:
            pass


        if debug:
            print '[+] Recognized %d tokens in req with saphireTime %0.3f' % (recognized,e['saphireTime'])



    if debug:
        ans = raw_input('Print 10 random tokens?(y/N): ')
        if ans=='y':
            idx = 0
            for i in range(10):
                tokens[ idx % len(tokens) ].dump()
                idx += 87
    return



UNICODE_NONPRINTABLE_CATEGORIES = [ 'Zl', 'Zp', 'Cc', 'Cf', 'Cs','Co','Cn' ]
# we consider terminal-safe all unicode categories except Control Chars. and Separators
#   Space Separators (Zs) are accepted by convention
# https://www.unicode.org/reports/tr44/#General_Category_Values

def make_term_safe(text):
    """
    Eliminate termcolor.sequences split in half because of length restrictions
    """
    ret = ''
    i = 0
    while i < len(text):
        if text[i] not in string.printable:
            try:
                if text[i:i+5] in COLOR_PREFIXES:
                    ret += text[i:i+5]
                    i += 4
                elif text[i:i+4] in COLOR_ATTR_PREFIXES:
                    ret += text[i:i+4]
                    i += 3
                elif text[i:i+4] in termcolor.RESET:
                    ret += text[i:i+4]
                    i += 3
                else:
                    cat = unicodedata.category(text[i])
                    if cat in UNICODE_NONPRINTABLE_CATEGORIES:
                        ret += ''
                        i += 1
                    else:
                        ret += text[i]
            except IndexError:
                ret += ''
                return ret
        elif text[i] in string.whitespace and text[i]!=' ':
            ret += ''                                               # skip whitespace (except of the space)
        else:
            ret += text[i]
        i += 1

    return ret




def fit_print(line, offset, threshold, first_last=False):
    """
    threshold is absolute
    When first_last in kwargs, print no ending box-border |
    """
    if offset:                                                      # 1. Move
        line = ' '*offset + line

    threshold_w_nonp = 0                                            # calculate correct threhold (different if colored!)
    printable = 0
    if is_colored(line):
        i = 0
        while i < len(line):
            if line[i:i+5] in COLOR_PREFIXES:
                threshold_w_nonp += 5
                i += 4
            elif line[i:i + 4] in COLOR_ATTR_PREFIXES:
                threshold_w_nonp += 4
                i += 3
            elif line[i:i + 4] in termcolor.RESET:
                threshold_w_nonp += 4
                i += 3
            else:
                threshold_w_nonp += 1
                printable += 1
            i += 1
            if printable==threshold:
                break
        #threshold_w_nonp = max(threshold_w_nonp,threshold)
        threshold_w_nonp = threshold + (threshold_w_nonp-printable)

    else:
        threshold_w_nonp = threshold

    print_line = ''
    if first_last:                                                   
        print_line += ' '
        for i in range(threshold_w_nonp):
            if i<len(line)-1:
                print_line += line[i]
            else:
                print_line += ' '                                   # 2. Pad
                if i==threshold_w_nonp-1:                           
                    print_line += ' |'                              # 3. Clip
                    break
        print make_term_safe(termcolor.RESET + print_line)


    else:
        line = line[:offset]+'| '+line[offset:]                     # 4. Box border
        for i in range(threshold_w_nonp):
            if i<len(line):
                print_line += line[i]

                if i==threshold_w_nonp-4 and not is_colored(line):  
                    print_line += '... |'
                    break

                if i==threshold_w_nonp-4 and     is_colored(line):  
                    print_line += termcolor.RESET
                    print_line += '... |'
                    break
            else:
                print_line += ' '                              
                if i==threshold_w_nonp-1:
                    print_line += ' |'
                    break
        print make_term_safe(termcolor.RESET + print_line)            # 5. Catch color-leak from prev line





def flow_print():
    columns = 0
    try:
        columns = int(os.popen('stty size', 'r').read().split()[1])
    except IndexError:                                              # if the 'stty' trick won't work inside the IDE (or for any other reason),
        columns = 250                                               # work around with a fixed value

    divider = 50
    if debug:
        ans = raw_input('Enter req/resp divid er pct. (ENTER -> default=50%): ')
        if ans:
            divider = int(ans)
            print "Divider set to %d" % divider

    req_thres   = int( divider/100.0 * columns)
    resp_offset = int( divider/100.0 * columns) + 1
    if debug:
        print "Request-info will span %d/%d chars. Responses start on %d" % (req_thres, columns, resp_offset)

    max_len = 25                                                    # limit the length of tokens displayed, need to print as much as we can
    if xpand == XPAND_HORZ:                                         # only used in XPAND_HORZ
        if debug:                                                   # for a short, cool demonstration. Not the full value of it! (do this later manually)
            ans = raw_input('Enter maximum characters of tokens to be shown. (ENTER -> default=25)')
            if ans:
                max_len = int(ans)
                print "Max len set to %d" % max_len


    for i in range(len(req_resp)):
        e = req_resp[i]                                             # "startedDateTime": "2017-10-30T20:29:41.816Z"
        req_tokens_by_type = {}
        for cur_type in Token.types:
            req_tokens_by_type[cur_type] = []                       # will group tokens by type (init arrays)
        
        any_tokens = False
        for t in tokens:
            if t.time == e['saphireTime']:                          # filter tokens by request-time (keep only the ones of current req_resp)
                any_tokens = True
                req_tokens_by_type[ t.type ].append(t)                

        if not any_tokens:
            continue




        ##### Request
        fit_print('_'*500, 0, req_thres, True)
        line =    "%10s|%s (saphireTime:%0.3f)" % ('#'+str(i), e['startedDateTime'][11:22], e['saphireTime'])
        fit_print(line, 0, req_thres)                               
        u = urlparse.urlparse(e['request']['url'])
        line =    "%10s|%s %s" % (e['request']['method'], u.netloc, u.path)
        fit_print(line, 0, req_thres)

        fit_print('-'*10 + '+' + '-'*500, 0, req_thres)
        for t_type in ['url','cookie','req_header','form','json','jwt_header','jwt_payload']:
            if xpand == XPAND_HORZ:
                print_xpanding_horz(req_tokens_by_type, t_type, max_len,
                                    columns, req_thres, resp_offset, True)

            elif xpand == XPAND_VERT:
                print_xpanding_vert(req_tokens_by_type, t_type,
                                    columns, req_thres, resp_offset, True)

        fit_print('_'*500, 0, req_thres, True)
        
        
        
        ##### Response
        fit_print('_'*500, resp_offset, columns-2, True)
        line = "%4d %s" % (e['response']['status'], e['response']['statusText'])
        fit_print(line,resp_offset, columns-2)
        fit_print('-'*500, resp_offset, columns-2)

        for t_type in ['rsp_header','set_cookie','json','html', 'jwt_header', 'jwt_payload']:
            if xpand == XPAND_HORZ:
                print_xpanding_horz(req_tokens_by_type, t_type, max_len,
                                    columns, req_thres, resp_offset, False)

            elif xpand == XPAND_VERT:
                print_xpanding_vert(req_tokens_by_type, t_type,
                                    columns, req_thres, resp_offset, False)

        fit_print('_'*500, resp_offset, columns-2,True)
        print '\n'


def print_xpanding_horz(req_tokens_by_type, t_type, max_len, columns, req_thres, resp_offset, is_request):
    """
    Print tokens of the type specified in the same line

    :param req_tokens_by_type: the array of tokens of same type to be printed
    :param t_type: the type all tokens passed belong to
    :param max_len: the maximum length a token can hold in the crowded line
    :param columns: the width of the terminal window
    :param req_thres: the threshold, the requests should span until, width-speaking
    :param resp_offset: the absolute position of the req/resp split
    :param is_request (Boolean): Whether we are printing for a request or response
    """
    array_len = len(req_tokens_by_type[t_type])
    if array_len == 0:
        return

    line = "%10s|" % t_type
    for j in range(array_len):
        rtc = req_tokens_by_type[t_type][j]

        key = rtc.tuple[0]
        value = (rtc.tuple[1][:max_len] + '...') if len(rtc.tuple[1]) > max_len else rtc.tuple[1]
        colord_token = ''
        if t_type == 'html':
            colord_token = "<input type=%s name=%s %s/>" \
                           % ( key, value, ("id=" + rtc.tuple[2]) if len(rtc.tuple) == 3 else '')
        elif t_type in ['json', 'jwt_header', 'jwt_payload']:
            colord_token = "%s" % value
        else:
            colord_token = "%s=%s" % (key, value)
        if color_opt != COLOR_OPTS[0]:
            if rtc.fcolor:                                          # in try-match mode some tokens are not colored!
                colord_token = termcolor.colored(colord_token, rtc.fcolor)

        line += "%s%s" % (colord_token, ' ' if j < array_len - 1 else '')
    if is_request:
        fit_print(line, 0, req_thres)
    else:
        fit_print(line, resp_offset, columns - 2)


def print_xpanding_vert(req_tokens_by_type, t_type, columns, req_thres, resp_offset, is_request):
    """
    Print tokens of the type specified, one line each

    :param req_tokens_by_type: the array of tokens of same type to be printed
    :param t_type: the type all tokens passed belong to
    :param columns: the width of the terminal window
    :param req_thres: the threshold, the requests should span until, width-speaking
    :param resp_offset: the absolute position of the req/resp split
    :param is_request (Boolean): Whether we are printing for a request or response
    """
    array_len = len(req_tokens_by_type[t_type])
    if array_len == 0:
        return

    if t_type in ['json', 'jwt_header', 'jwt_payload']:
        """treat whole array as single token, but print line by line and color-highlight"""
        saphireTime_of_source_request = req_tokens_by_type[t_type][0].time
        e = [ r for r in req_resp if r['saphireTime']==saphireTime_of_source_request ][0]
        full_json = object()
        if   t_type == 'json':
            try:
                full_json = e['request']['saphireJson'] if is_request else e['response']['saphireJson']
            except KeyError:
                return
        else:
            e = e['request'] if is_request else e['response']
            try:
                full_json = e['saphireJWT']['header'] if t_type == 'jwt_header' else e['saphireJWT']['payload']
            except KeyError:
                return
                                                                    # pretty_print the full json object from the calling request
        string_io = [ sl for sl in StringIO.StringIO( pprint.pformat(full_json) )]
        for j in range(len(string_io)):
            repr_line = string_io[j]

            for m in re.findall(r"u'[^']*'", repr_line):
                repr_line = repr_line.replace(m, m[1:])             # strip the unicode tags from u'XXX'

            if color_opt != COLOR_OPTS[0]:
                for rtc in req_tokens_by_type[t_type]:             # search in json tokens and color inside the pretty_print
                    if rtc.fcolor and rtc.tuple[1] in repr_line:

                        if rtc.tuple[1] in ' '.join(COLOR_PREFIXES+COLOR_ATTR_PREFIXES):
                            continue                                # Don't recolor the color sequences!

                        colord_token = termcolor.colored(rtc.tuple[1], rtc.fcolor)
                        repr_line = repr_line.replace(rtc.tuple[1], colord_token)

            line = "%10s|" % ' '
            if j == 0:                                              # special care for the first line
                line = "%10s|" % t_type
            if is_request:
                fit_print(line + repr_line, 0, req_thres)
            else:
                fit_print(line + repr_line, resp_offset, columns - 2)
        return


    for j in range(array_len):
        line = "%10s|" % ' '
        if j == 0:                                                  # special care for the first line
            line = "%10s|" % t_type

        rtc = req_tokens_by_type[t_type][j]
        colord_token = ''
        if t_type == 'html':
            colord_token = "<input type=%s name=%s %s/>" \
                           % (rtc.tuple[0], rtc.tuple[1], ("id=" + rtc.tuple[2]) if len(rtc.tuple) == 3 else '')
        else:
            colord_token = "%s=%s" % (rtc.tuple[0], rtc.tuple[1])
        if color_opt != COLOR_OPTS[0]:
            if rtc.fcolor:                                          # in try-match mode some tokens are not colored!
                colord_token = termcolor.colored(colord_token, rtc.fcolor)

        if is_request:
            fit_print(line + colord_token, 0, req_thres)
        else:
            fit_print(line + colord_token, resp_offset, columns - 2)






COLOR_PREFIXES =        [ "\033[%dm" % n     for n in range(30,48) ]      # colors like 'red'
COLOR_ATTR_PREFIXES =   [ "\033[%dm" % n     for n in range(1,9)   ]      # attrs like 'underline'
def is_colored(text):
    for pre in COLOR_PREFIXES+COLOR_ATTR_PREFIXES:
        if pre in text:
            return True
    return False



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
            json_resp = json.loads( body[i:] )
            if debug:
                print "[+] Extracted JSON starting from pos %d: %s..." % (i,json.dumps(json_resp)[:30])
            return json_resp
        except ValueError:
            pass







def urldecode(text):
    """
    Custom unquote implementation to go through str() and back to unicode() ...if we can

    This is made because python escapes some strings when it auto-imports them to unicode,
    so unquote() can't do it's jobs correctly. Work on strings here, and return a unicode to the rest of the code

    Excellent piece of advice to keep in mind: "The Unicode Sandwich" (although I do the reverse here!)
    from https://stackoverflow.com/a/35444608

    str ->  Read ->  utf8
            Work
    utf8 -> Print -> str
    """
    try:
        return urllib.unquote( str(text) ).decode('utf-8')
    except UnicodeEncodeError:
        return text
    except UnicodeDecodeError:
        return text


def is_urlencoded(text):
    """
    Check if a string is urlencoded, by:
    - Decode and compare
    - Look for code sequences (like %2B)

    :return
        0 < conf < 1

    Use as
        while is_urlencoded(string):
            string = urldecode(string)
    """
    conf = 0.0

    try:
        if urldecode(text) != text:
            conf += 0.5
    except UnicodeWarning:
        pass

    regex = r"%([a-fA-F0-9]{2})"
    matches = re.findall(regex, text)
    if len(matches):
        conf += 0.5

    return conf



def is_timestamp(ts_string):
    global harfile_pagetime

    for c in ts_string:
        if not c.isdigit():
            return False

    in_year = 0
    try:
        in_year = time.gmtime(int(ts_string)).tm_year
    except ValueError:
        return False

    harfile_struct = time.strptime( harfile_pagetime.split('.')[0], "%Y-%m-%dT%H:%M:%S")
    harfile_year = harfile_struct.tm_year

    if abs(harfile_year - in_year) < 3:
        return True




def is_jwt(text):
    """
    :param text: is inferred as a JWT by it's format:
    - 3 parts separated by dots
    - First part (header) MUST decode to a printable string
    - Each part correctly decodes as Base64Url
    :return: True / False
    """
    parts = text.split('.')
    if len(parts) != 3:
        return False

    for p in parts:
        p += '==='                                                  # less padding throws Error but more padding is OK
        try:
            decoded = unicode(base64.urlsafe_b64decode( str(p) ), errors='ignore')
            if p == parts[0]+'===':
                if len(decoded)<6 or len([c for c in decoded if c not in string.printable]) > 0:
                    return False
        except TypeError:
            return False
        except UnicodeEncodeError:
            return False
    return True






def is_b64encoded(text):
    """
    A string is inferred as base64 encoded, by:

     Red flags are:
    - non base64 alphabet
    - it fails to decode

    - has valid words
    - Short- or odd-length'ed strings
    - Strings with more digits than letters
    - Strings with not-low frequency of symbols
    (biggest index => require most aces in bytes => most rare in plaintext)
    - Only hex chars (chars same case and less than f)

    :returns one of
        'no' if it's not a valid b64 code
        'yes' proceed with decoding and get a nice ascii string
    """
    # TODO all possible variations
    # inferred from the alphabet used
    #  instead of 'yes' return 'yes '+variation


    ##### Red flags
    base64_alphabet = list(string.ascii_letters + string.digits + "=+-/_")
    for c in text:
        if c not in base64_alphabet:
            return 'no'
    try:
        _ = base64.b64decode(text)
    except Exception:
        return 'no'

    ##### Do the Tests
    conf = 1.0
    if has_valid_words(text):
        conf += -0.3
    if len(text) < 25 or len(text) % 2 == 1:
        conf += -0.2
    if len( [d for d in text if d in string.digits] ) > len( [l for l in text if l in string.letters] ):
        conf += -0.2
    if float( len( [d for d in text if d in list("=+-/_")] ) ) > 20.0/100.0 * float( len(text) ):
        conf += -0.2
    if ( text.isupper() or text.islower() ) and len( [c for c in text if c not in string.hexdigits+"=+-/_"] )==0:
        # effectively: not .ismixed()       and          all chars in hexdigits+symbols
        conf += -0.2
    if text[:-1]=='=':
        conf += 0.2
    if text[:-2]=='==':
        conf += 0.2
    # TODO another test:
    # count different symbols appearing (besides =)

    ##### Decide on results
    if conf <= 0.5:
        return 'no'
    else:
        return 'yes'



def jwt_decode(text):
    global JWT_HEADER_TAG, JWT_PAYLOAD_TAG
    """
    Custom method to decode JWT without signature verification.

    Existing libraries wouldn't work because they don't support non-standard payloads,
    here we don't know what to expect so e.g. non-unicode characters could be encountered
    """
    parts = text.split('.')
    ret =  JWT_HEADER_TAG+ unicode(base64.urlsafe_b64decode(str(parts[0]+'===')), errors='ignore')
    ret += JWT_PAYLOAD_TAG + unicode(base64.urlsafe_b64decode(str(parts[1]+'===')), errors='ignore')
    return ret


def base64decode(text):
    """
    custom implementation to decode using the correct variation, and "normalize" the result
    :return: a one-lined text, stripped of non-printable chars and whitespace
    """
    # TODO pass variation in signature
    #  with def value, previously inferrred from is_b64encoded()

    decoded = base64.b64decode(text)                                # TODO replace with appropriate decoding call based on variation
    ret = ''
    for c in unicode(decoded, 'utf-8', 'ignore'):
        if unicodedata.category(c) in UNICODE_NONPRINTABLE_CATEGORIES:
            ret += '.'
        else:
            ret += c

    return ret



def has_valid_words(text):
    """
    Use pyenchant to try and guess if it's text, to help defer
    when to (or not to) do some smart decoding operations

    It produces a few false positives, but never a false negative

    :param text: the token to be checked
    :return: True if it surely has valid words, False if it surely doesn't, None when not sure...
    """
    d = enchant.Dict("en_US")                                       # TODO recognize locale and add another dict
    if d.check(text):
        return True

    tknzr = enchant.tokenize.get_tokenizer('en_US')
    for word_tuple in tknzr(text):
        word = word_tuple[0]
        if d.check(word):
            return True
        if d.suggest(word) != []:
            return True





####### GLOBALS (default values if not specified on cmdline)

common_headers = []
req_resp = []
tokens = []
harfile_pagetime = ''
debug = False
smart_decoding = True

COLOR_OPTS=['off','by-type','try-match','try-match-all']
color_opt = COLOR_OPTS[2]

(XPAND_HORZ, XPAND_VERT)= ('h','v')
xpand = XPAND_VERT

JWT_PAYLOAD_TAG = u', PAYLOAD='
JWT_HEADER_TAG  = u'JWT:HEADER='

class Token:
    fg_colors = [ 'red', 'green', 'yellow', 
                 'blue', 'magenta', 'cyan', 'white']
    bg_colors = [ 'on_'+fc for fc in fg_colors ]
    types = ['url',
             'cookie',     'set_cookie',
             'req_header', 'rsp_header',
             'form',
             'json', 'jwt_header', 'jwt_payload',
             'html']
    fc = 0                                                          # static =class-scoped counter for fg color idx in array

    def __init__(self, ttype, ttime, ttuple):
        self.tuple = ttuple
        if ttype not in Token.types:
            exit('Unsupported type \''+ttype+'\'!')
        self.type = ttype
        self.time = ttime                                           # saphireTime
        self.fcolor = ''
        if color_opt == COLOR_OPTS[1]:                              # "by-type" : loop colors for same-typed tokens, 
            bc = Token.types.index(ttype) % len(Token.bg_colors)
            self.bcolor = Token.bg_colors[ bc ]
            
            if Token.fc==bc:
                Token.fc = (Token.fc+1) % len(Token.fg_colors)
            
            self.fcolor = Token.fg_colors[Token.fc]
            Token.fc = (Token.fc+1) % len(Token.fg_colors)
      

    def dump(self):
        dictified = {
                'type' : self.type,
                'time' : self.time,
                'tuple': self.tuple,
                }
        print json.dumps( dictified, indent=4, sort_keys=True )


    def match_and_insert(self, array):
        """
        array.append() encapsulated in the Token object to add custom actions,
        for every new token: Here's what it does:
        1.  Search if it has pre-occured and color accordingly
        2.  Smart decode (inspired by Burp)
        """

        ##### Smart decoding

        key =   self.smart_decode(self.tuple[0]) if smart_decoding and self.tuple[0] else self.tuple[0]
        value = self.smart_decode(self.tuple[1]) if smart_decoding and self.tuple[1] else self.tuple[1]

        self.tuple = (key, value) if len(self.tuple)==2 else (key, value, self.tuple[2])


        ##### Match Coloring
        if self.type != 'html':                                     # Don't color 'html' <input fields
            if color_opt == COLOR_OPTS[3]:
                """ try-match-all : If found use same color, but all new tokens get colored"""
                found = False

                for t in array:
                    if self.tuple[1] == t.tuple[1]:
                        self.fcolor = t.fcolor
                        found = True

                if not found:
                    self.fcolor = Token.fg_colors[Token.fc]
                    Token.fc = (Token.fc + 1) % len(Token.fg_colors)

            elif color_opt == COLOR_OPTS[2]:
                """ try-match : If found use same color, but color only the tokens seen at least before """
                found = False

                for t in array:
                    if self.tuple[1] == t.tuple[1]:
                        found = True
                        if t.fcolor:
                            self.fcolor = t.fcolor
                        else:
                            self.fcolor = Token.fg_colors[Token.fc]     # new color for both New...
                            t.fcolor = self.fcolor                      # ...and Old
                            Token.fc = (Token.fc + 1) % len(Token.fg_colors)

                if not found:
                    self.fcolor = ''

        array.append(self)




    def smart_decode(self, text):
        global JWT_HEADER_TAG, JWT_PAYLOAD_TAG
        """
        Recursively decode the tuple of the current token.
        Highlight the value on certain cases.
    
        By the time the tokens' key/value come here the final
        coloring has been settled and we can procceed with bg "marker"
            to note b64 / gzip encoding
        but with the more common ones:
            not to spam  url / html
    
        :param text: to be decoded and bg-colored
        """
        orig_text = text
        transformation_chain = ''
        for i in range(100):
            did_transformation = False
            if is_urlencoded(text)==1:                              # 1. URL encoding
                text = urldecode(text)
                transformation_chain += 'url '
                did_transformation = True
    
    
            if 'yes' in is_b64encoded(text):                        # 2. Base 64
                text = base64decode(text)
                transformation_chain += 'b64 '
                did_transformation = True
                if color_opt!=COLOR_OPTS[0]:
                    text = termcolor.colored(text, attrs=['underline'])
    
    
            if is_timestamp(text):                                  # 3. Timestamp
                text = timestamp_to_hartime(text)
                transformation_chain += 'timestamp '
                did_transformation = False                          # decode no further
                if color_opt!=COLOR_OPTS[0]:
                    text = termcolor.colored(text, attrs=['underline'])
    
    
            if is_jwt(text):                                        # 4. JSON Web Token
                text = jwt_decode(text)
                jwt_header  = text.split(JWT_PAYLOAD_TAG)[0].replace(JWT_HEADER_TAG,'')
                jwt_payload = text.split(JWT_PAYLOAD_TAG)[1]
                e = [ r for r in req_resp if r['saphireTime']==self.time ][0]
                                                                    # find token's origin request, by its time
                if self.type in ['url','cookie','req_header','form']:
                    e = e['request']                                # was the JWT found in the request or the response?
                else:
                    e = e['response']

                e['saphireJWT'] = {}                                # set the 2 dicts, will be recognized() later...
                try:
                    e['saphireJWT']['header']  = json.loads(jwt_header)
                except ValueError:                                  # no valid json in JWT, never mind
                    pass
                try:
                    e['saphireJWT']['payload'] = json.loads(jwt_payload)
                except ValueError:
                    pass

                transformation_chain += 'jwt '
                did_transformation = True
                if color_opt != COLOR_OPTS[0]:
                    text = termcolor.colored(text, attrs=['underline'])


            if did_transformation == False:
                break
    
        if debug and transformation_chain:
            try:
                print "[+] Applied transformations: %s. '%s' -> '%s'" % (transformation_chain, orig_text, text)
            except UnicodeDecodeError:
                pass
    
        return text





def tokenize_json(json_dict, token_type, token_time):
    global tokens
    """
    :param json_dict: Python object to walk
    and make a new token for every item

    :param token_type: The type for the token to create
    :param token_time: The saphireTime for the token to create

    :return The number of tokens recognized 
    """
    recognized = 0

    all_strings = []
    walk(json_dict, all_strings)  # break the dict
    all_strings = list(set(all_strings))  # unique-ify
    for el in all_strings:
        if isinstance(el, bool):
            continue  # ignore True/False
        t = Token(token_type, token_time, ('', unicode(el)))
        t.match_and_insert(tokens)
        recognized += 1
    return recognized



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


def set_saphireTimes():
   req_resp2 = [ e.update( {"saphireTime":hartime_to_saphire(e["startedDateTime"])} )          for e in req_resp ]


def sort_list_of_dicts_by_key(list, dictkey):
    return sorted(list, key=lambda d: d[dictkey])





####### MAIN

if __name__ == "__main__":                                          # TODO split files (Token, saphire.py, utils)
    parser = argparse.ArgumentParser(description="...a Smart API Reverse Enginneering Helper", epilog="See README for more on the options provided here")
    parser.add_argument("harfile", help="the recorded .har flow to analyze")
    parser.add_argument("-d", "--debug", help="fine-tune settings and get more verbose output", action="store_true")
    parser.add_argument("-c", "--color", type=int, choices=[0, 1, 2, 3],
                        help="color setting: 0=Off, 1=by-type, 2=try-match, 3=try-match-all.")
    parser.add_argument("-x","--expand", choices=['h','v'],
                        help="dimension to expand the list of tokens per-category: h=Horizontally, v=Vertically. See README for more")
    parser.add_argument("-s", "--nosmart", help="turnoff smart decoding", action="store_true")


    args = parser.parse_args()
    if args.debug:
        debug = True
    if args.color != None :
        color_opt = COLOR_OPTS[args.color]
    if args.expand:
        xpand = args.expand
    if args.nosmart:
        smart_decoding = False

    isolate_requests( args.harfile )
    set_saphireTimes()                                   # make new field with unique timestamp
    req_resp = sort_list_of_dicts_by_key(req_resp,'saphireTime')
    recognize_tokens()

    graph = False                                                   # TODO make cmdline switch --flow-print vs --flow-graph (mutually_exclusive)
    if graph:
#       flow_graph()                                                # TODO gui
        pass
    else:
        flow_print()

    
