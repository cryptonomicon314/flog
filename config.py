import os
import yaml
from flask.ext.appbuilder.security.manager import AUTH_DB

basedir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

secrets_folder = basedir + '/data/app/secrets'
#---------------------------------------------------
# Image and file configuration
#---------------------------------------------------
# The file upload folder, when using models with files
UPLOAD_FOLDER = basedir + '/data/app/static/uploads/entry/'
ENTRY_FILES_UPLOAD_FOLDER = basedir + '/data/app/static/uploads/entry/'
# The image upload folder, when using models with images
IMG_UPLOAD_FOLDER = basedir + '/data/app/static/uploads/img/'
# The image upload url, when using models with images
IMG_UPLOAD_URL = '/static/uploads/'
# Enty file uploads
ENTRY_FILES_UPLOAD_URL = '/static/uploads/entry'

APP_NAME = 'blog'

PAGE_VERSION_PUBLIC = 'public'
PAGE_VERSION_PRIVATE = 'private'

CKEDITOR_SRC = 'private/ckeditor'
CKEDITOR_DST = 'public/ckeditor'

# Test whether we are running on openshift or locally
try:
    #  If we are running on Openshift, do nothing;
    # the environment vars are already configured.
    #  If they are not configured, accessing them
    # will raise an error, which takes us to the
    # ``except`` clause.
    os.environ['OPENSHIFT_POSTGRESQL_DB_HOST']
    os.environ['OPENSHIFT_POSTGRESQL_DB_PORT']
    # We use the presence ot absense of the Openshift env vars
    # to test whether we are running locally or remotely
except:
    #  If we are not running on Openshift (for testing)
    # set the variables ourselves.
    #  These variables persist only during the execution of
    # the program, and won't pollute the environment
    # afterwards.
    #  Port 5432 is the default.
    os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'] = 'localhost'
    os.environ['OPENSHIFT_POSTGRESQL_DB_PORT'] = '5432'

POSTGRESQL_HOST = os.environ['OPENSHIFT_POSTGRESQL_DB_HOST']
POSTGRESQL_PORT = os.environ['OPENSHIFT_POSTGRESQL_DB_PORT']

try:
    secrets_path = os.path.join(secrets_folder, 'remote.yaml')
    secrets = yaml.safe_load(open(secrets_path).read())
except:
    secrets_path = os.path.join(secrets_folder, 'local.yaml')
    secrets = yaml.safe_load(open(secrets_path).read())


POSTGRESQL_USERNAME = secrets['postgresql_username']
POSTGRESQL_DBNAME   = secrets['postgresql_dbname']
POSTGRESQL_PASSWORD = secrets['postgresql_password']

SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}:{port}/{db}'.format(
            user=POSTGRESQL_USERNAME,
            password=POSTGRESQL_PASSWORD,
            host=POSTGRESQL_HOST,
            port=POSTGRESQL_PORT,
            db=POSTGRESQL_DBNAME)

# Your App secret key
SECRET_KEY = secrets['secret_key']
try:
    AKISMET_API_KEY = secrets['akismet_api_key']
except:
    print "Akismet api key not found."
    pass
# SQLite support has been removed because SQLite doesn't handle
# timedelta (SQL INTERVAL) arithmetic correctly. It can lead to
# unexpected nasty bugs with date arithmetic.

# Flask-WTF flag for CSRF
CSRF_ENABLED = True
AUTH_TYPE = AUTH_DB

# These variables only have effet when running locally,
# using the Werkzeug debugger.
HOST = 'localhost'
PORT = 5000
DEBUG = True

# Uncomment to setup OpenID providers example for OpenID authentication
#OPENID_PROVIDERS = [
# { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
# { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
# { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
# { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
# { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]
#---------------------------------------------------
# Babel config for translations
#---------------------------------------------------
# Setup default language
BABEL_DEFAULT_LOCALE = 'en'
# Your application default translation path
BABEL_DEFAULT_FOLDER = 'translations'
# The allowed translation for you app
LANGUAGES = {
'en': {'flag':'gb', 'name':'English'},
'pt': {'flag':'pt', 'name':'Portuguese'},
'pt_BR': {'flag':'br', 'name': 'Pt Brazil'},
'es': {'flag':'es', 'name':'Spanish'},
'de': {'flag':'de', 'name':'German'},
'zh': {'flag':'cn', 'name':'Chinese'},
'ru': {'flag':'ru', 'name':'Russian'}
}
