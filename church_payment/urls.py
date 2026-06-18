from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('', include('dashboard.urls')),
    path('members/', include('members.urls')),
    path('payments/', include('payments.urls')),
    path('reports/', include('reports.urls')),
    path('settings/', include('settings_admin.urls')),
]
