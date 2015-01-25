from flask.ext.appbuilder.security.models import User

from app import db
from app.models import *
from faker import Factory
import random


fake = Factory.create()

admin = db.session.query(User).filter(User.role.has(name='Admin')).first()

def tryadd(obj, db):
    try:
        db.session.add(obj)
        db.session.commit()
        print obj
        return 1
    except Exception as e:
        #raise e
        db.session.rollback()
        return 0

def fake_entry(author, cat):
    since = fake.date_time_between(start_date="-15y", end_date="+1y")
    until = fake.date_time_between(start_date="now", end_date="+3y")
    created = fake.date_time_between(start_date=since - datetime.timedelta(days=160))
    title = fake.sentence()

    return Entry(title=title,
                 slug=title.strip().replace(',', '')\
                                   .replace('.', '')\
                                   .replace(' ', '-')\
                                   .lower(),
                 author_id=author.id,
                 show_author=fake.boolean(80),
                 category_id=cat.id,
                 public=fake.boolean(90),
                 archivable=fake.boolean(90),
                 lead="<p>"+fake.text(100)+"</p>",
                 content="<p>"+fake.text(3000)+"</p>",
                 unlocked=fake.boolean(80),
                 commentable=fake.boolean(90),
                 since=since,
                 until=until,
                 created=created,
                 created_by=admin,
                 changed_by=admin)

def fake_link_list(n, type='ul'):
    inner = "\n".join(["<li><a>{}</a></li>".format(fake.sentence().title())
                          for i in xrange(n)])
    return "<{0}>\n{1}</{0}>".format(type, inner)

def fake_sidebar_module(k, index):
    return SidebarModule(
            title=fake.sentence(),
            text=fake_link_list(k),
            visible=fake.boolean(70),
            index=index,
            created_by=admin,
            changed_by=admin)

def fake_category(index):
    word = fake.word()
    return Category(name=word.capitalize(),
                    slug=word,
                    description=fake.sentence(),
                    index=index)

def fake_tag():
    name = fake.word()
    return Tag(name=name,
               slug=name,
               description=fake.sentence(),
               created_by=admin,
               changed_by=admin)

def fake_sidebar_modules(N, k, db):
    n = 0
    while n < N:
        n = n + tryadd(fake_sidebar_module(k, n), db)

def fake_author():
    return Author(name=fake.name(),
                  description=fake.sentence(),
                  created_by=admin,
                  changed_by=admin)

def fake_categories(N, db):
    n = 0
    while n < N:
        n = n + tryadd(fake_category(n), db)

def add_independent(creator):
    def inner(N, db):
        n = 0
        while n < N:
            n = n + tryadd(creator(), db)
            print n
    return inner

fake_authors = add_independent(fake_author)
fake_tags = add_independent(fake_tag)

def fake_entries(N, db):
    for author in db.session.query(Author).all():
        for cat in db.session.query(Category).filter_by(name='Main').all():
            n = 0
            while n < N:
                entry = fake_entry(author, cat)
                n = n + tryadd(entry, db)

def fake_comments(N, db):
    for entry in db.session.query(Entry).all():
        n = 0
        while n < N:
            comm = fake_comment(entry)
            n = n + tryadd(comm, db)


def fake_comment(entry):
    profile = fake.profile()
    return Comment(name=profile['name'],
                   email=profile['mail'],
                   website=fake.url(),
                   content=fake.text(300),
                   published=fake.date_time_between(entry.since, 'now'),
                   entry_id=entry.id)

def add_tags(N, db):
    tags = db.session.query(Tag).all()
    for entry in db.session.query(Entry).all():
        entry.tags = random.sample(tags, N)
    db.session.commit()

def fake_data(db):
    # fake_categories(3, db)
    fake_tags(15, db)
    fake_authors(2, db)
    fake_entries(5, db)
    fake_comments(5, db)
    fake_sidebar_modules(4, 10, db)
    add_tags(5, db)

fake_data(db)
