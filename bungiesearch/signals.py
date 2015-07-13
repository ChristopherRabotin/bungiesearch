from _collections import defaultdict
from importlib import import_module

from django.db.models import signals

from . import Bungiesearch
from .utils import update_index, delete_index_item


def get_signal_processor():
    signals = Bungiesearch.BUNGIE['SIGNALS']
    if 'SIGNAL_CLASS' in signals:
        signal_path = signals['SIGNAL_CLASS'].split('.')
        signal_module = import_module('.'.join(signal_path[:-1]))
        signal_class = getattr(signal_module, signal_path[-1])
    else:
        signal_class = BungieSignalProcessor
    return signal_class()

__items_to_be_indexed__ = defaultdict(list)
class BungieSignalProcessor(object):

    def post_save_connector(self, sender, instance, **kwargs):
        try:
            Bungiesearch.get_index(sender, via_class=True)
        except KeyError:
            return # This model is not managed by Bungiesearch.

        try:
            buffer_size = Bungiesearch.BUNGIE['SIGNALS']['BUFFER_SIZE']
        except KeyError:
            buffer_size = 100

        __items_to_be_indexed__[sender].append(instance)

        if len(__items_to_be_indexed__[sender]) >= buffer_size:
            update_index(__items_to_be_indexed__[sender], sender.__name__, bulk_size=buffer_size)
            # Let's now empty this buffer or we'll end up reindexing every item which was previously buffered.
            __items_to_be_indexed__[sender] = []

    def pre_delete_connector(self, sender, instance, **kwargs):
        try:
            Bungiesearch.get_index(sender, via_class=True)
        except KeyError:
            return # This model is not managed by Bungiesearch.

        delete_index_item(instance, sender.__name__)

    def setup(self, model):
        signals.post_save.connect(self.post_save_connector, sender=model)
        signals.pre_delete.connect(self.pre_delete_connector, sender=model)

    def teardown(self, model):
        signals.pre_delete.disconnect(self.pre_delete_connector, sender=model)
        signals.post_save.disconnect(self.post_save_connector, sender=model)
