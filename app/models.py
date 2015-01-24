from flask import Markup
from flask.ext.appbuilder import Model
from flask.ext.appbuilder.models.mixins import AuditMixin
from sqlalchemy_searchable import make_searchable, search
from sqlalchemy_utils.types import TSVectorType

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text, Table, DateTime, Interval, CheckConstraint
from sqlalchemy.orm import relationship
from app import db, app

from utils import format_bool, bool_as_lock, bool_as_special

from jinja2 import Template

import datetime

make_searchable()

assoc_entry_tag = Table('entry_tag', Model.metadata,
    Column('id', Integer, primary_key=True),
    Column('entry_id', Integer, ForeignKey('entry.id')),
    Column('tag_id', Integer, ForeignKey('tag.id')))

class Author(AuditMixin, Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(128))
    description = Column(Text)

    def __repr__(self):
        return self.name

class SidebarModule(AuditMixin, Model):
    id = Column(Integer, primary_key=True)
    index = Column(Integer)
    title = Column(Text)
    text = Column(Text)
    visible = Column(Boolean, default=True)

    def __repr__(self):
        return self.title

class Entry(AuditMixin, Model):
    """A blog entry"""

    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('author.id'))
    author = relationship('Author', backref='entries')
    show_author = Column(Boolean)

    title = Column(String(128))
    slug = Column(String(128), unique=True)
    public = Column(Boolean)
    lead = Column(Text)
    content = Column(Text)
    commentable = Column(Boolean)
    unlocked = Column(Boolean)

    since = Column(DateTime)
    show_date = Column(Boolean, default=True)
    until  = Column(DateTime)
    created = Column(DateTime, nullable=False)
    archivable = Column(Boolean)

    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship('Category', backref='entries')

    tags = relationship('Tag', secondary=assoc_entry_tag)

    # Search:
    search_vector = Column(TSVectorType('title', 'lead', 'content'))

    def pretty_commentable(self):
        return format_bool(self.commentable)
    def pretty_unlocked(self):
        return bool_as_lock(self.unlocked)
    def pretty_public(self):
        return format_bool(self.public)
    def pretty_archivable(self):
        return bool_as_special(self.archivable)

    def pretty_content(self):
        return Markup(self.content)

    def __repr__(self):
        return self.slug

class Tag(AuditMixin, Model):
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    slug = Column(String(64), unique=True)
    description = Column(Text)

    entries = relationship('Entry', secondary=assoc_entry_tag)

    def __repr__(self):
        return self.name

class Category(Model):
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    slug = Column(String(128), unique=True)
    description = Column(Text)
    show = Column(Boolean)
    index = Column(Integer)

    def __repr__(self):
        return self.name

class Comment(Model):
    """A Blog Comment"""

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(128))
    website = Column(String(128))
    content = Column(Text)
    published = Column(DateTime)

    visible = Column(Boolean, default=True)
    akismet_spam = Column(Boolean, default=False)
    confirmed_spam = Column(Boolean, default=False)

    entry_id = Column(Integer, ForeignKey('entry.id'))
    entry = relationship('Entry', backref='comments')

    # Search:
    search_vector = Column(TSVectorType('content'))

    def __repr__(self):
        return self.content[:50]

class ChooseConfig(AuditMixin, Model):
    id = Column(Integer, primary_key=True)
    chosen_config_id = Column(Integer, ForeignKey('blog_config.id'), nullable=False)
    chosen_config = relationship('BlogConfig')
    # Force this table to have at most 1 row
    lock = Column(Integer, CheckConstraint('lock=0'),
                  default=0, unique=True, nullable=False)

    def __repr__(self):
        return self.chosen_config

class BlogConfig(AuditMixin, Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(32), unique=True)
    description = Column(String(256))
    blog_title = Column(String(64))
    blog_subtitle = Column(String(128))
    edit_lag_in_minutes = Column(Integer)
    window_title = Column(String(64))
    entries_in_sidebar = Column(Integer)
    entries_per_page = Column(Integer)
    show_all_tab = Column(Boolean)

    def __repr__(self):
        return self.name
