##### All the functions needed to output on the terminal
import os
import termcolor
import string
import urlparse
import unicodedata
import StringIO
import pprint
import re

import global_vars
import Token


def flow_print():
    columns = 0
    try:
        columns = int(os.popen('stty size', 'r').read().split()[1])
    except IndexError:                                              # if the 'stty' trick won't work inside the IDE (or for any other reason),
        columns = 250                                               # work around with a fixed value

    divider = 50
    if global_vars.debug:
        ans = raw_input(termcolor.colored('Enter req/resp divid er pct. (ENTER -> default=50%): ', color='yellow'))
        if ans:
            divider = int(ans)
            print "Divider set to %d" % divider

    req_thres = int(divider / 100.0 * columns)
    resp_offset = int(divider / 100.0 * columns) + 1
    if global_vars.debug:
        print "Request-info will span %d/%d chars. Responses start on %d" % (req_thres, columns, resp_offset)

    max_len = 25                                                    # limit the length of tokens displayed, need to print as much as we can
    if global_vars.xpand == global_vars.XPAND_HORZ:                 # only used in XPAND_HORZ
        if global_vars.debug:                                       # for a short, cool demonstration. Not the full value of it! (do this later manually)
            ans = raw_input(termcolor.colored('Enter maximum characters of tokens to be shown. (ENTER -> default=25)', color='yellow'))
            if ans:
                max_len = int(ans)
                print "Max len set to %d" % max_len

    for i in range(len(global_vars.req_resp)):
        e = global_vars.req_resp[i]                                 # "startedDateTime": "2017-10-30T20:29:41.816Z"
        req_tokens_by_type = {}
        for cur_type in Token.Token.types:
            req_tokens_by_type[cur_type] = []                       # will group tokens by type (init arrays)

        any_tokens = False
        for t in global_vars.tokens:
            if t.time == e['saphireTime']:                          # filter tokens by request-time (keep only the ones of current global_vars.req_resp)
                any_tokens = True
                req_tokens_by_type[t.type].append(t)

        if not any_tokens:
            continue

        ##### Request
        fit_print('_' * 500, 0, req_thres, True)
        line = "%10s|%s (saphireTime:%0.3f)" % ('#' + str(i), e['startedDateTime'][11:22], e['saphireTime'])
        fit_print(line, 0, req_thres)
        u = urlparse.urlparse(e['request']['url'])
        line = "%10s|%s %s" % (e['request']['method'], u.netloc, u.path)
        fit_print(line, 0, req_thres)

        fit_print('-' * 10 + '+' + '-' * 500, 0, req_thres)
        for t_type in ['url', 'cookie', 'req_header', 'form', 'json', 'jwt_header', 'jwt_payload']:
            if global_vars.xpand == global_vars.XPAND_HORZ:
                print_xpanding_horz(req_tokens_by_type, t_type, max_len,
                                    columns, req_thres, resp_offset, True)

            elif global_vars.xpand == global_vars.XPAND_VERT:
                print_xpanding_vert(req_tokens_by_type, t_type,
                                    columns, req_thres, resp_offset, True)

        fit_print('_' * 500, 0, req_thres, True)

        ##### Response
        fit_print('_' * 500, resp_offset, columns - 2, True)
        if e['response']['status'] == 0:
            e['response']['status'] = ''
            e['response']['statusText'] = 'CANCELED'
        line = "%4s %s" % ( str(e['response']['status']), e['response']['statusText'])
        fit_print(line, resp_offset, columns - 2)
        fit_print('-' * 500, resp_offset, columns - 2)

        for t_type in ['rsp_header', 'set_cookie', 'json', 'html', 'jwt_header', 'jwt_payload']:
            if global_vars.xpand == global_vars.XPAND_HORZ:
                print_xpanding_horz(req_tokens_by_type, t_type, max_len,
                                    columns, req_thres, resp_offset, False)

            elif global_vars.xpand == global_vars.XPAND_VERT:
                print_xpanding_vert(req_tokens_by_type, t_type,
                                    columns, req_thres, resp_offset, False)

        fit_print('_' * 500, resp_offset, columns - 2, True)
        print '\n'

        if global_vars.interact:
            # TODO add clause for curl-generation when implemented
            if i < len(global_vars.req_resp) - 1:
                _ = raw_input('Press any key to continue... ')


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
                           % (key, value, ("id=" + rtc.tuple[2]) if len(rtc.tuple) == 3 else '')
        elif t_type in ['json', 'jwt_header', 'jwt_payload']:
            colord_token = "%s" % value
        else:
            colord_token = "%s=%s" % (key, value)
        if global_vars.coloring:
            if rtc.fcolor:                                          # even in coloring mode, some tokens are not colored!
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
        e = [r for r in global_vars.req_resp if r['saphireTime'] == saphireTime_of_source_request][0]
        full_json = object()
        if t_type == 'json':
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
        string_io = [sl for sl in StringIO.StringIO(pprint.pformat(full_json))]
        for j in range(len(string_io)):
            repr_line = string_io[j]

            for m in re.findall(r"u'[^']*'", repr_line):
                repr_line = repr_line.replace(m, m[1:])             # strip the unicode tags from u'XXX'

            if global_vars.coloring:
                for rtc in req_tokens_by_type[t_type]:              # search in json tokens and color inside the pretty_print
                    if rtc.fcolor and rtc.tuple[1] in repr_line:

                        if rtc.tuple[1] in ' '.join(COLOR_PREFIXES + COLOR_ATTR_PREFIXES):
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
        if global_vars.coloring:
            if rtc.fcolor:                                          # in try-match mode some tokens are not colored!
                colord_token = termcolor.colored(colord_token, rtc.fcolor)

        if is_request:
            fit_print(line + colord_token, 0, req_thres)
        else:
            fit_print(line + colord_token, resp_offset, columns - 2)


COLOR_PREFIXES = ["\033[%dm" % n for n in range(30, 48)]            # colors like 'red'
COLOR_ATTR_PREFIXES = ["\033[%dm" % n for n in range(1, 9)]         # attrs like 'underline'
def is_colored(text):
    for pre in COLOR_PREFIXES + COLOR_ATTR_PREFIXES:
        if pre in text:
            return True
    return False





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





