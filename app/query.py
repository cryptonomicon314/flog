from models import Entry, SidebarModule, Comment, ChooseConfig, Category, Author, Tag
# db is always a parameter to a function, never app.db
from app import app
import datetime

PUBLIC = app.config['PAGE_VERSION_PUBLIC']
PRIVATE = app.config['PAGE_VERSION_PRIVATE']

# Functions whose name is plural (e.g. ``categories``)
# return a query. Functions whose name is singular
# (e.g. ``category``) return a single object or ``None``


def category(db, name=None, slug=None):
    if name:
        return db.session.query(Category).filter_by(name=name).first()
    elif slug:
        return db.session.query(Category).filter_by(slug=slug).first()

def categories(db):
    return db.session.query(Category)\
        .filter_by(show=True)\
        .order_by(Category.index.asc())

def author(db, name):
    return db.session.query(Author).filter_by(name=name).first()

def tag(db, name):
    return db.session.query(Tag).filter_by(name=name).first()

def home_category(db):
    home_cat = categories(db).first()
    if home_cat:
        return home_cat
    else:
        return db.session.query(Category).first()

def blog_config(db):
    return db.session.query(ChooseConfig).first().chosen_config


def comment(db, comment_id):
    return db.session.query(Comment).get(comment_id)

def comments(db, entry_id, visible_only=True):
    q = db.session.query(Comment).\
            filter(Comment.entry_id == entry_id).\
            order_by(Comment.published.asc())

    if visible_only:
        return q.filter_by(visible=True)
    else:
        return q

def entry(db, slug, version):
    if version == PRIVATE:
        return db.session.query(Entry).filter_by(slug=slug).first()
    else:
        return db.session.query(Entry).filter_by(slug=slug, public=True).first()

def all_visible_entries(db, now, imin, imax, is_preview):
    if is_preview:
        q = db.session.query(Entry)\
                .filter( (Entry.until == None) | (Entry.until >= now) )\
                .order_by(Entry.created.desc())\
                .offset(imin).limit(imax)
    else:
        q = db.session.query(Entry)\
            .filter( Entry.public,
                     ((Entry.since == None) | (Entry.since <= now)),
                     ((Entry.until == None) | (Entry.until >= now)))\
            .order_by(Entry.created.desc())\
            .offset(imin).limit(imax)
        for e in db.session.query(Entry).all():
            print e.until
        print
    if (imin, imax) == (None, None):
        return q
    else:
        return q.offset(imin).limit(imax)

def visible_entries(db, catslug, now, imin, imax, is_preview):
    if is_preview:
        q = db.session.query(Entry)\
                .filter( Entry.category.has(slug=catslug),
                         (Entry.until == None) | (Entry.until >= now) )\
                .order_by(Entry.created.desc())\
                .offset(imin).limit(imax)
    else:
        q = db.session.query(Entry)\
            .filter( Entry.category.has(slug=catslug),
                     Entry.public,
                     ((Entry.since == None) | (Entry.since <= now)),
                     ((Entry.until == None) | (Entry.until >= now)))\
            .order_by(Entry.created.desc())\
            .offset(imin).limit(imax)
        for e in db.session.query(Entry).all():
            print e.until
        print
    if (imin, imax) == (None, None):
        return q
    else:
        return q.offset(imin).limit(imax)


def sidebar_modules(db):
    return db.session.query(SidebarModule).\
        filter(SidebarModule.visible).\
        order_by(SidebarModule.index)

def editable_comments(db, now, edit_lag, usercomments):
    oldest_possible = now - edit_lag
    editable_comments = db.session.query(Comment.id, Comment.published).\
        filter(Comment.id.in_(usercomments),
               Comment.published > oldest_possible)
    return editable_comments
