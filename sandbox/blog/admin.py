from django.contrib import admin

from blog.models import Author, Comment, Post, Tag

for model in (Author, Tag, Post, Comment):
    admin.site.register(model)
