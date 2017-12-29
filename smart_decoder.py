import urllib
import string
import base64
import json
import enchant.tokenize
import unicodedata



from utils import *
import global_vars
import flow_print_impl


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
    for c in ts_string:
        if not c.isdigit():
            return False

    in_year = 0
    try:
        in_year = time.gmtime(int(ts_string)).tm_year
    except ValueError:
        return False

    harfile_struct = time.strptime( global_vars.harfile_pagetime.split('.')[0], "%Y-%m-%dT%H:%M:%S")
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
    """
    Custom method to decode JWT without signature verification.

    Existing libraries wouldn't work because they don't support non-standard payloads,
    here we don't know what to expect so e.g. non-unicode characters could be encountered
    """
    parts = text.split('.')
    ret =  global_vars.JWT_HEADER_TAG+ unicode(base64.urlsafe_b64decode(str(parts[0]+'===')), errors='ignore')
    ret += global_vars.JWT_PAYLOAD_TAG + unicode(base64.urlsafe_b64decode(str(parts[1]+'===')), errors='ignore')
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
        if unicodedata.category(c) in flow_print_impl.UNICODE_NONPRINTABLE_CATEGORIES:
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

