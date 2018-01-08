#!/usr/bin/python
#encoding=utf8

import base64
import json
import os
import string
import re
import argparse
import bs4

import conf
import utils
import global_vars
from flow_print_impl import *
from Token import Token, IgnoredTokenException



def isolate_requests(har_file):
    har = {}
    with open(har_file) as harfile:
        har = json.load( harfile )
        global_vars.harfile_pagetime = har['log']['pages'][0]['startedDateTime']
                                                                    # needed later on
    global_vars.req_resp = har['log']['entries']
    if global_vars.debug:
        print "[+] Read %d entries" % len(global_vars.req_resp)

    if conf.domains == []:
        fdomain = raw_input("Filter by domain? (ENTER for no): ")
        if fdomain:
            utils.filter_by(fdomain)
    else:
        print "[c] Read %d domains to filter on" % len(conf.domains)    # TODO search_all [c] when patching #25
        for fdomain in conf.domains:
            utils.filter_by(fdomain)







    no_data = raw_input("Ignore media/fonts/css/... junk? (Y/n): ")
    if no_data in ["", "y", "Y"]:
        junk_ext = [".ttf", ".woff", ".otf", ".eot",                # fonts
                    ".css", ".sass",                                # styles
                    ".img", ".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif", ".bmp", ".ico",
                    ".pdf",                                         # img / doc
                    ]                                               # media
        junk_ext += [ j.upper() for j in junk_ext ]                 # ...and .JPG has been seen


        for e in list(global_vars.req_resp):
            if 'data:' in e['request']['url']:
                global_vars.req_resp.remove(e)
                if global_vars.debug:
                    print '[+] Ingoring entry with url: '+ e['request']['url']
                continue

            for j in junk_ext:
                if j in e['request']['url']:
                    global_vars.req_resp.remove(e)
                    if global_vars.debug:
                        print '[+] Ingoring entry with url: '+ e['request']['url']

    return





def recognize_tokens():
    if global_vars.debug:
        print "[+] %d Entries in for token recognition" % len(global_vars.req_resp)
        
    global_vars.common_headers = []
    with open('common_headers.txt') as infile:
        for line in infile:
            global_vars.common_headers.append( line.lower().replace('\n','') if '#' not in line else None )
        if global_vars.debug:
            print "[+] Read in "+str(len(global_vars.common_headers))+' common headers to ignore'

    for e in global_vars.req_resp:
        recognized = 0

        try:
            ###### url params
            for p in e['request']['queryString']:
                t = Token('url', e['saphireTime'], (p['name'], p['value']))
                t.match_and_insert(global_vars.tokens)
                recognized += 1
        except IgnoredTokenException:
            pass
        except KeyError:
            pass

        try:
            ###### cookies
            if e['request']['cookies'] != []:
                for c in e['request']['cookies']:
                    t = Token('cookie', e['saphireTime'], (c['name'], c['value']))
                    t.match_and_insert(global_vars.tokens)
                    recognized += 1
            else:                                                   # check the header
                cookie_string = [ h['value'] for h in e['request']['headers'] if h['name'].lower()=='cookie' ][0]
                for c in cookie_string.split('; '):
                    t = Token('cookie', e['saphireTime'], (c.split('=')[0] , c.split('=')[1]))
                    t.match_and_insert(global_vars.tokens)
                    recognized += 1
        except IgnoredTokenException:
            pass
        except KeyError:
            pass
        except IndexError:
            pass

        try:
            ###### form fields
            if e['request']['method'] == 'POST':
                header_values = [ h['value'] for h in e['request']['headers']]
                for v in header_values:
                    if 'application/x-www-form-urlencoded' in v:    # TODO what about application/form-multipart
                        if e['request']['postData']['params'] != []:
                            for f in e['request']['postData']['params']:
                                t = Token('form', e['saphireTime'], (f['name'], f['value']))
                                t.match_and_insert(global_vars.tokens)
                                recognized += 1
                        else:
                            for f in e['request']['postData']['text'].split('&'):
                                ttuple = (f.split('=')[0], f.split('=')[1]) if '=' in f else ('',f)
                                t = Token('form', e['saphireTime'], ttuple)
                                t.match_and_insert(global_vars.tokens)
                                recognized += 1

                    if   'application/json' in v \
                      or 'application/x-javascript' in v \
                      or 'text/javascript' in v:
                        body = e['request']['postData']['text']
                        post_json = utils.get_json(body)
                        e['request']['saphireJson'] = post_json  # add the full dict, might need later...
                        count = utils.tokenize_json(post_json, 'json', e['saphireTime'])
                        recognized += count
        except IgnoredTokenException:
            pass
        except KeyError:
            pass

        try:
            ###### headers
            for h in e['request']['headers']:
                h['name'] = h['name'].lower()
                h['value']= h['value']
                if h['name'] in global_vars.common_headers:
                    continue
                t = Token('req_header', e['saphireTime'], (h['name'], h['value']))
                t.match_and_insert(global_vars.tokens)
                recognized += 1
        except IgnoredTokenException:
            pass
        except KeyError:
            pass

        try:
            for h in e['response']['headers']:
                h['name'] = h['name'].lower()
                h['value']= h['value']
                if h['name'] in global_vars.common_headers:
                    continue
                t = Token('rsp_header', e['saphireTime'], (h['name'], h['value']))
                t.match_and_insert(global_vars.tokens)
                recognized += 1

            if str(e['response']['status'])[0]=='3':
                location = [ h['value'] for h in e['response']['headers'] if h['name'].lower()=='location' ][0]
                t = Token('rsp_header', e['saphireTime'], ('location', location))
                t.match_and_insert(global_vars.tokens)
                recognized += 1
        except IgnoredTokenException:
            pass
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
                    resp_json = utils.get_json(body)
                    e['response']['saphireJson'] = resp_json        # add the full dict, might need later...
                    count = utils.tokenize_json(resp_json,'json', e['saphireTime'])
                    recognized += count
        except KeyError:
            pass


        try:
            ###### resp cookies
            if e['response']['cookies'] != []:
                for c in e['response']['cookies']:
                    t = Token('set_cookie', e['saphireTime'], (c['name'], c['value']))
                    t.match_and_insert(global_vars.tokens)
                    recognized += 1
            else:
                cookie_string = [ h['value'] for h in e['response']['headers'] if h['name'].lower()=='set-cookie' ][0]
                for c in cookie_string.split('\n'):
                    t = Token('set_cookie', e['saphireTime'], (c.split('=')[0] , c.split('=')[1].split('; ')[0]))
                    t.match_and_insert(global_vars.tokens)
                    recognized += 1
        except IgnoredTokenException:
            pass
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
                    t.match_and_insert(global_vars.tokens)
                    recognized += 1
        except IgnoredTokenException:
            pass
        except KeyError:
            pass


        try:
            ###### JWTs                                             # discovered from match_and_insert > smart_decode call from the prev. ones
            jwt_header  = e['request']['saphireJWT']['header']
            count =  utils.tokenize_json(jwt_header, 'jwt_header', e['saphireTime'])
            recognized += count
        except KeyError:
            pass

        try:
            jwt_payload = e['request']['saphireJWT']['payload']
            count = utils.tokenize_json(jwt_payload, 'jwt_payload', e['saphireTime'])
            recognized += count
        except KeyError:
            pass

        try:
            jwt_header = e['response']['saphireJWT']['header']
            count = utils.tokenize_json(jwt_header, 'jwt_header', e['saphireTime'])
            recognized += count
        except KeyError:
            pass

        try:
            jwt_payload = e['response']['saphireJWT']['payload']
            count = utils.tokenize_json(jwt_payload, 'jwt_payload', e['saphireTime'])
            recognized += count
        except KeyError:
            pass


        if global_vars.debug:
            print '[+] Recognized %d tokens in req with saphireTime %0.3f' % (recognized,e['saphireTime'])



    if global_vars.debug:
        ans = raw_input('Print 10 random tokens?(y/N): ')
        if ans=='y':
            idx = 0
            for i in range(10):
                global_vars.tokens[ idx % len(global_vars.tokens) ].dump()
                idx += 87
    return






def set_saphireTimes():
   global_vars.req_resp2 = [ e.update( {"saphireTime":utils.hartime_to_saphire(e["startedDateTime"])} )          for e in global_vars.req_resp ]







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
    parser.add_argument("-i", "--interactive", help="don't flood the terminal, print each req/resp pairs on user's prompt", action="store_true")


    args = parser.parse_args()
    if args.debug:
        global_vars.debug = True
    if args.color != None :
        global_vars.color_opt = global_vars.COLOR_OPTS[args.color]
    if args.expand:
        global_vars.xpand = args.expand
    if args.nosmart:
        global_vars.smart_decoding = False
    if args.interactive:
        global_vars.interact = True

    isolate_requests( args.harfile )
    set_saphireTimes()                                              # make new field with unique timestamp
    global_vars.req_resp = utils.sort_list_of_dicts_by_key(global_vars.req_resp,'saphireTime')
    recognize_tokens()

    graph = False                                                   # TODO make cmdline switch --flow-print vs --flow-graph (mutually_exclusive)
    if graph:
#       flow_graph()                                                # TODO gui
        pass
    else:
        flow_print()

    
