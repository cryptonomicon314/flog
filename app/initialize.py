from flask.ext.appbuilder.security.models import User, Role
from app import db, appbuilder
from app.models import *

def default_blog_config():
    try:
        admin_role = db.session.query(Role).filter_by(name=appbuilder.sm.auth_role_admin).first()
        admin = db.session.query(User)\
                     .filter(User.role == admin_role)\
                     .first()
        #  We will always have a config named default,
        # to make sure we don't break anything important
        default_config = BlogConfig(
            name="default",
            description="A good default configuration",
            blog_title="Blog Title",
            blog_subtitle="A blog subtitle",
            window_title="A blog",
            edit_lag_in_minutes=15,
            entries_in_sidebar=10,
            entries_per_page=5,
            entries_in_feed=5,
            comments_in_feed=100,
            show_all_tab=True,
            created_by=admin,
            changed_by=admin)
        db.session.add(default_config)
        db.session.flush()
        choose_config = ChooseConfig(chosen_config_id=default_config.id, lock=0,
                created_by=admin, changed_by=admin)
        db.session.add(choose_config)
        db.session.commit()
    except:
        db.session.rollback()

def default_categories():
    # A default category to avoid having zero categories
    try:
        default_category = Category(
            name="default",
            slug="default",
            description="A default category (don't add entries here)",
            show=False,
            index=0)
        db.session.add(default_category)
        db.session.commit()
    except:
        db.session.rollback()

    if len(db.session.query(Category).all()) == 1:
        main_category = Category(
            name="Main",
            slug="main",
            description="Main category for the Blog",
            show=True,
            index=1)
        about_category = Category(
            name="About",
            slug="about",
            description="'About' category for the blog",
            show=True,
            index=2)
        contact_category = Category(
            name="Contact",
            slug="contact",
            description="'Contact' category for the blog",
            show=True,
            index=3)

        db.session.add_all([main_category,
                            about_category,
                            contact_category])
        db.session.commit()

def initialize():
    default_blog_config()
    default_categories()
