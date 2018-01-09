import termcolor
import json

import utils
import smart_decoder
import global_vars
import conf


class Token:
    fg_colors = ['red', 'green', 'yellow',
                 'blue', 'magenta', 'cyan', 'white']
    bg_colors = ['on_' + fc for fc in fg_colors]
    types = ['url',
             'cookie', 'set_cookie',
             'req_header', 'rsp_header',
             'form',
             'json', 'jwt_header', 'jwt_payload',
             'html']
    fc = 0                                                          # static =class-scoped counter for fg color idx in array





    def __init__(self, ttype, ttime, ttuple):
        """
        Token() constructor. Trows a custom Exception when token should be ignored

        :param ttype: A value from the types list in the attribute
        :param ttime: The saphireTime of the request that contains it (Foreign Key - like)
        :param ttuple: Could be one of:
            - (type,name,id)    for some 'html' type of Tokens
            - (type,name)       for the rest of  'html' type of Tokens
            - ('', value)       for 'json' and some 'form' type Tokens
            - (key,value)       else, for most tokens
        """
        if len(ttuple)==3:                                          # code repetition - Issue #26
            if ttuple[1] in conf.ignore_tokens_with_keys:
                raise IgnoredTokenException
        elif ttuple[0]=='':
            if ttuple[1] in conf.ignore_tokens:
                raise IgnoredTokenException
        else:
            if ttuple[0] in conf.ignore_tokens_with_keys \
            or ttuple[1] in conf.ignore_tokens:
                raise IgnoredTokenException

        self.tuple = ttuple
        if ttype not in Token.types:
            exit('Unsupported type \'' + ttype + '\'!')
        self.type = ttype
        self.time = ttime  # saphireTime
        self.fcolor = ''





    def dump(self):
        dictified = {
            'type': self.type,
            'time': self.time,
            'tuple': self.tuple,
        }
        print json.dumps(dictified, indent=4, sort_keys=True)




    def match_and_insert(self, array):
        """
        array.append() encapsulated in the Token object to add custom actions,
        for every new token: Here's what it does:
        1.  Search if it has pre-occured and color accordingly
        2.  Smart decode (inspired by Burp)
        """

        ##### Smart decoding
        do_decode = self.tuple[0] not in conf.no_decode_keys and self.tuple[1] not in conf.no_decode
        decode_key   = self.tuple[0] and global_vars.smart_decoding and do_decode
        decode_value = self.tuple[1] and global_vars.smart_decoding and do_decode
        key   = self.smart_decode(self.tuple[0]) if decode_key   else self.tuple[0]
        value = self.smart_decode(self.tuple[1]) if decode_value else self.tuple[1]

        self.tuple = (key, value) if len(self.tuple) == 2 else (key, value, self.tuple[2])

        ##### Match Coloring
        if self.type != 'html' and self.tuple[1]:                   # Don't color 'html' <input fields or empty tokens
            if global_vars.coloring:

                if global_vars.conf_has_color_only:                 # If conf explicitly states which to color, find it inside
                    proceed = False
                    if len(self.tuple) == 3:                            # code repetition - Issue #26
                        if self.tuple[1] in conf.only_color_tokens_with_keys:
                            proceed = True
                    elif self.tuple[0] == '':
                        if self.tuple[1] in conf.only_color_tokens:
                            proceed = True
                    else:
                        if self.tuple[0] in conf.only_color_tokens_with_keys \
                        or self.tuple[1] in conf.only_color_tokens:
                            proceed = True
                                                                    # It doesnt? -> Go on! | It does? ->  Found?
                if (not global_vars.conf_has_color_only) or proceed:
                    same = False
                    for t in array:
                        if self.tuple[1] == t.tuple[1]:
                            same = True
                            if t.fcolor:
                                self.fcolor = t.fcolor
                            else:                                   # new color for both New...
                                self.fcolor = Token.fg_colors[Token.fc]
                                t.fcolor = self.fcolor
                                Token.fc = (Token.fc + 1) % len(Token.fg_colors)
                                                                    # ...and Old
                    if not same:
                        self.fcolor = ''

        array.append(self)




    def smart_decode(self, text):
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

            if text in conf.b64_tokens                             \
            or self.tuple[0] in conf.keys_of_b64_tokens and text==self.tuple[1]:
                text = smart_decoder.base64decode(text)             # 0. Explicit rule > b64
                transformation_chain += 'b64 '
                did_transformation = True
                if global_vars.coloring:
                    text = termcolor.colored(text, attrs=['underline'])

            if smart_decoder.is_urlencoded(text) == 1:              # 1. URL encoding
                text = smart_decoder.urldecode(text)
                transformation_chain += 'url '
                did_transformation = True

            if 'yes' in smart_decoder.is_b64encoded(text):          # 2. Base 64
                text = smart_decoder.base64decode(text)
                transformation_chain += 'b64 '
                did_transformation = True
                if global_vars.coloring:
                    text = termcolor.colored(text, attrs=['underline'])

            if smart_decoder.is_timestamp(text):                    # 3. Timestamp
                text = utils.timestamp_to_hartime(text)
                transformation_chain += 'timestamp '
                did_transformation = False                          # decode no further
                if global_vars.coloring:
                    text = termcolor.colored(text, attrs=['underline'])

            if smart_decoder.is_jwt(text):                          # 4. JSON Web Token
                text = smart_decoder.jwt_decode(text)
                jwt_header = text.split(global_vars.JWT_PAYLOAD_TAG)[0].replace(global_vars.JWT_HEADER_TAG, '')
                jwt_payload = text.split(global_vars.JWT_PAYLOAD_TAG)[1]
                e = [r for r in global_vars.req_resp if r['saphireTime'] == self.time][0]
                                                                    # find token's origin request, by its time
                if self.type in ['url', 'cookie', 'req_header', 'form']:
                    e = e['request']                                # was the JWT found in the request or the response?
                else:
                    e = e['response']

                e['saphireJWT'] = {}                                # set the 2 dicts, will be recognized() later...
                try:
                    e['saphireJWT']['header'] = json.loads(jwt_header)
                except ValueError:                                  # no valid json in JWT, never mind
                    pass
                try:
                    e['saphireJWT']['payload'] = json.loads(jwt_payload)
                except ValueError:
                    pass

                transformation_chain += 'jwt '
                did_transformation = True
                if global_vars.coloring:
                    text = termcolor.colored(text, attrs=['underline'])

            if did_transformation == False:
                break

        if global_vars.debug and transformation_chain:
            try:
                print "[+] Applied transformations: %s. '%s' -> '%s'" % (transformation_chain, orig_text, text)
            except UnicodeDecodeError:
                pass

        return text


class IgnoredTokenException(Exception):
    pass