from _collections import defaultdict
from . import Bungiesearch
from .utils import update_index


__items_to_be_indexed__ = defaultdict(list)
def post_save_connector(sender, instance, **kwargs):
    try:
        buffer_size = Bungiesearch.BUNGIE['SIGNALS']['BUFFER_SIZE']
    except KeyError:
        buffer_size = 100
    
    __items_to_be_indexed__[sender].append(instance)
    
    if len(__items_to_be_indexed__[sender]) >= buffer_size:
        update_index(__items_to_be_indexed__[sender], sender.__name__, buffer_size)