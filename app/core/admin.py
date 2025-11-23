from sqladmin import ModelView
from app.models.user import User
from app.models.post import Post, Comment, PostMedia


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email, User.created_at]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.created_at]

    form_columns = [User.username, User.email, User.bio]

    icon = "fa-solid fa-user"
    name = "User"
    name_plural = "Users"


class PostAdmin(ModelView, model=Post):
    column_list = [Post.id, Post.author, Post.content, Post.created_at]
    column_sortable_list = [Post.created_at]

    icon = "fa-solid fa-newspaper"


class CommentAdmin(ModelView, model=Comment):
    column_list = [Comment.id, Comment.author, Comment.content, Comment.created_at]
    icon = "fa-solid fa-comments"


class MediaAdmin(ModelView, model=PostMedia):
    column_list = [PostMedia.id, PostMedia.filename, PostMedia.post]
    icon = "fa-solid fa-image"
