from django.http import HttpResponse
from django.views.generic import DetailView, ListView

from blog.decorators import timed
from blog.models import Post

print("blog.views imported")


class PostListView(ListView):
    model = Post


class PostDetailView(DetailView):
    model = Post


@timed
def archive(request, year):
    return HttpResponse(f"archive {year}")


def legacy_detail(request, pk):
    return HttpResponse(f"legacy {pk}")
