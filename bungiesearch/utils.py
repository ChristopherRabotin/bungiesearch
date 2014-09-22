import logging

from . import Bungiesearch
from elasticsearch.helpers import bulk_index

def update_index(model_items, model_name, bulk_size=100, num_docs=-1):
    '''
    Updates the index for the provided model_items.
    :param model_items: a list of model_items (django Model instances, or proxy instances) which are to be indexed, or updated.
    :param model_name: doctype, which must also be the model name.
    :param bulk_size: bulk size for indexing. Defaults to 100.
    :param num_docs: maximum number of model_items from the provided list to be indexed.
    :note: If model_items contain multiple models, then num_docs is applied to *each* model. For example, if bulk_size is set to 5,
    and item contains models Article and Article2, then 5 model_items of Article *and* 5 model_items of Article2 will be indexed.
    '''
    src = Bungiesearch()

    logging.info('Getting index for model {}.'.format(model_name))
    index_name = src.get_index(model_name)
    index_instance = src.get_model_index(model_name)
    model = index_instance.get_model()

    if num_docs == -1:
        if isinstance(model_items, (list, tuple)):
            num_docs = len(model_items)
        else:
            logging.info('Fetching number of documents to be added to {}.'.format(model.__name__))
            num_docs = model_items.count()
    else:
        logging.warning('Limiting the number of model_items to be indexed to {}.'.format(num_docs))

    logging.info('Indexing {} documents.'.format(num_docs))
    prev_step = 0
    max_docs = num_docs + 1 if num_docs > bulk_size else bulk_size + 1
    for next_step in xrange(bulk_size, max_docs, bulk_size):
        logging.info('Indexing documents {} to {} of {} total.'.format(prev_step, next_step, num_docs))
        bulk_index(src.get_es_instance(), [index_instance.serialize_object(doc) for doc in model_items[prev_step:next_step]], index=index_name, doc_type=model.__name__)
        prev_step = next_step

def delete_index_item(item, model_name):
    '''
    Deletes an item from the index.
    :param item: must be a serializable object.
    :param model_name: doctype, which must also be the model name.
    '''
    src = Bungiesearch()

    logging.info('Getting index for model {}.'.format(model_name))
    index_name = src.get_index(model_name)
    index_instance = src.get_model_index(model_name)
    item_es_id = index_instance.fields['_id'].value(item)
    src.get_es_instance().delete(index_name, model_name, item_es_id)
