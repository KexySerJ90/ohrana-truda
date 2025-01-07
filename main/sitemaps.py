from django.contrib.sitemaps import Sitemap
from .models import Categorys


class CategorySitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Categorys.objects.all()

    # def lastmod(self, obj):
    #     return obj.updated