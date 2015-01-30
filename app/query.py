from models import Entry, SidebarModule, Comment, ChooseConfig, Category, Author, Tag
from app import app, db
import datetime

# Functions whose name is plural (e.g. ``categories``)
# return a query. Functions whose name is singular
# (e.g. ``category``) return a single object or ``None``


def category(name=None, slug=None):
    if name:
        return db.session.query(Category).filter_by(name=name).first()
    elif slug:
        return db.session.query(Category).filter_by(slug=slug).first()

def categories():
    return db.session.query(Category)\
        .filter_by(show=True)\
        .order_by(Category.index.asc())

def author(name):
    return db.session.query(Author).filter_by(name=name).first()

def tag(name):
    return db.session.query(Tag).filter_by(name=name).first()

def home_category():
    home_cat = categories().first()
    if home_cat:
        return home_cat
    else:
        return db.session.query(Category).first()

def blog_config():
    return db.session.query(ChooseConfig).first().chosen_config

def comment(comment_id):
    return db.session.query(Comment).get(comment_id)

def comments(entry_id, visible_only=True):
    q = db.session.query(Comment).\
            filter(Comment.entry_id == entry_id).\
            order_by(Comment.published.asc())

    if visible_only:
        return q.filter_by(visible=True)
    else:
        return q

def entry(slug, is_preview=False):
    if is_preview:
        return db.session.query(Entry).filter_by(slug=slug).first()
    else:
        return db.session.query(Entry).filter_by(slug=slug, public=True).first()

def entries(is_preview, catslug=None, start=None, page_size=None, archivable=True):
    now = datetime.datetime.utcnow()
    q = db.session.query(Entry)\
         .order_by(Entry.created.desc())

    if not is_preview:
        q = q.filter( Entry.public == True,
                      ((Entry.since == None) | (Entry.since <= now)),
                      ((Entry.until == None) | (Entry.until >= now)))
    if catslug:
        q = q.filter(Entry.category.has(slug=catslug))
    if archivable:
        q = q.filter_by(archivable=True)
    if start != None:
        q = q.offset(start)
    if page_size != None:
        q = q.limit(page_size)
    return q


def sidebar_modules():
    return db.session.query(SidebarModule).\
        filter(SidebarModule.visible).\
        order_by(SidebarModule.index)

def editable_comments(edit_lag, usercomments):
    now = datetime.datetime.utcnow()
    oldest_possible = now - edit_lag
    editable_comments = db.session.query(Comment.id, Comment.published).\
        filter(Comment.id.in_(usercomments),
               Comment.published > oldest_possible)
    return editable_comments
