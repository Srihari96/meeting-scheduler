from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


class UserInterfaceTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f'{reverse("login")}?next=/')

    def test_logged_in_user_can_view_dashboard(self):
        user = User.objects.create_user(username="alice", password="password123")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Schedule meeting")

    def test_register_page_is_public(self):
        response = self.client.get(
            reverse("register-page")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'value="Asia/Kolkata"',
        )

        self.assertContains(
            response,
            "India — Asia/Kolkata",
        )

    def test_registration_rejects_unknown_timezone(self):
        response = APIClient().post("/api/register/", {
            "username": "bob",
            "password": "password123",
            "preferred_timezone": "Not/A_Timezone",
            "minimum_notice_minutes": 30,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("preferred_timezone", response.data)
