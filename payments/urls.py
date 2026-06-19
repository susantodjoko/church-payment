from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.record_payment, name='record_payment'),
    path('', views.payment_list, name='payment_list'),
    path('batch-report/', views.batch_report, name='batch_report'),
    path('laporan-masuk/', views.LaporanMasukView.as_view(), name='laporan_masuk'),
    path('confirm/', views.confirm_laporan, name='confirm_laporan'),
]
