from _collections import defaultdict
import logging
from optparse import make_option

from django.core.management.base import BaseCommand
from elasticsearch.helpers import bulk_index

from ... import Bungiesearch


class Command(BaseCommand):
    args = ''
    help = 'Manage search index.'

    option_list = BaseCommand.option_list + (
        make_option('--create',
            action='store_const',
            dest='action',
            const='create',
            help='Create the index specified in the settings with the mapping generating from the search indices.'),
        make_option('--update',
            action='store_const',
            dest='action',
            const='update',
            help='Update the index specified in the settings with the mapping generating from the search indices.'),
        make_option('--update-mapping',
            action='store_const',
            dest='action',
            const='update-mapping',
            help='Update the mapping of specified models (or all models) on the index specified in the settings.'),
        make_option('--delete',
            action='store_const',
            dest='action',
            const='delete',
            help='Delete the index specified in the settings. Requires the "--guilty-as-charged" flag.'),
        make_option('--delete-mapping',
            action='store_const',
            dest='action',
            const='delete-mapping',
            help='Delete the mapping of specified models (or all models) on the index specified in the settings. Requires the "--guilty-as-charged" flag.'),
        make_option('--guilty-as-charged',
            action='store_true',
            dest='confirmed',
            default=False,
            help='Flag needed to delete an index.'),
        make_option('--models',
            action='store',
            dest='models',
            default=None,
            help='Models to be updated, separated by commas. If none are specified, then all models defined in the index will be updated.'),
        make_option('--index',
            action='store',
            dest='index',
            default=None,
            help='Specify the index for which to apply the action, as defined in BUNGIESEARCH.INDEXES of settings. Defaults to using all indices.'),
        make_option('--bulk-size',
            action='store',
            dest='bulk_size',
            default=100,
            type='int',
            help='Specify the number of items to be updated together.'),
        make_option('--num-docs',
            action='store',
            dest='num_docs',
            default=-1,
            type='int',
            help='Specify the maximum number of items to be indexed. By default will index the whole model.'),
        )

    def handle(self, *args, **options):
        del args
        logging.basicConfig(level='INFO')

        src = Bungiesearch()
        es = src.get_es_instance()

        if not options['action']:
            raise ValueError('No action specified. Must be one of "create", "update" or "delete".')

        if options['action'].startswith('delete'):
            if not options['confirmed']:
                raise ValueError('If you know what a delete operation does (on index or mapping), add the --guilty-as-charged flag.')
            if options['action'] == 'delete':
                if options['index']:
                    indices = [options['index']]
                else:
                    indices = src.get_indices()

                for index in indices:
                    logging.warn('Deleting elastic search index {}.'.format(index))
                    es.indices.delete(index=index, ignore=404)

            else:
                index_to_doctypes = defaultdict(list)
                if options['models']:
                    logging.info('Deleting mapping for models {} on index {}.'.format(options['models'], index))
                    for model_name in options['models'].split():
                        index_to_doctypes[src.get_index(model_name)].append(model_name)
                elif options['index']:
                    index = options['index']
                    logging.info('Deleting mapping for all models on index {}.'.format(index))
                    index_to_doctypes[index] = src.get_models(index)
                else:
                    for index in src.get_indices():
                        index_to_doctypes[index] = src.get_models(index)
                    logging.info('Deleting mapping for all models ({}) on all indices ({}).'.format(index_to_doctypes.values(), index_to_doctypes.keys()))

                for index, doctype_list in index_to_doctypes.iteritems():
                    es.indices.delete_mapping(index, ','.join(doctype_list), params=None)

        elif options['action'] == 'create':
            if options['index']:
                indices = [options['index']]
            else:
                indices = src.get_indices()

            for index in indices:
                mapping = {}
                for mdl_idx in src.get_model_indices(index):
                    mapping[mdl_idx.get_model().__name__] = mdl_idx.get_mapping()

                logging.info('Creating index {} with {} doctypes.'.format(index, len(mapping)))
                es.indices.create(index=index, body={'mappings': mapping})

        elif options['action'] == 'update-mapping':
            if options['models']:
                model = options['models']
                for model_name in options['models'].split():
                    index = src.get_index(model_name)
                    logging.info('Updating mapping of model/doctype {} on index {}.'.format(model_name, index))
                    es.indices.put_mapping(model_name, src.get_model_index(model_name).get_mapping(), index=index)
            else:
                for model_name, model_idx in src._model_name_to_model_idx.iteritems():
                    index = src.get_index(model_name)
                    logging.info('Updating mapping of model/doctype {} on index {}.'.format(model_name, index))
                    es.indices.put_mapping(model_name, model_idx.get_mapping(), index=index)

        else:
            if options['models']:
                logging.info('Updating models {}.'.format(options['models']))
                model_names = options['models'].split(',')
            elif options['index']:
                index = options['index']
                logging.info('Updating all models on index {}.'.format(options['index']))
                model_names = src.get_models(index)
            else:
                model_names = [model for index in src.get_indices() for model in src.get_models(index)]
            # Update index.
            for model_name in model_names:
                print 'Getting index for', model_name
                index_name = src.get_index(model_name)
                index_instance = src.get_model_index(model_name)
                model = index_instance.get_model()

                model_fetch = model.objects.all()
                if options['num_docs'] == -1:
                    logging.info('Fetching number of documents to be added to {}.'.format(model.__name__))
                    num_docs = model_fetch.count()
                else:
                    num_docs = options['num_docs']
                    logging.warning('Forcing the number of items to be idnexed to {}.'.format(num_docs))
                logging.info('Indexing {} documents.'.format(num_docs))
                prev_step = 0
                bulk_size = options['bulk_size']
                max_docs = num_docs if num_docs > bulk_size else bulk_size + 1
                for next_step in xrange(bulk_size, max_docs, bulk_size):
                    logging.info('Indexing documents pk\'d {} to {} of {} total.'.format(prev_step, next_step, num_docs))
                    bulk_index(es, [index_instance.serialize_object(doc) for doc in model_fetch[prev_step:next_step]], index=index_name, doc_type=model.__name__)
                    prev_step = next_step
