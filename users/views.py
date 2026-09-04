from rest_framework import generics, permissions
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .models import User
from .serializers import PreferenceSerializer, RegisterSerializer, UserSummarySerializer
from .timezones import TIMEZONE_CHOICES


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = PreferenceSerializer

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    serializer_class = UserSummarySerializer

    def get_queryset(self):
        return User.objects.exclude(pk=self.request.user.pk).order_by("username")


class RegisterPageView(TemplateView):
    template_name = "users/register.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["timezone_choices"] = TIMEZONE_CHOICES
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "users/dashboard.html"
