from django.conf import settings
from django.test import TestCase

from bungiesearch import Bungiesearch


class SettingsTestCase(TestCase):

    def test_timeout_used(self):
        settings.BUNGIESEARCH['TIMEOUT'] = 29
        search = Bungiesearch()

        self.assertEqual(search.BUNGIE['TIMEOUT'], 29)
        self.assertEqual(search._using.transport.kwargs['timeout'], 29)
