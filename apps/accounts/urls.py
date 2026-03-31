from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from apps.core import views as core_views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-reset/", core_views.password_reset_start, name="password_reset_start"),
    path("password-reset/code/", core_views.password_reset_code, name="password_reset_code"),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]

