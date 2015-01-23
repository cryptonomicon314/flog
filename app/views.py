from flask import Markup, request, make_response
import flask.json as json

import flask_wtf.file as flask_wtf # not from wtforms!
from app import appbuilder, db, csrf
from models import Entry, Comment, Tag, Category, Author, SidebarModule, BlogConfig, ChooseConfig

from werkzeug import secure_filename

from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.models.sqla.filters import FilterContains
from flask.ext.appbuilder import ModelView, BaseView, expose, has_access
from flask.ext.appbuilder.views import IndexView
from flask.ext.appbuilder.baseviews import expose

from flask.ext.login import login_user

class EntryView(ModelView):
    # The goal is to use this view the least we can, and use the
    # command line client and REST API to add entries.
    datamodel = SQLAModel(Entry)
    add_columns = ['author',
                   'show_author',
                   'title',
                   'slug',
                   'lead',
                   'content',
                   'public',
                   'tags',
                   'category',
                   'commentable',
                   'unlocked',
                   'created',
                   'show_date',
                   'since',
                   'until',
                   'archivable']

    edit_columns = add_columns

    label_columns = {'commentable':         'Comments Allowed',
                     'pretty_commentable':  'Commentable',
                     'unlocked':            'Comments Unlocked',
                     'pretty_unlocked':     'Unlocked',
                     'public':              'Public',
                     'pretty_public':       'Public'}

    list_columns = ['author',
                    'show_author',
                    'title',
                    'slug',
                    'pretty_public',
                    'tags',
                    'pretty_commentable',
                    'pretty_unlocked',
                    'created',
                    'since',
                    'until',
                    'archivable']

    search_columns = ['author',
                      'show_author',
                      'title',
                      'slug',
                      'content',
                      'public',
                      'tags',
                      'commentable',
                      'unlocked',
                      'created',
                      'archivable']

    #  Custom list_template that makes the font smaller
    # so that everything fits in the screen
    list_template = 'admin/entry/list.html'
    # Custom ``add_template`` and ``edit_template`` add support for
    # ruch text editing with the CKEditor plugin.
    add_template = 'admin/richtext/add.html'
    edit_template = 'admin/richtext/edit.html'

    extra_args = {'rich_textareas': ['lead', 'content']}

    show_fieldsets = [
        ('Info', {'fields': ['title', 'content', 'public']}),
        ('Audit', {'fields': ['created_by', 'created_on', 'changed_by', 'changed_on'],
                   'expanded': False})]


class CommentView(ModelView):
    datamodel = SQLAModel(Comment)

    list_columns = ['name',
                    'published',
                    'content',
                    'akismet_spam',
                    'confirmed_spam']

    add_columns = ['name',
                   'email',
                   'website',
                   'content',
                   'published',
                   'visible',
                   'akismet_spam',
                   'confirmed_spam',
                   'entry']
    edit_columns = add_columns

    search_columns = add_columns

    extra_args = {'rich_textareas': ['content']}

    add_template = 'admin/richtext/add.html'
    edit_template = 'admin/richtext/edit.html'


class TagView(ModelView):

    list_columns = ['name', 'slug', 'description']
    add_columns = ['name', 'slug', 'description']

    datamodel = SQLAModel(Tag)

class CategoryView(ModelView):
    list_columns = ['name', 'description', 'index']
    base_order = ('index', 'asc')

    datamodel = SQLAModel(Category)

class AuthorView(ModelView):
    list_columns = ['name', 'entries']
    add_columns = ['name', 'entries']
    edit_columns = add_columns

    datamodel =  SQLAModel(Author)

class SidebarModuleView(ModelView):
    datamodel = SQLAModel(SidebarModule)

    list_columns = ['title', 'index', 'visible']
    add_columns = ['title', 'text', 'index', 'visible']

    base_order = ('index', 'asc')

    add_template = 'admin/richtext/add.html'
    edit_template = 'admin/richtext/edit.html'

    extra_args = {'rich_textareas': ['text']}

class BlogConfigView(ModelView):
    datamodel = SQLAModel(BlogConfig)
    add_columns = ['name',
                   'description',
                   'blog_title',
                   'blog_subtitle',
                   'edit_lag_in_minutes',
                   'window_title',
                   'entries_in_sidebar',
                   'entries_per_page',
                   'show_all_tab']

    edit_columns = add_columns
    list_columns = ['name', 'description']

    search_columns = ['name']

class ChooseConfigView(ModelView):
    datamodel = SQLAModel(ChooseConfig)

    list_columns = ['chosen_config']
    add_columns = list_columns
    edit_columns = list_columns

db.session.remove()
db.create_all()

# Import the client API
from rest_api import ClientApi
# Import the views we defined in the ``routes`` module
from routes import PublicView, PrivateView

# Add these vews without a menu:
appbuilder.add_view_no_menu(ClientApi())
appbuilder.add_view_no_menu(PrivateView())
appbuilder.add_view_no_menu(PublicView())

# Add the modelviews with a menu:
appbuilder.add_view(EntryView,         "Entries",        icon="fa-folder-open-o", category_icon="fa-envelope")
appbuilder.add_view(CommentView,       "Comments",       icon="fa-folder-open-o", category_icon="fa-envelope")
appbuilder.add_view(TagView,           "Tags",           icon="fa-folder-open-o", category_icon="fa-envelope")
appbuilder.add_view(CategoryView,      "Categories",     icon="fa-folder-open-o", category_icon="fa-envelope")
appbuilder.add_view(AuthorView,        "Authors",        icon="fa-folder-open-o", category_icon="fa-envelope")
appbuilder.add_view(SidebarModuleView, "Sidebar",        icon="fa-folder-open-o", category_icon="fa-envelope")
appbuilder.add_view(ChooseConfigView,  "Choose Config",  icon="fa-folder-open-o", category_icon="fa-envelope")
appbuilder.add_view(BlogConfigView,    "Blog Config",    icon="fa-folder-open-o", category_icon="fa-envelope")

# Make the ``PrivateView`` private
import permissions
permissions.make_public(PublicView)
