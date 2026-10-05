from django.contrib.auth import views as auth_views
from django.urls import path

app_name = "contas"

urlpatterns = [
    path(
        "entrar/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="entrar",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="sair"),
]
