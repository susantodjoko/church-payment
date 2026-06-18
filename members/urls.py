from django.urls import path
from . import views

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('search/', views.member_search, name='member_search'),
    path('new/', views.MemberCreateView.as_view(), name='member_create'),
    path('<int:pk>/', views.member_detail, name='member_detail'),
    path('<int:pk>/edit/', views.MemberUpdateView.as_view(), name='member_update'),
]
