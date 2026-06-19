from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.UserListView.as_view(), name='settings_users'),
    path('wilayah/', views.WilayahListView.as_view(), name='settings_wilayah'),
    path('lingkungan/', views.WilayahListView.as_view(), name='settings_lingkungan'),
    path('payment-types/', views.PaymentTypeListView.as_view(), name='settings_payment_types'),
    path('keluarga/', views.KeluargaListView.as_view(), name='settings_keluarga'),
    path('keluarga/<int:pk>/toggle-active/', views.KeluargaToggleActiveView.as_view(), name='keluarga_toggle_active'),
]
