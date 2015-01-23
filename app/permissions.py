from flask.ext.appbuilder.security.models import Role, PermissionView

from app import app, db

def make_public(viewcls):
    view_menu_name = viewcls.__class__.__name__

    role_public = db.session.query(Role)\
        .filter(Role.name == app.config['AUTH_ROLE_PUBLIC'])\
        .first()

    public_permission_view = db.session.query(PermissionView)\
        .filter(PermissionView.permission.has(name='can_view_blog'),
                PermissionView.view_menu.has(name='PublicView'))\
        .first()

    role_public.permissions.append(public_permission_view)
    db.session.commit()
