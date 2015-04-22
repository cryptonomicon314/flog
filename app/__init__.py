import logging
from flask import Flask, Blueprint,  url_for, redirect, g, request
# Bundle assets for cache busting:
from flask.ext.assets import Environment, Bundle
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CsrfProtect
from flask.ext.script import Manager, Command, Option
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.moment import Moment

from flask.ext.appbuilder import SQLA, AppBuilder
from flask.ext.appbuilder.baseviews import BaseView, expose

from akismet import Akismet

from dirtools import Dir
import shutil
import os
import subprocess

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.DEBUG)



class NewIndexView(BaseView):
    route_base = ''
    default_view = 'index'

    @expose('/')
    def index(self):
        # This method redirects the user to a different page depending on
        # whether the user is authenticated or not:
        self.update_redirect
        if g.user is not None and g.user.is_authenticated():
            if g.user.role.name != app.config['AUTH_ROLE_PUBLIC']:
                return redirect(url_for('UserDBModelView.show', pk=g.user.id))
        else:
            return redirect(url_for('PublicView.home'))

# This class manages a directory tree of files whose name
# can't be changed, because they depend on each other.
# This means we can't user ordinary techniques for cache busting,
# because they involve changing the name of the file.
class AssetDirTree(object):

     def __init__(self, app, src, dst):
        """src is absolute and dst is relative to the app's static_folder """
        static_folder = app.static_folder
        # Add "cache busting" without flask.assets
        abs_src = os.path.join(static_folder, src)
        abs_dst = os.path.join(static_folder, dst)

        directory = Dir(abs_src)
        #####################################################
        # Make sure the destination directory is different if
        # any of the files has changed
        # This is a form of cache busting.
        #####################################################
        # - get a hash of the directory;
        # - take only first 16 hex digits (= 16*16 bits)
        uniq = directory.hash()[:16]

        dst_dirtree_relpath = os.path.join(dst, uniq)
        dst_dirtree_abspath = os.path.join(static_folder, dst_dirtree_relpath)

        if not os.path.exists(dst_dirtree_abspath):
            shutil.copytree(abs_src, dst_dirtree_abspath)

        self.dst_url = dst_dirtree_relpath

def configure_ckeditor(app):
    ckeditor = AssetDirTree(app,
                            app.config['CKEDITOR_SRC'],
                            app.config['CKEDITOR_DST'])

    @app.context_processor
    def inject():
        return dict(
          ckeditor_main_filename=os.path.join(ckeditor.dst_url, 'ckeditor.js'))

    return ckeditor

class AppRun(Command):
    # The run command must only be used on the local machine,
    # and never in production
    def run(self):
        app.run(host=app.config['HOST'],
                port=app.config['PORT'],
                debug=app.config['DEBUG'])

def configure_manager(app):
    manager = Manager(app)
    manager.add_command('db', MigrateCommand)
    manager.add_command('run', AppRun)
    return manager

def configure_db(app):
    db = SQLA(app)
    app.db = db
    return db

def configure_bootstrap(app):
    return Bootstrap(app)

def configure_loginmanager(app):
    login_manager = LoginManager(app)
    return login_manager

# An object that defines several datetime formats.
# We will pass an instance of this class to the
# Jinja environment for convenience
class MomentFmt(object):
    datetime = "MMMM Do YYYY h:mm:ss"
    datetime_mins = "MMMM Do YYYY h:mm"
    date = "MMMM Do YYYY"
    time = "h:mm:ss"
    datetime_ampm = "MMMM Do YYYY h:mm:ss a"
    time_ampm = "h:mm:ss a"

def configure_moment(app):
    moment_fmt = MomentFmt()

    # This decorator allows us to inject names into the
    # global Jinja environment
    @app.context_processor
    def inject():
        return dict(moment_fmt=moment_fmt)

    moment = Moment(app)
    return moment


def configure_assets(app):
    assets = Environment(app)
    assets.versions = 'hash'
    assets.url_expire = True
    # ----------------------------------------- #
    # Bundle the assets, using "normal" cache busting
    non_hljs_css = Bundle('private/css/bootswatch/journal/bootstrap.css',
                          'private/css/custom.css',
            output='public/css/non-hljs.%(version)s.css')
    hljs_css = Bundle('private/css/highlightjs-style.css',
            output='public/css/hljs.%(version)s.css')
    #font_ttf  = Bundle('private/fonts/glyphicons-halflings-regular.ttf',
    #        output='public/fonts/glyphicons-halflings-regular.ttf')

    assets.register('non_hljs_css', non_hljs_css)
    assets.register('hljs_css', hljs_css)
    #assets.register('font_ttf', font_ttf)
    return assets

class AkismetChecker(Akismet):

    def is_spam(self, comment, is_test=True):
        comment_data = {'comment_author': comment.name,
                         'comment_author_email': comment.email,
                         'comment_author_url': comment.website,
                         'user_agent': request.user_agent.string,
                         'user_ip': request.remote_addr,
                         'is_test': int(is_test)}
        return akis.comment_check(comment.content, comment_data)

def configure_akismet(app):
    try:
        apikey = app.config['AKISMET_API_KEY']
    except:
        return None

    akis = AkismetChecker(agent=app.config['APP_NAME'])
    akis.setAPIKey(apikey)
    if not akis.verify_key():
        raise Exception("Akismet API key is invalid.")
    return akis

app = Flask(__name__)
app.config.from_object('config')
db = configure_db(app)
appbuilder = AppBuilder(app, db.session, indexview=NewIndexView)
manager = configure_manager(app)
migrate = Migrate(app, db)
ckeditor = configure_ckeditor(app)
assets = configure_assets(app)
bootstrap = configure_bootstrap(app)
moment = configure_moment(app)
akis = configure_akismet(app)
# crsf will handle CSRF protection for forms in the website.
# We will have to especially allow POST requests without a
# CSRF token for the REST API
csrf = CsrfProtect(app)

# Create a blueprint to provide a special ``static_folder``
# to store image files
file_uploads = Blueprint('file_uploads', __name__,
        static_folder=app.config['ENTRY_FILES_UPLOAD_FOLDER'],
        static_url_path=app.config['ENTRY_FILES_UPLOAD_URL'])

app.register_blueprint(file_uploads)

from app import models, views, routes, rest_api

# Initialize the app with good defaults, if the
# database is stil virgin.
import initialize
initialize.initialize()
