from flask import Markup
from flask.ext.wtf import Form
from wtforms.fields import StringField, TextAreaField, TextField, HiddenField
from wtforms.widgets import TextArea
from wtforms.validators import Required, Email

class CKTextAreaWidget(TextArea):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('class_', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)

class CKTextAreaField(TextAreaField):
    widget = CKTextAreaWidget

class CommentForm(Form):
    name = StringField("Name",
        validators=[Required(message="Name is required (can be a pseudonym)")])
    email = StringField("Email",
        validators=[Required(message=Markup("Email is required - will <strong>not</strong> be published")),
                    Email(message="Invalid email.")])
    website = StringField("Website")

class NewCommentForm(CommentForm):
    type = HiddenField('new-comment', default='new-comment')
    content = TextAreaField("Content",
        validators=[Required(message="Comment was empty.")])

class EditCommentForm(CommentForm):
    type = HiddenField('edit-comment', default='edit-comment')
    content = TextAreaField("Content",
        validators=[])

class SearchForm(Form):
    search = StringField('search', validators=[Required()])
