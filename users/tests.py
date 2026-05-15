from django.test import SimpleTestCase

from users.models import CustomUser


class SmokeTestCase(SimpleTestCase):
    def test_custom_user_model_is_configured(self):
        self.assertEqual(CustomUser._meta.label, "users.CustomUser")
