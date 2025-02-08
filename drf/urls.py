from django.urls import include, path
from rest_framework import routers

from drf.views import ArticleViewSet, UploadFilesViewSet, LeaderViewSet, ProfileAPIUpdate, UserLoginHistoryViewSet, \
    JobDetailsListViewSet, TagViewSet, ProfessionViewSet, CategoryViewSet, EquipmentViewSet

app_name = "drf"


router=routers.DefaultRouter()
router.register(r'ohrlist', ArticleViewSet)
router.register(r'upload', UploadFilesViewSet, basename='upload')
router.register(r'tags-view', TagViewSet, basename='tags_view')
router.register(r'category', CategoryViewSet, basename='category')
router.register(r'subject', CategoryViewSet, basename='subject')
router.register(r'leader-users', LeaderViewSet, basename='leader')
router.register(r'profile-users', ProfileAPIUpdate, basename='profile')
router.register(r'login-history', UserLoginHistoryViewSet, basename='login_history')
router.register(r'job-details-list', JobDetailsListViewSet, basename='job_details_listView')
router.register(r'equipment', EquipmentViewSet, basename='equipment')
router.register(r'profession', ProfessionViewSet, basename='profession')
router.register(r'department', ProfessionViewSet, basename='department')




urlpatterns = [
    path('v1/', include(router.urls)),]