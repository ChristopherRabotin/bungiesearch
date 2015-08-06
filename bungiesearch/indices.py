import logging

from bungiesearch.fields import AbstractField, django_field_to_index
from six import iteritems

from elasticsearch_dsl.analysis import Analyzer


class ModelIndex(object):
    '''
    Introspects a model to generate an indexable mapping and methods to extract objects.
    Supports custom fields, including Python code, and all elasticsearch field types (apart from binary type).

    ModelIndex does efficient querying by only fetching from the database fields which are to be indexed.

    How to create an index?

    1. Create a class which inherits from ModelIndex.
    2. Define custom indexed fields as class attributes. Values must be instances AbstractField. Important info in 3b.
    3. Define a `Meta` subclass, which must contain at least `model` as a class attribute.
        a. Optional class attributes: `fields`, `excludes` and `additional_fields`.
        b. If custom indexed field requires model attributes which are not in the difference between `fields` and `excludes`, these must be defined in `additional_fields`.
    '''
    def __init__(self):
        # Introspect the model, adding/removing fields as needed.
        # Adds/Excludes should happen only if the fields are not already
        # defined in `self.fields`.
        try:
            _meta = getattr(self, 'Meta')
        except AttributeError:
            raise AttributeError('ModelIndex {} does not contain a Meta class.'.format(self.__class__.__name__))

        self.model = getattr(_meta, 'model', None)
        self.fields = {}
        fields = getattr(_meta, 'fields', [])
        excludes = getattr(_meta, 'exclude', [])
        hotfixes = getattr(_meta, 'hotfixes', {})
        additional_fields = getattr(_meta, 'additional_fields', [])
        id_field = getattr(_meta, 'id_field', 'id')
        self.updated_field = getattr(_meta, 'updated_field', None)
        self.optimize_queries = getattr(_meta, 'optimize_queries', False)
        self.is_default = getattr(_meta, 'default', True)
        self.indexing_query = getattr(_meta, 'indexing_query', None)

        # Add in fields from the model.
        self.fields.update(self._get_fields(fields, excludes, hotfixes))
        # Elasticsearch uses '_id' to identify items uniquely, so let's duplicate that field.
        # We're duplicating it in order for devs to still perform searches on `.id` as expected.
        self.fields['_id'] = self.fields[id_field]
        self.fields_to_fetch = list(set(self.fields.keys()).union(additional_fields))

        # Adding or updating the fields which are defined at class level.
        for cls_attr, obj in iteritems(self.__class__.__dict__):
            if not isinstance(obj, AbstractField):
                continue

            if cls_attr in self.fields:
                logging.info('Overwriting implicitly defined model field {} ({}) its explicit definition: {}.'.format(cls_attr, unicode(self.fields[cls_attr]), unicode(obj)))
            self.fields[cls_attr] = obj

    def matches_indexing_condition(self, item):
        '''
        Returns True by default to index all documents.
        '''
        return True

    def get_model(self):
        return self.model

    def get_mapping(self):
        '''
        :return: a dictionary which can be used to generate the elasticsearch index mapping for this doctype.
        '''
        return {'properties': dict((name, field.json()) for name, field in iteritems(self.fields))}

    def collect_analysis(self):
        '''
        :return: a dictionary which is used to get the serialized analyzer definition from the analyzer class.
        '''
        analysis = {}    
        for field in self.fields.values():
            for analyzer_name in ('analyzer', 'index_analyzer', 'search_analyzer'):
                if not hasattr(field, analyzer_name):
                    continue

                analyzer = getattr(field, analyzer_name)

                if not isinstance(analyzer, Analyzer):
                    continue

                definition = analyzer.get_analysis_definition()
                if definition is None:
                    continue

                for key in definition:
                    analysis.setdefault(key, {}).update(definition[key])

        return analysis

    def serialize_object(self, obj, obj_pk=None):
        '''
        Serializes an object for it to be added to the index.

        :param obj: Object to be serialized. Optional if obj_pk is passed.
        :param obj_pk: Object primary key. Supersedded by `obj` if available.
        :return: A dictionary representing the object as defined in the mapping.
        '''
        if not obj:
            try:
                # We're using `filter` followed by `values` in order to only fetch the required fields.
                obj = self.model.objects.filter(pk=obj_pk).values(*self.fields_to_fetch)[0]
            except Exception as e:
                raise ValueError('Could not find object of primary key = {} in model {} (model index class {}). (Original exception: {}.)'.format(obj_pk, self.model, self.__class__.__name__, e))

        return dict((name, field.value(obj)) for name, field in iteritems(self.fields))

    def _get_fields(self, fields, excludes, hotfixes):
        '''
        Given any explicit fields to include and fields to exclude, add
        additional fields based on the associated model. If the field needs a hotfix, apply it.
        '''
        final_fields = {}
        fields = fields or []
        excludes = excludes or []

        for f in self.model._meta.fields:
            # If the field name is already present, skip
            if f.name in self.fields:
                continue

            # If field is not present in explicit field listing, skip
            if fields and f.name not in fields:
                continue

            # If field is in exclude list, skip
            if excludes and f.name in excludes:
                continue

            # If field is a relation, skip.
            if getattr(f, 'rel'):
                continue

            attr = {'model_attr': f.name}
            if f.has_default():
                attr['null_value'] = f.default

            if f.name in hotfixes:
                attr.update(hotfixes[f.name])

            final_fields[f.name] = django_field_to_index(f, **attr)

        return final_fields

    def __str__(self):
        return '<{0.__class__.__name__}:{0.model.__name__}>'.format(self)