#!/usr/bin/python
import base64
import sys
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
#TODO that pip install -r requirements.txt trick


def isolate_requests(har_file):
    global req_resp, debug

    har = {}
    with open(har_file) as harfile:
        har = json.load( harfile )

    req_resp = har['log']['entries']
    if debug:
        print "[+] Read %d entries" % len(req_resp)

    fdomain = raw_input("Filter by domain? (ENTER for no): ")
    if fdomain:
        for e in list(req_resp):                                    # iterating over a copy
            u = urlparse.urlparse(e['request']['url'])
            if fdomain not in u.netloc:
                req_resp.remove(e)
                if debug: 
                    print '[+] Filtered out entry with url: %s' % u.netloc



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
    pre = pre[:] if pre else []
    if isinstance(indict, dict):
        for key, value in indict.items():
            if isinstance(value, dict):
                for d in dict_generator(value, [key] + pre):
                    yield d
            elif isinstance(value, list) or isinstance(value, tuple):
                for v in value:
                    for d in dict_generator(v, [key] + pre):
                       yield d
            else:
                yield pre + [key, value]
    else:
        yield indict





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
            for c in e['request']['cookies']:
                t = Token('cookie', e['saphireTime'], (c['name'],c['value']) )
                t.match_and_insert(tokens)
                recognized += 1
        except KeyError:
            pass

        try:
            ###### form fields
            if e['request']['method'] == 'POST':                        # TODO what about PUT ?
                if 'application/x-www-form-urlencoded' in [ h['value'] for h in e['request']['headers'] ]:
                                                                        # TODO what about application/form-multipart
                    for f in e['request']['postData']['params']:
                        t = Token('form', e['saphireTime'], (f['name'],f['value']) )
                        t.match_and_insert(tokens)
                        recognized += 1
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
        except KeyError:
            pass

        try:
            ###### resp body
            if 'application/json' in [ h['value'] for h in e['response']['headers']]:
                body = e['response']['content']['text']
                all_lists = []
                for l in dict_generator(body):                          # TODO test this
                    all_lists += l
                all_strings = list(set(all_lists))                      # unique-ify
                for s in all_strings:
                    t = Token('resp', e['saphireTime'], ('',s))
                    t.match_and_insert(tokens)
                    recognized += 1
        except KeyError:
            pass


        try:
            ###### resp cookies
            for c in e['response']['cookies']:
                t = Token('set_cookie', e['saphireTime'], (c['name'], c['value']))
                t.match_and_insert(tokens)
                recognized += 1
        except KeyError:
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



def make_printable(text):
    """strip non-printable chars, but keep the color ones"""
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
                    ret += ''
                    i += 2
            except IndexError:
                ret += ''
                return ret

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
            elif line[i:i + 4] in termcolor.RESET:
                threshold_w_nonp += 4
                i += 3
            else:
                threshold_w_nonp += 1
                printable += 1
            i += 1
            if printable==threshold:
                break
        threshold_w_nonp = max(threshold_w_nonp,threshold)

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
        print make_printable(termcolor.RESET+print_line)


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
        print make_printable(termcolor.RESET+print_line)            # 5. Catch color-leak from prev line





def flow_print():
                                                                    # 'stty' trick won't work in the debugger, detect it as explained in the below question instead!
                                                                    # https://stackoverflow.com/questions/333995/how-to-detect-that-python-code-is-being-executed-through-the-debugger
    columns = 250 if sys.gettrace() else int(os.popen('stty size', 'r').read().split()[1])
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
        for t_type in ['url', 'cookie', 'req_header', 'form']:
            l = len(req_tokens_by_type[t_type])
            if l:
                if xpand == XPAND_HORZ:

                    line = "%10s|" % t_type
                    for j in range(l):
                        rtc = req_tokens_by_type[t_type][j]

                        key     = rtc.tuple[0]
                        value   = (rtc.tuple[1][:max_len]+'...') if len(rtc.tuple[1]) > max_len else rtc.tuple[1]
                        colord_token = "%s=%s" % ( key,value )
                        if color_opt!=COLOR_OPTS[0]:
                            if rtc.fcolor:                          # in try-match mode some tokens are not colored!
                                colord_token = termcolor.colored( colord_token, rtc.fcolor)

                        line += "%s%s" % (colord_token,' ' if j<l-1 else '')
                    fit_print(line, 0, req_thres)

                elif xpand == XPAND_VERT:

                    for j in range(l):
                        line = "%10s|" % ' '
                        if j==0:                                    # special care for the first line
                            line = "%10s|" % t_type

                        rtc = req_tokens_by_type[t_type][j]
                        colord_token = "%s=%s" % (rtc.tuple[0], rtc.tuple[1])
                        if color_opt != COLOR_OPTS[0]:
                            if rtc.fcolor:                          # in try-match mode some tokens are not colored!
                                colord_token = termcolor.colored(colord_token, rtc.fcolor)
                        fit_print(line + colord_token, 0, req_thres)

        fit_print('_'*500, 0, req_thres, True)
        
        
        
        ##### Response
        fit_print('_'*500, resp_offset, columns-2, True)
        line = "%4d %s" % (e['response']['status'], e['response']['statusText'])
        fit_print(line,resp_offset, columns-2)
        fit_print('-'*500, resp_offset, columns-2)

        for t_type in ['rsp_header','set_cookie','resp','html']:
            l = len(req_tokens_by_type[t_type])
            if l:
                if xpand == XPAND_HORZ:

                    line = "%10s|" % t_type
                    for j in range(l):
                        rtc = req_tokens_by_type[t_type][j]

                        key     = rtc.tuple[0]
                        value   = (rtc.tuple[1][:max_len]+'...') if len(rtc.tuple[1]) > max_len else rtc.tuple[1]
                        colord_token = ''
                        if t_type == 'html':
                            colord_token = "<input type=%s name=%s %s/>" % (key, value, ( "id="+rtc.tuple[2] ) if len(rtc.tuple)==3 else '' )
                        else:
                            colord_token = "%s=%s" % (key, value)
                        if color_opt!=COLOR_OPTS[0]:
                            if rtc.fcolor:                          # in try-match mode some tokens are not colored!
                                colord_token = termcolor.colored( colord_token, rtc.fcolor)

                        line += "%s%s" % (colord_token,' ' if j<l-1 else '')
                    fit_print(line,resp_offset,columns-2)

                elif xpand == XPAND_VERT:

                    for j in range(l):
                        line = "%10s|" % ' '
                        if j==0:                                    # special care for the first line
                            line = "%10s|" % t_type

                        rtc = req_tokens_by_type[t_type][j]
                        colord_token = ''
                        if t_type=='html':
                            colord_token = "<input type=%s name=%s %s/>" \
                                           % (rtc.tuple[0], rtc.tuple[1], ( "id="+rtc.tuple[2] ) if len(rtc.tuple)==3 else '' )
                        else:
                            colord_token = "%s=%s" % (rtc.tuple[0], rtc.tuple[1])
                        if color_opt != COLOR_OPTS[0]:
                            if rtc.fcolor:                          # in try-match mode some tokens are not colored!
                                colord_token = termcolor.colored(colord_token, rtc.fcolor)
                        fit_print(line + colord_token,resp_offset,columns-2)


        fit_print('_'*500, resp_offset, columns-2,True)
        print '\n'






COLOR_PREFIXES =        [ "\033[%dm" % n     for n in range(30,48) ]      # colors like 'red'
COLOR_ATTR_PREFIXES =   [ "\033[%dm" % n     for n in range(1,9)   ]      # attrs like 'underline'
def is_colored(text):
    for pre in COLOR_PREFIXES+COLOR_ATTR_PREFIXES:
        if pre in text:
            return True
    return False


def is_urlencoded(text):
    """
    Check if a string is urlencoded, by:
    - Decode and compare
    - Look for code sequences (like %2B)
    - deny If it introduces non-printables characters

    :return
        0 < conf < 1

    Use as
        while is_urlencoded(string):
            string = urllib.unquote(string)

    """
    conf = 0.0

    if urllib.unquote(text) != text:
        conf += 0.5

    regex = r"%([a-fA-F0-9]{2})"
    matches = re.findall(regex, text)
    if len(matches):
        conf += 0.5

    was_printable = True
    for c in text:
        if c not in string.printable:
            was_printable = True
    for c in urllib.unquote(text):
        if c not in string.printable and was_printable:
            return 0


    return conf


def is_b64encoded(text):
    """
    A string is inferred as base64 encoded, by:
    - The alphabet used (A-Za-z0-9=+-/_)
    AND
    - whether it decodes

    Red flags are:
    - Short- or odd-length'ed strings
    - Strings with more digits than letters
    - Strings with not-low frequency of symbols
    (biggest index => require most aces in bytes => most rare in plaintext)

    :returns one of
        'no' if it's not a valid b64 code
        'yes' proceed with decoding and get a nice ascii string
    """
    # TODO all possible variations
    # inferred from the alphabet used
    #  instead of 'yes' return 'yes '+variation

    # TODO test and incorporate
    # https://blog.nviso.be/2017/08/30/decoding-malware-via-simple-statistical-analysis/
    # https://blog.didierstevens.com/2017/08/12/update-byte-stats-py-version-0-0-6/

    if len(text) < 10 or len(text) % 2 == 1:
        return 'no'
    if len( [d for d in text if d in string.digits] ) > len( [l for l in text if l in string.letters] ):
        return 'no'
    if float( len( [d for d in text if d in list("=+-/_")] ) ) > 3.0/100.0 * float( len( [l for l in text if l in string.letters] ) ):
        return 'no'


    base64_alphabet = list(string.ascii_letters + string.digits + "=+-/_")
    for c in text:
        if c not in base64_alphabet:
            return 'no'

    try:
        decoded = base64.b64decode(text)
    except Exception:
        return 'no'

    return 'yes'


def base64decode(text):
    """
    custom implementation to decode using the correct variation, and "normalize" the result
    :return: a one-lined text, stripped of non-printable chars and whitespace
    """
    # TODO pass variation in signature
    #  with def value, previously inferrred from is_b64encoded()

    decoded = base64.b64decode(text)                                # TODO replace with appropriate decoding call based on variation
    ret = ''
    for c in decoded:
        if (c not in string.printable) or c in (string.whitespace):
            c='.'
        ret += c
    return ret




####### GLOBALS (default values if not specified on cmdline)

common_headers = []
req_resp = []
tokens = []
debug = False

COLOR_OPTS=['off','by-type','try-match','try-match-all']
color_opt = COLOR_OPTS[2]

(XPAND_HORZ, XPAND_VERT)= ('h','v')
xpand = XPAND_VERT


class Token:
    fg_colors = [ 'red', 'green', 'yellow', 
                 'blue', 'magenta', 'cyan', 'white']
    bg_colors = [ 'on_'+fc for fc in fg_colors ]
    types = ['url', 'cookie', 'set_cookie', 'req_header', 'rsp_header', 'form', 'resp', 'html']
    fc = 0                                                          # static =class-scoped counter for fg color idx in array

    def __init__(self, ttype, ttime, ttuple):
        self.tuple = ttuple
        if ttype not in Token.types:
            exit('Unsupported type \''+ttype+'\'!')
        self.type = ttype
        self.time = ttime
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

        key = smart_decode(self.tuple[0])
        value = smart_decode(self.tuple[1])

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







def smart_decode(string):
    """
    Recursively decode and highlight the output on certain cases.

    By the time the tokens' key/value come here the final
    coloring has been settled and we can procceed with bg "marker"
        to note b64 / gzip encoding
    but with the more common ones:
        not to spam  url / html

    :param string: to be decoded and bg-colored
    """
    orig_string = string
    transformation_chain = ''
    for i in range(100):
        did_transformation = False
        if is_urlencoded(string)==1:                                # 1. URL encoding
            string = urllib.unquote(string)
            transformation_chain += 'url '
            did_transformation = True


        if 'yes' in is_b64encoded(string):                          # 3. Base 64
            string = base64decode(string)
            transformation_chain += 'b64 '
            did_transformation = True
            if color_opt!=COLOR_OPTS[0]:
                string = termcolor.colored(string, attrs=['underline'])

        if did_transformation == False:
            break

    if debug and transformation_chain:
        print "[+] Applied transformations: %s. '%s' -> '%s'" % (transformation_chain, orig_string, string)

    return string










def hartime_to_saphire(time_string):
    """about time:

    > time_string = "2017-11-28T20:14:53.852Z"

    > time_struct = time.strptime( time_string.split('.')[0], "%Y-%m-%dT%H:%M:%S")
    time.struct_time(tm_year=2017, tm_mon=11, tm_mday=28, tm_hour=20, tm_min=14, tm_sec=53, tm_wday=1, tm_yday=332, tm_isdst=-1)

    > timestamp = str( time.mktime(time_struct) ).split('.')[0]
    1511892893

    > mili = time_string.split('.')[1].split('Z')[0]
    852

    > float(timestamp+'.'+mili)
    1511892893.852
    """
    time_struct = time.strptime( time_string.split('.')[0], "%Y-%m-%dT%H:%M:%S")
    timestamp = str(time.mktime(time_struct)).split('.')[0]
    mili = time_string.split('.')[1].split('Z')[0]
    return float(timestamp+'.'+mili)


def set_saphireTimes():
   #TODO try commented oneliner below if it works"""
   req_resp2 = [ e.update( {"saphireTime":hartime_to_saphire(e["startedDateTime"])} )          for e in req_resp ]


def sort_list_of_dicts_by_key(list, dictkey):
    return sorted(list, key=lambda d: d[dictkey])





####### MAIN

if __name__ == "__main__":                                          # TODO split files (Token, saphire.py, utils)
    parser = argparse.ArgumentParser()
    parser.add_argument("harfile", help="the recorded .har flow to analyze")
    parser.add_argument("-d", "--debug", help="fine-tune settings and get more verbose output", action="store_true")
    parser.add_argument("-c", "--color", type=int, choices=[0, 1, 2, 3],
                        help="color setting: 0=Off, 1=by-type, 2=try-match, 3=try-match-all. See README for more")
    parser.add_argument("-x","--expand", choices=['h','v'],
                        help="dimension to expand the list of tokens per-category: h=Horizontally, v=Vertically. See README for more")


    args = parser.parse_args()
    if args.debug:
        debug = True
    if args.color != None :
        color_opt = COLOR_OPTS[args.color]
    if args.expand:
        xpand = args.expand

    isolate_requests( args.harfile )
    set_saphireTimes()                                   # make new field with unique timestamp
    req_resp = sort_list_of_dicts_by_key(req_resp,'saphireTime')    # TODO arg=key in the req{} . Our custom time added in the step above
    recognize_tokens()

    graph = False                                                   # TODO make cmdline switch --flow-print vs --flow-graph (mutually_exclusive)
    if graph:
#       flow_graph()                                                # TODO gui
        pass
    else:
        flow_print()

    
