# Flask:
from flask import render_template, redirect, abort, url_for,\
  g, session, request, flash

from werkzeug.contrib.atom import AtomFeed

# Flask extensions:
from flask.ext.appbuilder import BaseView, expose, has_access, permission_name
from flask_appbuilder.security.models import User, Role

from sqlalchemy_searchable import search
# Standard Library:
import os
import itertools
import datetime

# Flog modules:
from app import app, db, appbuilder, akis
from models import Entry, Comment, Category, Tag
from utils import sanitize_plaintext, sanitize_richtext
from forms import EditCommentForm, NewCommentForm, SearchForm
import query


# A function that builds a HTML anchor <link>
# to the comment with id ``comment_id``
def comment_anchor_id(comment_id):
    return "comment-id-{}".format(comment_id)

# Common variables that are useful in templates
class Common(object):
    def __init__(self, max_entries):
        self.categories = query.categories(db).all()

@app.before_request
def before_request():
    # Prepare session:
    try:
        session['comments']
    except:
        session['comments'] = []
    session.permanent = True

    g.blog_config = query.blog_config(db)
    g.blog_config.edit_lag = \
        datetime.timedelta(minutes=g.blog_config.edit_lag_in_minutes)
        # edit_lag is stored as an integer number of minutes
        # because many database engines have problems storing timedeltas.
    g.common = Common(g.blog_config.entries_in_sidebar)
    g.search_form = SearchForm()


@app.route('/atom-feed-entries')
def atom_feed_entries():
    now = datetime.datetime.utcnow()
    config = query.blog_config(db)
    title = config.blog_title + " Entries"
    subtitle = config.blog_subtitle
    feed = AtomFeed(title, feed_url=request.url,
                    url=request.host_url,
                    subtitle=subtitle)

    for entry in query.all_visible_entries(db, now, None, None, False, True)\
                   .limit(config.entries_in_feed).all():
        feed.add(entry.title, entry.lead + entry.content, content_type='html',
                 author=entry.author.name,
                 url=url_for('PublicView.entry', slug=entry.slug),
                 id=entry.id,
                 updated=entry.created,
                 published=entry.created)
    return feed.get_response()

@app.route('/atom-feed-comments')
def atom_feed_comments():
    now = datetime.datetime.utcnow()
    config = query.blog_config(db)
    title = config.blog_title + " Comments"
    subtitle = "Responses from the readers"
    feed = AtomFeed(title, feed_url=request.url,
                    url=request.host_url,
                    subtitle=subtitle)

    for comment in db.session.query(Comment)\
                       .limit(config.comments_in_feed).all():
        feed.add(comment.name, comment.content, content_type='html',
                 author=comment.name,
                 url=url_for('PublicView.entry',
                             slug=comment.entry.slug,
                             _anchor=comment_anchor_id(comment.id)),
                 id=comment.id,
                 updated=comment.published,
                 published=comment.published)
    return feed.get_response()


# The class SiteView represents the set of routes in our blog.
# It defines not only the routes, but also their permissions.
# By subclassing the SiteView and assigning permissions to certain
# roles, we can create different versions of the site for different
# user roles (as of now, only **Admin** and **Public**)
#
# We will have 2 versions:
#
# - *public*: this is the website that is visible to users with the **Public**
# role, taht is, users that visit the website without an account
#
# - *private* or *preview*: this version of the website will not available to
# the public. Users will need to create an account with a role that has the
# appropriate permissions (in our case, the **Admin** role)
#
# We want the different versions of the website to have different base
# routes. This creates a challenge with hyperlinks between pages of the website.
# We want the *public* version to link to pages in the *public* version, and
# the *private* version to link to pages in the *private* version only.
# The problem is that the default function to generate hyperlinks, ``url_for()``
# doesn't know if it has been called from the *public* or *private* version.
#
# for this reason, we will define a ``.url_for()`` method.
class SiteView(BaseView):

    # The ``.url_for()`` method behaves almost like the default ``url_for()``
    # function. The difference is that it knows from which class it has been called.
    #
    # When you invoke ``self.url_for("methodname")`` from class ``SecretView``,
    # the function will generate the url for ``"SecretView.methodname"``.
    #
    # This makes sure that as long as the user navigates using hyperlinks, he will
    # be directed from *private* pages to *private* pages and form *public* pages to
    # *public* pages.
    #
    # Of course, the user might choose to navigate to the unaccessible pages by
    # typing the URL in the URL bar, but will be asked to login before he can access
    # restricted views.
    def url_for(self, methodname, *args, **kwargs):
        name = '{}.{}'.format(self.__class__.__name__, methodname)
        return url_for(name, *args, **kwargs)

    # Most methods of this class will have to deal with 2 cases:
    # either (1) the page is *public* or (2) the page is *private*.
    #
    # As long as possible, this complecity has been relegated to
    # the query module, where most of the DB query operations have
    # been defined.
    #
    # Because the private and public versions of the pages are identical
    # except for the *data*, usually only the code that queries the DB
    # has to handle the 2 cases.
    # This keeps code repetition to the minimum.
    def recent_entries(self):
        max_entries = query.blog_config(db).entries_in_sidebar
        now = datetime.datetime.utcnow()
        recent_entries = query.all_visible_entries(db, now, 0, max_entries, self.is_preview, True)
        return recent_entries


    def tag_counts(self):
        """Returns pairs of the form (*tag*, *number of entries*).
        The method is aware of the page version (*public* or *private*),
        and will only show the number of entries that are available in
        that version"""

        # There should be a more "SQLy" way of doing this
        tags = db.session.query(Tag)
        #pairs = [(tag, len([entry for entry in tag.entries
        #                      if entry.is_visible(self.is_preview)]))
        #         for tag in tags]
        pairs = [(tag, tag.nr_of_visible_entries(self.is_preview))
                   for tag in tags]

        # Only show tags that have at least one entry:
        return [(tag, count) for (tag, count) in pairs if count != 0]

    def sidebar_modules(self):
        return query.sidebar_modules(db).all()

    def categories(self):
        return query.categories(db).all()

    @permission_name('view_blog')
    @expose('/search', methods=['POST'])
    def search(self):
        if not g.search_form.validate_on_submit():
            return redirect(url_for('index'))
        return redirect(self.url_for('search_results_entries',
            search_query=g.search_form.search.data))


    @permission_name('view_blog')
    @expose('/search-results/entries/<search_query>')
    def search_results_entries(self, search_query):
        now = datetime.datetime.utcnow()
        sql_q = query.all_visible_entries(db, now, None, None, self.is_preview, False)
        entries = search(sql_q, search_query.lower())

        # It won't need pagination for now
        return render_template('search-results-entries.html',
            search_query=search_query,
            entries=entries,
            cls=self)

    @permission_name('view_blog')
    @expose('/search-results/comments/<search_query>')
    def search_results_comments(self, search_query):
        now = datetime.datetime.utcnow()
        sql_q = db.session.query(Comment)
        comments = search(sql_q, search_query.lower())

        # The edit lag is the time the user has to edit the comment after the submission.
        # By deafult, it is 15 minutes, but can be configuref by the Admin.
        edit_lag = g.blog_config.edit_lag
        # get the editable comments from the DB, based on their publication date
        editable_cmts = editable_comments(db, edit_lag, session)
        # It won't need pagination for now
        return render_template('search-results-comments.html',
            search_query=search_query,
            comments=comments,
            editable_comments=editable_cmts,
            comment_anchor_id=comment_anchor_id,
            cls=self)


    @has_access
    # All methods in the SiteView class have the ``'view_blog'`` permission.
    # Flask-AppBuilder allows us to assign a pair (permission, class) to
    # a role. This allows us to say thing like: "a *Public* user can access the
    # methods marked ``'view_blog'`` from the ``PublicView`` class, but not the
    # methods marked ``'view_blog'`` from the ``PrivateView`` class.
    @permission_name('view_blog')
    @expose('/archives/')
    def archives(self):
        now = datetime.datetime.utcnow()
        entries = query.all_visible_entries(db, now, None, None, self.is_preview, True)

        # Group the entries by year:
        grouping = itertools.groupby(entries, lambda entry: entry.created.year)
        return render_template("archives.html",
                title="Archives",
                grouping=grouping,
                # We have to tell th template that we are rendering the
                # "archives" page, so that the template knows what to
                # mark as active in the bar.
                is_archives=True,
                # we supply the instance as an argument, so that we can call
                # ``cls.url_for()`` inside the template, and be redirected to
                # the correct endpoint.
                cls=self)

    @has_access
    @permission_name('view_blog')
    @expose('/tag/<tag_slug>')
    # List all entries with a certain tag
    def tag(self, tag_slug):
        tag = db.session.query(Tag).filter_by(slug=tag_slug).first()

        entries = db.session.query(Entry)\
            .filter(Entry.tags.contains(tag))\
            .order_by(Entry.created.desc())

        # Filter the entries according to the ``page_version``:
        if self.is_preview:
            entries = entries.all()
        else:
            entries = entries.filter_by(public=True).all()

        return render_template('tag.html',
                tag=tag,
                entries=entries,
                cls=self)


    @has_access
    @permission_name('view_blog')
    @expose('/entry/<slug>/', methods=['GET', 'POST'])
    @expose('/entry/<slug>/<int:edit_id>/', methods=['GET', 'POST'])
    # This is the most complex method, as it handles a lot of functionality:
    #
    # - a blog ``Entry`` and its ``Comment``s
    # - submiting a new comment
    # - editing a comment
    #
    def entry(self, slug, edit_id=None):
        # The anchor is the element id that the browser uses
        # to "focus" the webpage. If the Anchor is ``None``
        # the browser simply displays the page from the beginning.
        anchor = None
        # Get entry from database
        # The complexity of deciding whether the page is acessible
        # from the current view is delegated to the ``query`` module.
        #
        # Note that this has nothing to do with user permissions;
        # What decides whether the entry can be shown or not is the
        # SiteView subclass. User permissions only restrict the user
        # based on routes!
        _entry = query.entry(db, slug, self.page_version)
        if not _entry:
            # 404 is the "Not Found" error
            return abort(404)

        entry_id = _entry.id
        # Get all visible comment. By default, all spam comments are invisible.
        comments = query.comments(db, entry_id, visible_only=True).all()

        # we will use the current time (now) a lot
        now = datetime.datetime.utcnow()

        # We have to define 2 different forms:
        #
        # - a form to *edit* a comment
        # - a form to submit a *new* comment
        form_edit = EditCommentForm(request.form, prefix="edit")
        form_new = NewCommentForm(request.form, prefix="new")

        # If the user has just edited a comment:
        if edit_id and edit_id in session.get('comments'):
            # if the form has been submitted and validated, and has type ``'edit-comment'``:
            if form_edit.validate_on_submit() and form_edit.type.data == 'edit-comment':
                update_comment(db, edit_id, form_edit)
                # Redirect user to page with the comment updated
                # Note that we must use the ``self.url_for()`` instead
                # of the ``url_for()`` function.
                return redirect(self.url_for('entry', slug=slug,
                    # we want the browser to show the page focused on the
                    # recently edited comment
                    _anchor=comment_anchor_id(edit_id)))
            else:
                # If the user is going to edit a comment, populate the form
                # with the data from the comment.
                populate_form(db, edit_id, form_edit)

        else:
            # if the user has just submitted a new comment:
            if form_new.validate_on_submit() and form_new.type.data == 'new-comment':
                # Create a new comment, testing it for spam using Akismet's API.
                # if the comment is tagged spam, comment is set to None.
                comment, is_spam = create_comment(db, form_new, _entry)
                # If the comment is spam:
                #
                # Redirect the user to the newly posted comment.
                # As above, note the use of ``self.url_for()``
                if is_spam:
                    flash("Your comment was marked as spam.")
                    flash("It will be reviewed before being displayed.")
                    return redirect(self.url_for('entry', slug=slug,
                        _anchor='new-comment-form'))
                # If the comment is not spam:
                #
                # Store the comment ID in a secure token in the client
                # session. This ensures only this User can edit this
                # comment, and only using the same device. Forcing the
                # user to use the same device is not optimal, but
                # relieves us and the user from the hassle of managing
                # and creating accounts for the blog.
                else:
                    session['comments'].append(comment.id)
                    return redirect(self.url_for('entry', slug=slug,
                        _anchor=comment_anchor_id(comment.id)))

        # The edit lag is the time the user has to edit the comment after the submission.
        # By deafult, it is 15 minutes, but can be configuref by the Admin.
        edit_lag = g.blog_config.edit_lag
        # get the editable comments from the DB, based on their publication date
        editable_cmts = editable_comments(db, edit_lag, session)

        return render_template('entry-detail.html',
            entry=_entry,
            # The template needs to know ehat the active category is:
            active_category=_entry.category.slug,
            comments=comments,
            form_new=form_new, form_edit=form_edit,
            # we supply a function to generate anchors to the comments:
            comment_anchor_id=comment_anchor_id,
            editable_comments=editable_cmts,
            now=now,
            # we supply the ID of the comment the user is editing, or ``None``
            # if the User hasn't edited or won't edit.
            edit_id=edit_id,
            cls=self)


    @has_access
    @permission_name('view_blog')
    @expose('/home/')
    # This function redirects the user to first category of the blog,
    # by default ``Main``.
    def home(self):
        home_category = query.home_category(db)
        return redirect(self.url_for('category', catslug=home_category.slug))

    @has_access
    @permission_name('view_blog')
    @expose('/category/<catslug>')
    @expose('/category/<catslug>/<int:page>')
    # List entries in a category. Entries are divided into pages according
    # to the configuration defined by the Admin user. Each page has
    # ``entries_per_page`` entries. Pages start countiing from 1, not 0.
    #
    # If ``page == 1``, the page number is optional.
    def category(self, catslug, page=1):
        now = datetime.datetime.utcnow()
        category = db.session.query(Category).filter_by(slug=catslug).first()
        if not category:
            return abort(404)

        entries_per_page = query.blog_config(db).entries_per_page
        nr_of_entries = query.visible_entries(db, catslug, now, None, None, self.is_preview, False).count()

        if (page-1)*entries_per_page >= nr_of_entries:
            return abort(404)

        # Get the entries (remember, page numbers start at 1!)
        entries = query.visible_entries(db, catslug, now,
                (page - 1) * entries_per_page, entries_per_page,
                self.is_preview, False).all()


        # Get the *next* (= ``newer``) and *previous* (= ``older``) pages:
        # if there are no ``older`` or ``newer```pages, set the corresponding
        # value to ``None``. This will be used by the template.
        if page <= 1:
            newer = None
        else:
            newer = page - 1

        if page * entries_per_page >= nr_of_entries:
            older = None
        else:
            older = page + 1

        return render_template('category.html',
            entries=entries,
            category=category,
            active_category=catslug,
            current_page=page,
            older=older,
            newer=newer,
            route='category',
            cls=self)

    @has_access
    @permission_name('view_blog')
    @expose('/all/')
    @expose('/all/<int:page>')
    def all_entries(self, page=1):
        # Similar to above. Now, we won't filter by category.
        now = datetime.datetime.utcnow()
        entries_per_page = query.blog_config(db).entries_per_page
        nr_of_entries = query.all_visible_entries(db, now, None, None, self.is_preview, True).count()

        if (page-1)*entries_per_page >= nr_of_entries:
            return abort(404)

        entries = query.all_visible_entries(db, now,
                (page - 1) * entries_per_page, entries_per_page,
                self.is_preview, True)

        if page <= 1:
            newer = None
        else:
            newer = page - 1

        if page * entries_per_page >= nr_of_entries:
            older = None
        else:
            older = page + 1

        return render_template('all-entries.html',
            entries=entries,
            # we have to tell the template this is the 'All' page
            is_all=True,
            current_page=page,
            older=older,
            newer=newer,
            cls=self)

# Now we will subclass ``SiteView`` to get identical pages with
# different permissions. We just set the ``page_version`` and
# ``route_base`` attributes:
class PublicView(SiteView):
    page_version = 'public'
    is_preview = False
    route_base = ''

class PrivateView(SiteView):
    page_version = 'private'
    is_preview = True
    route_base = '/preview'


# Some utility functions we used above:
def create_comment(db, form, entry):
    is_spam = False
    # round the date to the nearest second. Otherwise we get problems
    # when using the admin interface because the datetime picker can't
    # handle microseconds.
    pub_datetime = datetime.datetime.utcnow().replace(microsecond=0)
    # Create comment from form data, sanitizing when appropriate.
    # Sanitization functions are defined in the ``utils`` module.
    comment = Comment(name=sanitize_plaintext(form.name.data),
                      email=form.email.data,
                      website=form.website.data,
                      content=sanitize_richtext(form.content.data),
                      published=pub_datetime,
                      number=entry.highest_comment()+1,
                      entry_id=entry.id)

    if akis is not None:
        is_spam = akis.is_spam(comment)

    if is_spam:
        comment.akismet_spam = True
        comment.visible = False
    # Otherwise, apply the defaults, which assume the comment is not spam
    db.session.add(comment)
    db.session.commit()
    return comment, is_spam




def update_comment(db, comment_id, form):
    comment = query.comment(db, comment_id)
    comment.name = sanitize_plaintext(form.name.data)
    comment.email = form.email.data
    comment.content = sanitize_richtext(form.content.data)
    db.session.commit()
    return comment

def populate_form(db, comment_id, form):
    comment = db.session.query(Comment).get(comment_id)
    form.name.data = comment.name
    form.email.data = comment.email
    form.content.data = comment.content
    return form


def editable_comments(db, edit_lag, session):
    """Gets editable comments based on the current time and
    comment publication date"""
    now = datetime.datetime.utcnow()
    pairs = query.editable_comments(db, now, edit_lag, session['comments'])
    editable_cmts = dict(
        [(cmt_id, {'date': date + edit_lag,
                   # delta in milliseconds (for javascript)
                   'delta': int(round((date + edit_lag - now).total_seconds()*1000))})
            for cmt_id, date in pairs])
    return editable_cmts
