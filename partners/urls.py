from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views
from . import workspace_views

app_name = 'partners'
urlpatterns = [
    path('workspace/',workspace_views.workspace,name='workspace'),
    path('workspace/records/',workspace_views.records,name='workspace_records'),
    path('workspace/action/',workspace_views.workspace_action,name='workspace_action'),
    path('workspace/owner/',workspace_views.owner,name='workspace_owner'),
    path('login/', views.PartnerLogin.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='partners:login'), name='logout'),
    path('', views.home, name='home'),
    path('trip/', views.trip, name='trip'),
    path('<uuid:pk>/options/', views.options, name='options'),
    path('<uuid:pk>/review/', views.review, name='review'),
    path('<uuid:pk>/preview/', views.preview, name='preview'),
    path('<uuid:pk>/send/', views.send, name='send'),
    path('manual/', views.manual, name='manual'),
]
