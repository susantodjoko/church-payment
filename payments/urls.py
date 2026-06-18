from django.urls import path
from . import views

urlpatterns = [
    path('new/', views.record_payment, name='record_payment'),
    path('', views.payment_list, name='payment_list'),
]
