from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/<int:org_id>/', views.upload_emissions, name='upload_emissions'),
    path('api/emissions/<int:org_id>/', views.org_emissions_api, name='org_emissions_api'),
    path('org/<int:org_id>/', views.org_dashboard, name='org_dashboard'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/<int:org_id>/', views.upload_emissions, name='upload_emissions'),
    path('api/emissions/<int:org_id>/', views.org_emissions_api, name='org_emissions_api'),
    path('api/emissions_forecast/<int:org_id>/', views.org_forecast_api, name='org_forecast_api'),   # NEW
    path('api/emissions_csv/<int:org_id>/', views.org_emissions_csv, name='org_emissions_csv'),     # NEW
    path('org/<int:org_id>/', views.org_dashboard, name='org_dashboard'),
]
