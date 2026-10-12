from django.contrib.auth import views as auth_views
from django.urls import path

from . import api_views, views

urlpatterns = [
    # Web Application Routes
    path("", views.home, name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="scanner/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("upload/", views.upload, name="upload"),
    path("history/", views.history, name="history"),
    path("result/<int:pk>/", views.result, name="result"),
    path("result/<int:pk>/request-review/", views.request_review, name="request_review"),
    path("medicines/", views.medicines, name="medicines"),
    path("medicines/<int:pk>/", views.medicine_detail, name="medicine_detail"),
    path("pharmacist/", views.pharmacist_dashboard, name="pharmacist_dashboard"),
    path("pharmacist/review/<int:pk>/", views.review, name="review"),

    # Mobile Application REST API Endpoints
    path("api/auth/login/", api_views.api_login, name="api_login"),
    path("api/auth/register/", api_views.api_register, name="api_register"),
    path("api/scan/", api_views.api_scan, name="api_scan"),
    path("api/prescriptions/", api_views.api_prescriptions, name="api_prescriptions"),
    path("api/prescriptions/<int:pk>/", api_views.api_prescription_detail, name="api_prescription_detail"),
    path("api/medicines/", api_views.api_medicines, name="api_medicines"),
]
