import bleach
from flask import Markup

def format_datetime(attr):
    def inner(c,v,m,n):
        try: return getattr(m, attr).replace(microsecond=0)
        except: return None
    return inner

def format_richtext(attr):
    def inner(c,v,m,n):
        try: return Markup(getattr(m, attr))
        except: return None
    return inner


def format_bool(val):
    if val == True:
        return Markup('<div style="text-align: center; font-size:large; font-weight:bold; color:green">&#x2714;</div>')
    elif val == False:
        return Markup('<div style="text-align: center; font-size:large; font-weight:bold; color:red">&#x2716</div>')
    elif val is None:
        return "-"

def bool_as_lock(val):
    if val == True:
        return Markup('<div style="text-align: center; font-size:large; color:green"><i class="fa fa-unlock"></i></div>')
    elif val == False:
        return Markup('<div style="text-align: center; font-size:large; color:red"><i class="fa fa-lock"></i></div>')
    elif val is None:
        return "-"

def bool_as_special(val):
    if val == True:
        return Markup('<div style="text-align: center; font-size:large; color:orange;"><i class="fa fa-star"></i></div>')
    elif val == False:
        return ""
    elif val is None:
        return "-"


TAGS_WHITELIST = ['a', 'br', 'div',
                  'strong', 'em',
                  'sup', 'sub',
                  'pre', 'code', 'var',
                  'section', 'header', 'cite', # footnotes
                  'span', # used by the mathjax plugin
                  'blockquote', # used by the blockquote plugin
                  'b', 'i', 'p',
                  's', # strikethrough
                  'ol', 'ul', 'li']

ATTRIBUTES_WHITELIST = {
        'a': ['href'],
        '*': ['class']
    }

# Strip all tags using the ``bleach`` library
def sanitize_plaintext(text, strip=True):
    return bleach.clean(text, [], [])

# Sanitize rich text using the ``bleach`` library
def sanitize_richtext(text, strip=False):
    return bleach.clean(text, TAGS_WHITELIST, ATTRIBUTES_WHITELIST)
