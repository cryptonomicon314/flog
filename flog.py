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


import base64
import yaml
import requests
import json
import os
import argparse

parser = argparse.ArgumentParser(description="Push data into Flog")
parser.add_argument('action')
parser.add_argument('--remote', action='store_const', const=True, default=False)


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

def authenticate(client, domain, payload):
    response = client.post(domain + api + '/auth/',
                           data=json.dumps(payload),
                           headers=headers)

    if response.status_code == 200:
        return response
    else:
        raise Exception("Authentication Failed")

def action_upload(client, meta, namemap, auth, domain):
    # TODO: Explain this
    files = dict([(os.path.split(remote)[1], base64.b64encode(open(local).read()))
        for local, remote in namemap.items()])

    response = client.post(domain + api + '/upload/' + meta['slug'],
                           data=json.dumps({'slug': meta['slug'],
                                            'files': files}),
                           headers=headers)
    return response


def create_entry(client, domain, fields):
    payload = {'fields': fields}
    return client.post(domain + api + '/entry/',
            data=json.dumps(payload),
            headers=headers)

def read_entry(client, slug, domain, fields):
    payload = {'slug': slug,
               'fields': fields}
    return client.get(domain + api + '/entry/',
                      data=json.dumps(payload),
                      headers=headers)

def update_entry(client, slug, domain, fields):
    payload = {'slug': slug,
               'fields': fields}
    return client.put(domain + api + '/entry/',
                      data=json.dumps(payload),
                      headers=headers)

def delete_entry(client, domain, slug):
    return client.delete(domain + api + '/entry/',
                         data=json.dumps({'slug': slug}),
                         headers=headers)

def upload_sidebar(client, domain, modules):
    return client.post(domain + api + '/sidebar/',
                       data=json.dumps({'modules': modules}),
                       headers=headers)

def action_sidebar(remote):
    modules, auth, domain = sidebar_process_files(remote)
    client = requests.Session()
    authenticate(client, domain, auth)
    response = upload_sidebar(client, domain, modules)
    print response.text

def action_add(remote):
    fields, namemap, auth, domain = entry_process_files(remote)
    client = requests.Session()
    authenticate(client, domain, auth)
    if namemap:
        response1 = action_upload(client, fields, namemap, auth, domain)
        try:
            print "Uploading Files..."
            if response1.json()['success']:
                print ">>> success"
        except:
            print response1.text

    response2 = create_entry(client, domain, fields)
    print "Creating Entry..."
    try:
        if response2.json()['created']:
            print ">>> success"
        else:
            print ">>> failure"
            print response2.json()['exception']
    except:
        print ">>> failed"
        print response2.text

def action_update(remote):
    fields, namemap, auth, domain = entry_process_files(remote)
    slug = fields['slug']
    client = requests.Session()
    authenticate(client, domain, auth)
    if namemap:
        response1 = action_upload(client, fields, namemap, auth, domain)
        try:
            print "Uploading Files..."
            if response1.json()['success']:
                print ">>> success"
        except:
            print response1.text

    response2 = update_entry(client, slug, domain, fields)
    print "Updating Entry..."
    try:
        if response2.json()['updated']:
            print ">>> success"
        else:
            print ">>> failure"
            print response2.json()['exception']
    except:
        print ">>> failed"
        print response2.text


VALID_FIELDS = ['author', 'show_author', 'show_date', 'title', 'slug', 'public', 'tags',
'category', 'commentable', 'unlocked', 'created', 'since', 'until',
'archivable', 'content', 'lead']

def validate(d):
    for key in d:
        try:
            assert key in VALID_FIELDS
        except Exception as e:
            print key
            raise e

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

    meta = yaml.safe_load(open(meta_path).read())
    _content = open(content_path).read()

    split = _content.split('\n<<< >>>\n', 2)
    if len(split) == 1:
        content, namemap = fix_refs(meta['slug'], markjax(_content))
        meta['content'] = content
        meta['lead'] = u''
    elif len(split) == 2:
        lead, lead_namemap = fix_refs(meta['slug'], markjax(split[0]))
        content, content_namemap = fix_refs(meta['slug'], markjax(split[1]))
        meta['lead'], meta['content'] = lead, content
        # **!!!** dict1.update(dict2) returns None!
        lead_namemap.update(content_namemap)
        namemap = lead_namemap
    else:
        raise Exception('Invalid Division between text and lead')

    auth, domain = get_credentials(remote)

    validate(meta)
    return (meta, namemap, auth, domain)

from bs4 import BeautifulSoup

ENTRY_FILE_UPLOAD_URL_BASE = '/static/uploads/entry'

import hashlib

def fix_refs(entry_slug, doc, debug=False):
    soup = BeautifulSoup(doc)
    namemap = {}
    # Fix <img src="files/filename.ext"/>
    for img in soup.find_all('img'):
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

if __name__ == "__main__":
    args = parser.parse_args()
    if args.action == 'add':
        action_add(args.remote)
    elif args.action == 'update':
        action_update(args.remote)
    elif args.action == 'sidebar':
        action_sidebar(args.remote)
