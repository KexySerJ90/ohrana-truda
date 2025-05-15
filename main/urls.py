from django.urls import path

from main import views

app_name = 'main'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('maindoc/<slug:dep_slug>/', views.Mainfiles.as_view(), name='maindoc'),
    path('about/', views.about, name='about'),
    path('consent/', views.consent, name='consent'),
    path('addfile/', views.UploadFileView.as_view(), name='add_file'),
    path('posts/', views.ArticlePosts.as_view(), name='home'),
    path('addpost/', views.AddPostView.as_view(), name='addpost'),
    path('post/<slug:post_slug>/', views.ShowPost.as_view(), name='post'),
    path('post/<int:pk>/comments/create/', views.CommentCreateView.as_view(), name='comment_create_view'),
    path('post/<int:post_pk>/comments/delete/<int:pk>/', views.CommentDeleteView.as_view(), name='comment_delete_view'),
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('archive/', views.ArchiveNotifications.as_view(), name='archive'),
    path('notifications/read/<int:pk>/', views.NotificationReadView.as_view(), name='notification_read'),
    path('notice/read/<int:pk>/', views.NoticeReadView.as_view(), name='notice_read'),
    path('category/<slug:cat_slug>/', views.ArticleCategory.as_view(), name='category'),
    path('edit/<slug:slug>/', views.UpdatePage.as_view(), name='edit_page'),
    path('tag/<slug:tag_slug>/', views.TagPostList.as_view(), name='tag'),
    path('search/', views.PostSearchView.as_view(), name='post_search'),
    path('rating/', views.RatingCreateView.as_view(), name='rating'),
    path('contact/', views.contact_view, name='contact'),
    path('login-history/', views.LoginHistoryView.as_view(), name='login_history'),
]


