from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from meetings.views import MeetingViewSet, MeetingRoomView
from users.views import DashboardView, MeView, RegisterPageView, RegisterView, UserListView

router = DefaultRouter()
router.register("meetings", MeetingViewSet, basename="meeting")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", DashboardView.as_view(), name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="users/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", RegisterPageView.as_view(), name="register-page"),
    path("api/auth/", include("rest_framework.urls")),
    path("api/register/", RegisterView.as_view()),
    path("api/me/", MeView.as_view()),
    path("api/users/", UserListView.as_view()),
    path("api/", include(router.urls)),
    path("meetings/<int:pk>/call/", MeetingRoomView.as_view(), name="meeting-room"),
]
