from django.contrib.syndication.views import Feed
from django.urls import reverse
from .models import Article

class LatestPostFeed(Feed):
    title = "Статьи - последние записи"
    link = "/feeds/"
    description = "Новые записи на моем сайте."

    def items(self):
        return Article.objects.order_by('-time_update')[:5]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.content

    def item_link(self, item):
        return reverse('main:post', args=[item.slug])