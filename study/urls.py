from django.urls import path
from study import views

app_name = 'study'

urlpatterns = [
    path('test/<slug:test_slug>/', views.test_view, name='test'),
    path('subject/<slug:subject_slug>/', views.subject_detail, name='subject_detail'),
    path('video/<slug:video_slug>/', views.VideoInstruktajView.as_view(), name='video_detail'),
    path('answer/<int:answer_id>/', views.AnswerView.as_view(), name='answer'),
    path('result/', views.MyResult.as_view(), name='result'),
    path('leader/', views.LeaderResultsView.as_view(), name='leader_results'),

]