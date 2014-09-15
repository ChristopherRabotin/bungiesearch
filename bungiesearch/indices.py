'''
This bit of code is mostly a mix between haystack and elasticutils.
'''
import logging

from bungiesearch.fields import AbstractField, django_field_to_index


class NoModelError(Exception):
    pass

class MappingType():

    def __init__(self):
        self._results_dict = {}
        self._object = None

    @classmethod
    def from_results(cls, results_dict):
        mt = cls()
        mt._results_dict = results_dict
        return mt

    def _get_object_lazy(self):
        if self._object:
            return self._object
        self._object = self.get_object()
        return self._object

    @classmethod
    def get_index(cls):
        """Returns the index to use for this mapping type.
        You can specify the index to use for this mapping type. This
        affects ``S`` built with this type.
        By default, raises NotImplementedError.
        Override this to return the index this mapping type should
        be indexed and searched in.
        """
        raise NotImplementedError()

    @classmethod
    def get_mapping_type_name(cls):
        """Returns the mapping type name.
        You can specify the mapping type name (also sometimes called the
        document type) with this method.
        By default, raises NotImplementedError.
        Override this to return the mapping type name.
        """
        raise NotImplementedError()

    def get_object(self):
        """Returns the model instance
        This gets called when someone uses the ``.object`` attribute
        which triggers lazy-loading of the object this document is
        based on.
        By default, this calls::
        self.get_model().get(id=self._id)
        where ``self._id`` is the Elasticsearch document id.
        Override it to do something different.
        """
        return self.get_model().get(id=self._id)

    @classmethod
    def get_model(cls):
        """Return the model class related to this MappingType.
        This can be any class that has an instance related to this
        MappingType by id.
        For example, if you're using Django and your MappingType is
        related to a Django model--this should return the Django
        model.
        By default, raises NoModelError.
        Override this to return a class that works with
        ``.get_object()`` to return the instance of the model that is
        related to this document.
        """
        raise NoModelError
    # Simulate attribute access

    def __getattr__(self, name):
        if name in self.__dict__:
        # We want instance/class attributes to take precedence.
        # So if something like that exists, we raise an
        # AttributeError and Python handles it.
            raise AttributeError(name)
        if name == 'object':
        # 'object' is lazy-loading. We don't do this with a
        # property because Python sucks at properties and
        # subclasses.
            return self.get_object()
        # If that doesn't exist, then check the results_dict.
        if name in self._results_dict:
            return self._results_dict[name]
        raise AttributeError(name)
    # Simulate read-only container access

    def __len__(self):
        return self._results_dict.__len__()

    def __getitem__(self, key):
        return self._results_dict.__getitem__(key)

    def __iter__(self):
        return self._results_dict.__iter__()

    def __reversed__(self):
        return self._results_dict.__reversed__()

    def __contains__(self, item):
        return self._results_dict.__contains__(item)

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
            raise AttributeError('Index does not contain a Meta class.')

        self.model = getattr(_meta, 'model', None)
        self.fields = {}
        fields = getattr(_meta, 'fields', [])
        excludes = getattr(_meta, 'exclude', [])
        hotfixes = getattr(_meta, 'hotfixes', {})
        additional_fields = getattr(_meta, 'additional_fields', [])

        # Add in fields from the model.
        self.fields.update(self._get_fields(fields, excludes, hotfixes))
        self.fields_to_fetch = list(set(self.fields.keys()).union(additional_fields))

        # Adding or updating the fields which are defined at class level.
        for cls_attr, obj in self.__class__.__dict__.iteritems():
            if not isinstance(obj, AbstractField):
                continue

            if cls_attr in self.fields:
                logging.info('Overwriting implicitly defined model field {} ({}) its explicit definition: {}.'.format(cls_attr, unicode(self.fields[cls_attr]), unicode(obj)))
            self.fields[cls_attr] = obj

    def get_model(self):
        return self.model

    def get_mapping(self):
        '''
        :return: a dictionary which can be used to generate the elasticsearch index mapping for this doctype.
        '''
        return {'properties': dict((name, field.json()) for name, field in self.fields.iteritems())}

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
                raise ValueError('Could not find object of primary key = {} in model {}. (Original exception: {}.)'.format(obj_pk, self.model, e))

        return dict((name, field.value(obj)) for name, field in self.fields.iteritems())

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
