'''
This test signal acts as a proxy to BungieSignalProcessor. It allows us
to test the functionality of the default signal processor while using a
custom processor instead, hence testing that we can plug in and use a custom
signal processor.
'''
from bungiesearch.signals import BungieSignalProcessor
from django.db.models import signals


class BungieTestSignalProcessor(BungieSignalProcessor):

    def handle_save(self, sender, instance, **kwargs):
        self.post_save_connector(sender, instance, **kwargs)

    def handle_delete(self, sender, instance, **kwargs):
        self.pre_delete_connector(sender, instance, **kwargs)

    def setup(self, model):
        signals.post_save.connect(self.handle_save, sender=model)
        signals.pre_delete.connect(self.handle_delete, sender=model)

    def teardown(self, model):
        signals.pre_delete.disconnect(self.handle_delete, sender=model)
        signals.post_save.disconnect(self.handle_save, sender=model)
