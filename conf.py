#encoding=utf8


##### FILTER BY DOMAIN
# only keep the requests with a URL including any of the strings
# in the dict below. Will not prompt at runtime if not empty.
domains = [
    # 'example.com',
    # '/api/session'
]



##### FORCE NOT DECODE
# never smart-decode the (values of) tokens with following keys/values
# useful for ones that smart-decoder mistakenly identified as e.g. base64 / timstamps and messed ud
no_decode = [
    '1512588272587',
]

no_decode_keys = [
    'x-fb-debug',
]

################ Following conf options not yet suported. Sorry :P

##### FORCE DECODE
# for tokens with the following values that should always be
# auto-decoded but smart-decoder failed to recognise as base64 encoded ones.
b64_tokens = [
    # 'TmV2ZXIgZ29ubmEgZ2l2ZSB5b3UgdXA=',
    # 'TmV2ZXIgZ29ubmEgbGV0IHlvdSBkb3du',
]

# for tokens with the following keys that should always be
# auto-decoded but SAPhIRE failed to recognise as base64 encoded ones.
# e.g. Auto-decode the Cookie token PHPSESSID=eydhZG1pbic6RmFsc2UsaWQ6ODcsJ3VzZXJuYW1lJzonZmxhcHRzYWsnfQ==
#      as base64:                   PHPSESSID="{'admin':False,id:87,'username':'flaptsak'}"
keys_of_b64_tokens = [
    # 'PHPSESSID',
]







##### IGNORE TOKENS
# don't bother smart-decoding / parsing / matching / coloring tokens
# with the following values or keys (next dict)
ignore_tokens = [
    'utf-8',
    '✓',
    'en-US',
]

ignore_tokens_with_keys = [
    'encoding',
    'locale',
    'lang',
]



##### ONLY COLOR
# color nothing but the tokens having a key/value in the ones below.
# If both dicts are empty, normal coloring occurs
only_color_tokens = [

]

only_color_tokens_with_keys = [
    # 'username',
    # 'password',
]





