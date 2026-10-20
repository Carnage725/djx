from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Author, Comment, Post, Tag


class Command(BaseCommand):
    help = "Seed the blog with authors, posts, tags and comments."

    def handle(self, *args, **options):
        User = get_user_model()
        authors = []
        for i in range(3):
            user, _ = User.objects.get_or_create(username=f"author{i}")
            author, _ = Author.objects.get_or_create(user=user, defaults={"bio": f"Bio {i}"})
            authors.append(author)
        tags = [Tag.objects.get_or_create(name=n)[0] for n in ("django", "ninja", "python", "tips")]
        for i in range(8):
            post, created = Post.objects.get_or_create(
                slug=f"post-{i}",
                defaults={
                    "author": authors[i % 3],
                    "title": f"Post {i}",
                    "body": f"Body of post {i}.",
                    "published_at": timezone.now() if i % 4 else None,
                },
            )
            if created:
                post.tags.set(tags[i % 4 : i % 4 + 2])
                for j in range(2):
                    Comment.objects.create(post=post, author_name=f"reader{j}", body="Nice post.")
        self.stdout.write(
            f"authors={Author.objects.count()} posts={Post.objects.count()} "
            f"tags={Tag.objects.count()} comments={Comment.objects.count()}"
        )
