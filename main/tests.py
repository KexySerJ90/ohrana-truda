from django.test import SimpleTestCase, TestCase
from django.urls import reverse, resolve

from main.models import Article
from main.views import IndexView


class IndexURLsTest(SimpleTestCase):
    """    Тестируем URLs    """

    def test_homepage_url_name(self):
        response = self.client.get(reverse('main:index'))
        self.assertEqual(response.status_code, 200)

    def test_root_url_resloves_to_homepage_view(self):
        found = resolve('/')
        self.assertEqual(found.func.view_class, IndexView)


class ArticlePostsTest(TestCase):
    def test_data_home(self):
        a = Article.published.all().select_related('category')
        path=reverse('main:home')
        response = self.client.get(path)
        print(a)