from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_index, name='report_index'),
    path('monthly/', views.monthly_report, name='monthly_report'),
    path('annual/', views.annual_report, name='annual_report'),
    path('unpaid/', views.unpaid_report, name='unpaid_report'),
    path('export/monthly/', views.export_monthly, name='export_monthly'),
    path('export/annual/', views.export_annual, name='export_annual'),
    path('export/unpaid/', views.export_unpaid, name='export_unpaid'),
]
