from _collections import defaultdict
from . import Bungiesearch
from .utils import update_index, delete_index_item


__items_to_be_indexed__ = defaultdict(list)
def post_save_connector(sender, instance, **kwargs):
    try:
        buffer_size = Bungiesearch.BUNGIE['SIGNALS']['BUFFER_SIZE']
    except KeyError:
        buffer_size = 100

    __items_to_be_indexed__[sender].append(instance)

    if len(__items_to_be_indexed__[sender]) >= buffer_size:
        update_index(__items_to_be_indexed__[sender], sender.__name__, buffer_size)
        # Let's now empty this buffer or we'll end up reindexing every item which was previously buffered.s
        __items_to_be_indexed__[sender] = []

def pre_delete_connector(sender, instance, **kwargs):
    delete_index_item(instance, sender.__name__)
