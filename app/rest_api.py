from app import app, db, appbuilder, csrf
from models import Entry, Author, Tag, Category, SidebarModule
import query

from werkzeug import secure_filename
import flask.json as json
from flask import request, make_response

from flask.ext.appbuilder import has_access, expose, BaseView
from flask.ext.login import login_user

import base64
import os
from datetime import datetime
import yaml

PRIVATE = app.config['PAGE_VERSION_PRIVATE']

class ClientApi(BaseView):
    route_base = '/client/api/v1'

    # The ``@csrf.exempt`` decorate bypasses ``wtform``'s CRSF protection
    # on POST requests.
    #
    # We have to disable it to be able to use the HTML methods as a REST API.
    @csrf.exempt
    @expose('/auth/', methods=['POST'])
    def auth(self):
        username = request.json.get('username')
        password = request.json.get('password')
        # ``appbuilder.sm`` is a ``SecurityManager``, responsible for adding
        # and authenticationg Users.
        user = appbuilder.sm.auth_user_db(username, password)
        if user:
            # Use the ``LoginManager`` to login the User.
            #
            # You login the user by adding a special cookie to
            # the session, which will be remembered by the client.
            login_user(user)
            return make_response(json.jsonify(success=True), 200)
        else:
            # If you can't authenticate the user, return a 403 error code:
            return make_response(json.jsonify(success=False), 403)

    @csrf.exempt
    @has_access
    # For simplicity, we only allow a POST method to
    # build the sidebar. You don't actually "edit" the sidebar.
    # You just delete the old one and upload the new one with
    # a POST request.
    @expose('/sidebar/', methods=['POST'])
    def sidebar(self):
        if request.method == 'POST':
            modules = request.json.get('modules')
            # Delete all sidebar modules
            num_deleted = db.session.query(SidebarModule).delete()
            for index, m in enumerate(modules):
                try:
                    visible = m['visible']
                except:
                    # If the ``visible`` field is not supplied,
                    # it is False by default
                    visible = False
                # Build a new SidebarModule
                module = SidebarModule(title=m['title'],
                                       visible=visible,
                                       text=m['text'],
                                       index=index)
                db.session.add(module)
            # Commit the changes. If it fails, we send the error message
            # to the client.
            try:
                db.session.commit()
                return json.jsonify({'success': 'True'})
            except Exception as e:
                return json.jsonify({'success': 'False',
                                     'error': str(e)})



    @csrf.exempt
    @has_access
    @expose('/entry/', methods=['GET', 'PUT', 'POST', 'DELETE'])
    def entry(self):
        # We use HTML methods as usually for a CRUD interface:
        #
        # - ``POST``: Create
        # - ``GET``: Read
        # - ``PUT``: Update
        # - ``Delete``: Delete
        if request.method in ['GET', 'DELETE', 'PUT']:
            slug = request.json.get('slug')
            e = query.entry(slug, True)
            # You can't add a new entry with the same slug
            if e is None:
                return make_response(json.jsonify({}), 404)
        # Get entry
        if request.method == 'GET':
            fields = request.json.get('fields')
            d = obj_get_from(e, fields)
            return json.jsonify(d)

        # Delete entry
        elif request.method == 'DELETE':
            db.session.delete(e)
            return json.jsonify({'success': True})

        # Create Entry / Update Entry
        elif request.method == 'POST':
            e = Entry()
            data = request.get_json()
            fields = parse_fields(db, data)
            # Set the object attributes to the JSON dict values.
            obj_set_from(e, fields)
            try:
                db.session.add(e)
                db.session.commit()
                return json.jsonify({'success': True})
            except Exception as exception:
                db.session.rollback()
                slug = data['slug']
                e = query.entry(slug, True)
                fields = parse_fields(db, data)
                # Set the object attributes to the JSON dict values.
                obj_set_from(e, fields)
                db.session.commit()
                return json.jsonify({'success': True})

        # Update Entry
        elif request.method == 'PUT':
            # fields = parse_fields(db, meta, lead, content)
            fields = parse_fields(db, request.get_json())
            # Set the object attributes to the JSON dict values.
            obj_set_from(e, fields)
            db.session.commit()
            return json.jsonify({'success': True})

        else:
            return {}

    @csrf.exempt
    @has_access
    @expose('/upload/<entry_slug>', methods=['POST'])
    # Upload image files
    #
    # This is currently inefficient, as all files are
    # deleted and replaced by the new version.
    #
    # This is not as wasteful as it seems, as
    # the operations is not frequent, and the data transfer
    # is similar to what the browser downloads each time
    # a user requests a page.
    #
    # I'm not planning on optimizing this further soon.
    def upload(self, entry_slug):
        UPLOAD = app.config['ENTRY_FILES_UPLOAD_FOLDER']
        entry_upload_folder = os.path.join(UPLOAD, entry_slug)
        # Create the folder if it doesn't exist already.
        if not os.path.exists(entry_upload_folder):
            # ``os.makedirs()`` creates all intermediate directories
            os.makedirs(entry_upload_folder)
        # Clean the old files (this is inefficient; it may be optimized)
        for fname in os.listdir(entry_upload_folder):
            os.remove(os.path.join(entry_upload_folder, fname))
        #
        for name, data in request.json.get('files').items():
            # always use ``werkzeug``'s ``secure_filename()`` function
            fname = secure_filename(name)
            # decode the base64 contents and write them to disk:
            f = open(os.path.join(entry_upload_folder, fname), 'w')
            f.write(base64.b64decode(data))
            f.close()
        return json.jsonify({'success': 'true'})

# Use ``setattr`` to add values to an ``object`` from a ``dict``
def obj_set_from(obj, d):
    for key, val in d.items():
        setattr(obj, key, val)
    return obj

# Get the values of an objects attributes by passing a list of
# strings with their names. Uses ``getattr``
#
# ``setattr`` and ``getattr```are the python programmer's best friends
def obj_get_from(obj, keys):
    d = {}
    for key in keys:
        d[key] = getattr(obj, key)
    return d

# Do not allow the creating of categories from he client.
# Categories must be created from the Admin interface.
# I might add support for adding categories from the client
# in the future
def category_from_name(db, name):
    category = query.category(name)
    if category:
        return category
    else:
        raise Exception("That category does not exist. Please create it")

# Allow adding a new author from the cient, if the supplied
# author name doesn't exist yet.
# It is not that useful, but it's easy to implement.
def author_from_name(db, name):
    author = query.author(name)
    if author:
        return author
    else:
        author = Author(name=name)
        db.session.add(author)
        db.session.commit()
        return author

# Allow adding new tags from names thad don't exist yet
# (like ``author_from_name`` above.
def tags_from_names(db, tagname_list):
    tags = []
    for tagname in tagname_list:
        tag = query.tag(tagname)
        if tag:
            tags.append(tag)
        else:
            tag = Tag(name=tagname, slug=to_slug(tagname))
            db.session.add(tag)
            db.session.commit()
            tags.append(tag)
    return tags

def to_slug(name):
    """Convert a name into a slug"""
    # has to be improved. It is not foolproof yet.
    return name.lower().replace(' ', '-')

def parse_fields(db, data):
    """Parse all fields from the JSON dict, creating new ``Author``s
    and ``Tag``s as needed. Don't creaet new categories"""
    meta, lead, content = data['meta'], data['lead'], data['content']
    fields = yaml.safe_load(meta)
    fields['lead'], fields['content'] = lead, content

    if 'author' in fields:
        fields['author'] = author_from_name(db, fields['author'])
    if 'tags' in fields:
        fields['tags'] = tags_from_names(db, fields['tags'])
    if 'category' in fields:
        fields['category'] = category_from_name(db, fields['category'])

    return fields

