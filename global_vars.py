

####### GLOBALS (default values if not specified on cmdline)

common_headers = []
req_resp = []
tokens = []
harfile_pagetime = ''
debug = False
interact = False
smart_decoding = True

COLOR_OPTS=['off','by-type','try-match','try-match-all']
color_opt = COLOR_OPTS[2]

(XPAND_HORZ, XPAND_VERT)= ('h','v')
xpand = XPAND_VERT

JWT_PAYLOAD_TAG = u', PAYLOAD='
JWT_HEADER_TAG  = u'JWT:HEADER='