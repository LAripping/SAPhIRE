#!/usr/bin/python

import sys
import json
import termcolor
import os
import string
import urlparse
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
    if not fdomain:
        for e in list(req_resp):                                    # iterating over a copy
            if fdomain not in e['request']['url']:
                req_resp.remove(e)
                if debug: 
                    print '[+] Filtered out entry with url: '+ e['request']['url']



    no_data = raw_input("Ignore media/fonts/css/... junk? (Y/n): ")
    if no_data in ["", "y", "Y"]:
        junk_ext = [".ttf", ".woff", ".otf", ".eot",                # fonts
                    ".css", ".sass",                                # styles
                    ".img", ".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif", ".bmp", ".ico",
                    ".pdf",                                         # img / doc
                    ]                                               # media (HTML? TODO)


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

        ###### url params
        for p in e['request']['queryString']:
            t = Token('url', e['time'], (p['name'],p['value'])  )
            t.match_and_insert(tokens)
            recognized += 1

        ###### cookies
        for c in e['request']['cookies']:
            t = Token('cookie', e['time'], (c['name'],c['value']) )
            t.match_and_insert(tokens)
            recognized += 1

        ###### form fields
        if e['request']['method'] == 'POST':                        # TODO what about PUT ?
            if 'application/x-www-form-urlencoded' in [ h['value'] for h in e['request']['headers'] ]:
                                                                    # TODO what about application/form-multipart
                for f in e['request']['postData']['params']:
                    t = Token('form', e['time'], (f['name'],f['value']) )
                    t.match_and_insert(tokens)
                    recognized += 1

        ###### headers
        for h in e['request']['headers']:
            h['name'] = h['name'].lower()
            h['value']= h['value'].lower()
            if h['name'] in common_headers:
                continue
            t = Token('req_header', e['time'], (h['name'],h['value']) )
            t.match_and_insert(tokens)
            recognized += 1

        for h in e['response']['headers']:
            h['name'] = h['name'].lower()
            h['value']= h['value'].lower()
            if h['name'] in common_headers:
                continue
            t = Token('resp_header', e['time'], (h['name'],h['value']) )
            t.match_and_insert(tokens)
            recognized += 1

        ###### resp body
        if 'application/json' in [ h['value'] for h in e['response']['headers']]:
            body = e['response']['content']['text']
            all_lists = []
            for l in dict_generator(body):                          # TODO test this
                all_lists += l
            all_strings = list(set(all_lists))                      # unique-ify 
            for s in all_strings:
                t = Token('resp', e['time'], ('',s))
                t.match_and_insert(tokens)
                recognized += 1

        ###### html element
        # TODO scrape <input type=hidden value> from responses

        if debug:
            print '[+] Recognized '+str(recognized)+' tokens in req with time '+str(e['time'])
    
    if debug:
        ans = raw_input('Print 10 random tokens?(y/N): ')
        if ans=='y':
            idx = 0
            for i in range(10):
                tokens[ idx % len(tokens) ].dump()
                idx += 87
    return



COLOR_PREFIXES = [ "\033[%dm" % n     for n in range(30,48) ]
def is_colored(text):
    for pre in COLOR_PREFIXES:
        if pre in text:
            return True
    return False


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
        print make_printable(print_line)


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
        print make_printable(print_line)





def flow_print():
                                                                    # this won't work in the debugger
    columns = 200 if debug else os.popen('stty size', 'r').read().split()[1]
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


    for i in range(len(req_resp)):
        e = req_resp[i]                                             # "startedDateTime": "2017-10-30T20:29:41.816Z"
        req_tokens_by_type = {}
        for cur_type in Token.types:
            req_tokens_by_type[cur_type] = []                       # will group tokens by type (init arrays)
        
        any_tokens = False
        for t in tokens:
            if t.time == e['time']:                                 # filter tokens by request-time (kepp only the ones of current req_resp)
                any_tokens = True
                req_tokens_by_type[ t.type ].append(t)                

        if not any_tokens:
            continue
        
        ##### Request
        fit_print('_'*500, 0, req_thres, True)
        line =    "%10s|%s" % ('#'+str(i), e['startedDateTime'][11:22]) 
        fit_print(line, 0, req_thres)                               
        u = urlparse.urlparse(e['request']['url'])
        line =    "%10s|%s %s" % (e['request']['method'], u.netloc, u.path)
        fit_print(line, 0, req_thres)

        fit_print('-'*10 + '+' + '-'*500, 0, req_thres)
        for t_type in ['url', 'cookie', 'req_header', 'form']:
            l = len(req_tokens_by_type[t_type])
            if l:
                line = "%10s|" % t_type
                for j in range(l):
                    rtc = req_tokens_by_type[t_type][j]
                    
                    colord_token = "%s=%s" % ( rtc.tuple[0],rtc.tuple[1] )
                    if color_opt!=COLOR_OPTS[0]:
                        colord_token = termcolor.colored( colord_token, rtc.fcolor)

                    line += "%s%s" % (colord_token,' ' if j<l-1 else '')
                fit_print(line, 0, req_thres)
        #        sys.exit(0)

        fit_print('_'*500, 0, req_thres, True)
        
        
        
        ##### Response
        fit_print('_'*500, resp_offset, columns-2, True)
        line = "%4d %s" % (e['response']['status'], e['response']['statusText'])
        fit_print(line,resp_offset, columns-2)
        fit_print('-'*500, resp_offset, columns-2)

        for t_type in ['resp_header','resp','html']:
            l = len(req_tokens_by_type[t_type])
            if l:
                line = "%10s|" % t_type
                for j in range(l):
                    rtc = req_tokens_by_type[t_type][j]

                    colord_token = "%s=%s" % ( rtc.tuple[0],rtc.tuple[1] )
                    if color_opt!=COLOR_OPTS[0]:
                        colord_token = termcolor.colored( colord_token, rtc.fcolor )

                    line += "%s%s" % (colord_token,' ' if j<l-1 else '')
                fit_print(line,resp_offset,columns-2)

        fit_print('_'*500, resp_offset, columns-2,True)
        print '\n'











####### GLOBALS

common_headers = []
reqs_resp = []
tokens = []
debug = True                                                        # TODO make cmdline opt

COLOR_OPTS=['off','by-type','try-match']
color_opt = COLOR_OPTS[2]                                           # TODO make cmdline opt
                                                                    # TODO make an asciinema for the README now that we have colors

class Token:
    fg_colors = [ 'red', 'green', 'yellow', 
                 'blue', 'magenta', 'cyan', 'white']
    bg_colors = [ 'on_'+fc for fc in fg_colors ]
    types = ['url', 'cookie', 'req_header', 'resp_header', 'form', 'resp', 'html'] 
    fc = 0                                                          # static =class-scoped counter for fg color idx in array

    def __init__(self, ttype, ttime, ttuple):
        self.tuple = ttuple
        if ttype not in Token.types:
            exit('Unsupported type \''+ttype+'\'!')
        self.type = ttype
        self.time = ttime
        
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
        Before adding any new token to the global array of recognized ones, search if it has 
        pre-occured and assign the same color. If not, assign a new one from the pool of free ones. 
        """

        if color_opt == COLOR_OPTS[2]:                              # "try_match" 
            found = False

            for t in array:
                if self.tuple[1] == t.tuple[1]:
                    self.fcolor = t.fcolor
                    found = True
    
            if not found:
                self.fcolor = Token.fg_colors[Token.fc]
                Token.fc = (Token.fc + 1) % len(Token.fg_colors)
    
        array.append(self)
            


####### MAIN

if __name__ == "__main__":
    if len(sys.argv) == 1:
        exit( "Usage: %s flow.har" % sys.argv[0] )
        # TODO replace with proper arg parsing

    isolate_requests( sys.argv[1] )
    recognize_tokens()
    

    graph = False                                                   # TODO make cmdline opt
    if graph:
#       flow_graph() TODO gui
        pass
    else:
        flow_print()

    
