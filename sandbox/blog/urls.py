from django.urls import path

from blog import views

app_name = "blog"

urlpatterns = [
    path("blog/", views.PostListView.as_view(), name="post-list"),
    path("blog/<slug:slug>/", views.PostDetailView.as_view(), name="post-detail"),
    path("blog/archive/<int:year>/", views.archive, name="archive"),
]
