#!/usr/bin/python

import sys
import json
import termcolor
import os
import urlparse

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
            tokens.append(t)
            recognized += 1

        ###### cookies
        for c in e['request']['cookies']:
            t = Token('cookie', e['time'], (c['name'],c['value']) )
            tokens.append(t)
            recognized += 1

        ###### form fields
        if e['request']['method'] == 'POST':                        # TODO what about PUT ?
            if 'application/x-www-form-urlencoded' in [ h['value'] for h in e['request']['headers'] ]:
                                                                    # TODO what about application/form-multipart
                for f in e['request']['postData']['params']:
                    t = Token('form', e['time'], (f['name'],f['value']) )
                    tokens.append(t)
                    recognized += 1

        ###### headers
        for h in e['request']['headers']:
            h['name'] = h['name'].lower()
            h['value']= h['value'].lower()
            if h['name'] in common_headers:
                continue
            t = Token('req_header', e['time'], (h['name'],h['value']) )
            tokens.append(t)
            recognized += 1

        for h in e['response']['headers']:
            h['name'] = h['name'].lower()
            h['value']= h['value'].lower()
            if h['name'] in common_headers:
                continue
            t = Token('resp_header', e['time'], (h['name'],h['value']) )
            tokens.append(t)
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
                tokens.append(t)
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









def fit_print(line, offset, threshold, first_last=False):
    """
    threshold is absolute
    When first_last in kwargs, print no ending box-border |
    """

    # TODO end any colors hung
    #offset =+ 2                                                   

    if offset:                                                      # move
        line = ' '*(offset+1) + line

    if len(line) >= threshold-5:                                    # clip 
        if not first_last:
            line = line[0:threshold-5]
            line += '...'
        else:
            line = line[0:threshold]

    if first_last:                                                  # box border 
        print " %-*s " % (threshold,line)
    else:
        line = line[:offset]+'| '+line[offset:]
#        line = ['|' if i==offset else line[i] for i in range(len(line)) ]
        print "%-*s |" % (threshold,''.join(line))








def flow_print():
    # TODO replace tokens.append(t) calls above with a t.search_and_insert_to(tokens)
    # to make use of a common method 
    # where they are colored similarly if found again

    rows, columns = os.popen('stty size', 'r').read().split()
    columns = int(columns)
    divider = 50
    if debug:
        ans = raw_input('Enter req/resp divider pct. (ENTER -> default=50%): ')
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
                req_tokens_by_type[ t.type ].append(t.tuple)                

        if not any_tokens:
            continue
        
        ##### Request
        fit_print('_'*500, 0, req_thres, True)
        line =    "%10s|%s" % ('#'+str(i), e['startedDateTime'][11:22]) 
        fit_print(line, 0, req_thres)                               # TODO trim according to len and end any colors hung (line, offset, threshold)
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
                    line += "%s=%s%s" % (rtc[0],rtc[1],' ' if j<l-1 else '')
                fit_print(line, 0, req_thres)

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
                    line += "%s=%s%s" % (rtc[0],rtc[1],' ' if j<l-1 else '')
                fit_print(line,resp_offset,columns-2)

        fit_print('_'*500, resp_offset, columns-2,True)
        print '\n'











####### GLOBALS

common_headers = []
reqs_resp = []
tokens = []
debug = True

class Token:
    fg_colors = ['grey', 'red', 'green', 'yellow', 
                 'blue', 'magenta', 'cyan', 'white']
    bg_colors = [ 'on_'+fc for fc in fg_colors ]
    types = ['url', 'cookie', 'req_header', 'resp_header', 'form', 'resp', 'html'] 
    fc = 0

    def __init__(self, ttype, ttime, ttuple):
        self.tuple = ttuple
        if ttype not in Token.types:
            exit('Unsupported type \''+ttype+'\'!')
        self.type = ttype
        self.time = ttime
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




####### MAIN

if __name__ == "__main__":
    if len(sys.argv) == 1:
        exit( "Usage: %s flow.har" % sys.argv[0] )
        # TODO replace with proper arg parsing

    isolate_requests( sys.argv[1] )
    recognize_tokens()
    

    graph = False
    if graph:
#       flow_graph() TODO gui
        pass
    else:
        flow_print()

    
