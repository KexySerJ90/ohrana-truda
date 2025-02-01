"""
URL configuration for ohr project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from main.feeds import LatestPostFeed
from main.sitemaps import CategorySitemap
from main.views import tr_handler403, tr_handler404, tr_handler500
from ohr import settings
from django.contrib.sitemaps.views import sitemap
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView,TokenVerifyView)



sitemaps = {
    'cats': CategorySitemap,
}

urlpatterns = [
    path('aslkglkasgmasmgaskmgaskmkmvikzcmid/', admin.site.urls),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('feeds/latest/', LatestPostFeed(), name='latest_post_feed'),
    path('', include('main.urls', namespace='main')),
    path('users/', include('users.urls', namespace="user")),
    path('study/', include('study.urls', namespace="study")),
    path('ohrana-truda/', include('profdetails.urls', namespace="profdetails")),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path("select2/", include("django_select2.urls")),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('api/', include('drf.urls')),
    path("api-auth/", include("rest_framework.urls")),
    path('api/token/', TokenObtainPairView.as_view(), name = 'token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name = 'token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name = 'token_verify'),
    path('social-auth/', include('social_django.urls', namespace='social')),
]


if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler403 = tr_handler403
handler404 = tr_handler404
handler500 = tr_handler500

admin.site.site_header = "Панель администрирования"
admin.site.index_title = "Охрана труда"