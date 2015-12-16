#!/usr/bin/python
# -*- coding: utf-8 -*-

from markdown2 import markdown
from markdown2Mathjax import sanitizeInput, reconstructMath

inline_delims = ['\\(', '\\)']

def markjax(text):
    tmp = sanitizeInput(text, inline_delims=inline_delims)
    mkd_text = markdown(tmp[0],
        extras=['code-friendly', 'fenced-code-blocks', 'footnotes',
                'metadata', 'smarty-pants', 'tables'])
    output = reconstructMath(mkd_text, tmp[1], inline_delims)
    return output

import string
import hashlib
import base64
import yaml
import requests
import json
import os
import argparse
from bs4 import BeautifulSoup


def isroot(path):
    return os.path.normpath(path) == os.path.abspath(os.sep)

def isempty(path):
    return os.path.normpath(path) == ''

def walkback(path, from_parent=False):
    # Handle redundant patterns and separators like '/home/user/..'
    normpath = os.path.normpath(path)

    if os.path.isdir(path):
        if from_parent:
            directory = os.path.dirname(normpath)
        else:
            directory = normpath
    else:
        directory = os.path.dirname(normpath)
    # Loop until either:
    # 1) we have reached the root of the filesystem
    # (the end of an absolute path)
    # 2) we have reached an empty path
    # (the end of a relative path)
    #
    # The empty path or the path to the root are still yielded,
    # (only once, since we interrupt the loop)
    while True:
        yield directory
        if isroot(directory) or isempty(directory):
            # Now that we have already yielded the
            # path to the root or the empty path, we
            # terminate the loop.
            # This is done to make sure these paths
            # are yielded only once, instead of entering
            # an infinite cycle.
            return
        directory = os.path.dirname(directory)

api = '/client/api/v1'
headers = {'content-type': 'application/json'}
crawler_headers = {'User-Agent': 'Mozzilla/5.0'}

def authenticate(client, domain, payload):
    response = client.post(domain + api + '/auth/',
                           data=json.dumps(payload),
                           headers=headers)

    if response.status_code == 200:
        return response
    else:
        raise Exception("Authentication Failed")

def action_upload(client, slug, fields, namemap, auth, domain):
    # TODO: Explain this
    files = dict([(os.path.split(remote)[1], base64.b64encode(open(local).read()))
        for local, remote in namemap.items()])

    response = client.post(domain + api + '/upload/' + slug,
                           data=json.dumps({'slug': slug,
                                            'files': files}),
                           headers=headers)
    return response


def action_sidebar(remote):
    modules, auth, domain = sidebar_process_files(remote)
    client = requests.Session()
    authenticate(client, domain, auth)
    response = client.post(domain + api + '/sidebar/',
                           data=json.dumps({'modules': modules}),
                           headers=headers)
    return handle_response(response)

def handle_response(response):
    try:
        if response.json()['success']:
            print ">>> success"
            return True
        else:
            print ">>> failure"
            print response.json()['exception']
            return False
    except:
        print ">>> failed"
        print response.text
        return False

def action_update(remote, check_dead_links=True):
    slug, fields, namemap, auth, domain = entry_process_files(remote)
    client = requests.Session()
    authenticate(client, domain, auth)
    if namemap:
        response_upload = action_upload(client, slug, fields, namemap, auth, domain)
        handle_response(response_upload)

    if check_dead_links:
        meta = yaml.safe_load(fields['meta'])
        is_public = meta['public']
        meta['public'] = False
        fields['meta'] = yaml.dump(meta)

    print "Updating Entry..."

    payload = {'slug': slug,
               'meta': fields['meta'],
               'lead': fields['lead'],
               'content': fields['content']}
    response_update = client.post(domain + api + '/entry/',
                                  data=json.dumps(payload),
                                  headers=headers)

    if check_dead_links:
        print "Checking links..."
        log, correct = check_links(slug, auth, domain, fields['lead'], fields['content'])
        if correct:
            if is_public:
                print "All Links correct. Will upload public version."
                return action_update(remote, False)
            else:
                print "All links correct."
        else:
            print_errors(log)
            return None


    return handle_response(response_update)

import urlparse
def is_absolute(url):
    return bool(urlparse.urlparse(url).netloc)

from colorama import Fore, Back, Style
def print_errors(errors):
    for error in errors:
        print (Fore.RED + "Error:" + Style.RESET_ALL)
        print (Style.RESET_ALL + "  URL: " + Fore.YELLOW + error['url'] + Style.RESET_ALL)
        if 'status_code' in error:
            print ("  Response " + Fore.YELLOW + "[" + str(error['status_code']) + "]" + Style.RESET_ALL)
        elif 'exception' in error:
            mess = str(error['exception'].message)
            lines = mess.split(': ')
            print ("  Exception: " + Fore.YELLOW)
            for i, line in enumerate(lines):
                print Fore.YELLOW + "    " + ("  " * i) + line + ":" + Style.RESET_ALL

# TODO: check links to preview entries
def check_links(slug, auth, domain, lead, content):
    client = requests.Session()
    authenticate(client, domain, auth)
    errors = []
    for doc in [lead, content]:
        soup = BeautifulSoup(doc)
        for tag in soup.find_all(True):
            for attr in ['src', 'href', 'link', 'url']:
                if attr in tag.attrs:
                    if tag[attr].startswith('mailto:'):
                        pass
                    else:
                        new_url = handle_url(slug, domain, tag[attr])
                        try:
                            response = client.get(new_url, headers=crawler_headers)
                            if response.status_code != 200:
                                errors.append({'tag': str(tag),
                                               'url': tag[attr],
                                               'status_code': response.status_code})
                        except Exception as e:
                            errors.append({'tag': str(tag),
                                           'url': tag[attr],
                                           'exception': e})
    if errors: correct = False
    else:      correct = True

    return errors, correct

def handle_url(slug, domain, url):
    relative_base_url = domain + '/preview/entry/'
    entry_preview_url = relative_base_url + slug

    if is_absolute(url):
        return url
    elif url.startswith('/'):
        return urlparse.urljoin(domain, url)
    elif url.startswith('#'):
        return urlparse.urljoin(entry_preview_url, url)
    else:
        return urlparse.urljoin(relative_base_url, url)


def get_credentials(remote):
    cred_path = None
    for path in walkback(os.getcwd()):
        candidate = os.path.join(path, 'credentials.yaml')
        if os.path.isfile(candidate):
            cred_path = candidate
            break

    if cred_path is None:
        raise Exception("No 'credentials.yaml' file found!")

    cred = yaml.safe_load(open(cred_path).read())

    if remote:
        domain = cred['remote-domain']
    else:
        domain = cred['local-domain']

    auth = {'username': cred['username'],
            'password': cred['password']}

    return auth, domain

def sidebar_process_files(remote):
    cwd = os.getcwd()
    modules_path = os.path.join(cwd, 'sidebar.yaml')

    modules = yaml.safe_load(open(modules_path).read())
    for module in modules:
        module['text'] = markjax(module['text'])
        try:
            module['visible'] = bool(module['visible'])
        except:
            pass

    auth, domain = get_credentials(remote)

    return (modules, auth, domain)

def entry_process_files(remote):
    cwd = os.getcwd()
    meta_path = os.path.join(cwd, 'meta.yaml')
    content_path = os.path.join(cwd, 'content.md')

    entry_path = os.path.join(cwd, 'entry.md')

    _, rest = open(entry_path).read().split('---\n', 1)
    raw_meta, text = rest.split('\n---\n', 1)
    meta = yaml.safe_load(raw_meta)
    slug = meta['slug']

    try:
        lead, content = string.split(text, '<!--more-->', maxsplit=2)
    except:
        lead, content = u'', text

    raw_meta = yaml.dump(meta)

    content, namemap = fix_refs(slug, markjax(content))
    lead, lead_namemap = fix_refs(slug, markjax(lead))
    namemap.update(lead_namemap)

    fields = {'meta': raw_meta, 'lead': lead, 'content': content}
    auth, domain = get_credentials(remote)
    return (slug, fields, namemap, auth, domain)


ENTRY_FILE_UPLOAD_URL_BASE = '/static/uploads/entry'

def fix_refs(entry_slug, doc, debug=False):
    soup = BeautifulSoup(doc)
    namemap = {}
    # Fix <img src="files/filename.ext"/>
    for img in soup.find_all(['img', 'source', 'audio']):
        # Files specific for this entry:
        if img['src'].startswith('files/'):
            local = img['src']
            # Hardcore "cache busting"
            content = open(os.path.join(os.getcwd(), local)).read()
            fname = os.path.basename(local)
            remote = '{}/{}/{}'.format(ENTRY_FILE_UPLOAD_URL_BASE, entry_slug, fname)
            remote_base, remote_ext = os.path.splitext(remote)
            # ext includes the dot (e.g. ext = '.png')
            remote = '{base}.{hash}{ext}'.format(
                            base=remote_base,
                            hash=hashlib.sha1(content).hexdigest()[:8],
                            ext=remote_ext)
            img['src'] = remote
            namemap[local] = remote

    if debug:
        print soup.prettify()
    return unicode(soup), namemap

parser = argparse.ArgumentParser(description="Push data into Flog")
parser.add_argument('--entry', action='store_const', const=True, default=False)
parser.add_argument('--sidebar', action='store_const', const=True, default=False)
parser.add_argument('--remote', action='store_const', const=True, default=False)
parser.add_argument('--nocheck', action='store_true', default=False)

if __name__ == "__main__":
    args = parser.parse_args()
    if args.sidebar:
        action_sidebar(args.remote)
    else:
        action_update(args.remote, not args.nocheck)
