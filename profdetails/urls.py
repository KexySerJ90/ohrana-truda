from django.urls import path

from profdetails import views
from profdetails.views import SaveImageView

app_name = "profdetails"


urlpatterns = [
    path('sout-user/', views.SOUTUserView.as_view(), name='sout_user'),
    path('siz/', views.SIZForm.as_view(), name='siz'),
    path('get_equipment/', views.EquipmentListView.as_view(), name='get_equipment'),
    path('generate-image/', views.GenerateImageView.as_view(), name='generate_image'),
    path('save-image/', SaveImageView.as_view(), name='save_image'),
    ]