from django.template.defaultfilters import striptags


class AbstractField(object):
    '''
    Represents an elasticsearch index field and values from given objects.
    Currently does not support binary fields, but those can be created by manually providing a dictionary.

    Values are extracted using the `model_attr` or `eval_as` attribute.
    '''
    common_fields = ['index_name', 'store', 'index', 'boost', 'null_value', 'copy_to']
    @property
    def fields(self):
        try:
            return self.fields
        except:
            raise NotImplementedError('Allowed fields are not defined.')

    @property
    def coretype(self):
        try:
            return self.coretype
        except:
            raise NotImplementedError('Core type is not defined!')

    @property
    def defaults(self):
        '''
        Stores default values.
        '''
        try:
            return self.defaults
        except:
            return {}

    def __init__(self, **args):
        '''
        Performs several checks to ensure that the provided attributes are valid. Will not check their values.
        '''
        if isinstance(self.coretype, list):
            if 'coretype' not in args:
                raise KeyError('{} can be represented as one of the following types: {}. Specify which to select as the `coretype` parameter.'.format(unicode(self), ', '.join(self.coretype)))
            if args['coretype'] not in self.coretype:
                raise KeyError('Core type {} is not supported by {}.'.format(args['coretype'], unicode(self)))
            self.type = args.pop('coretype')
        else:
            self.type = self.coretype

        self.model_attr = args.pop('model_attr', None)
        self.eval_func = args.pop('eval_as', None)

        if not self.model_attr and not self.eval_func:
            raise KeyError('{} gets its value via a model attribute or an eval function, but neither of `model_attr`, `eval_as` is provided. Args were {}.'.format(unicode(self), args))

        for attr, value in args.iteritems():
            if attr not in self.fields and attr not in AbstractField.common_fields:
                raise KeyError('Attribute `{}` is not allowed for core type {}.'.format(attr, self.coretype))
            setattr(self, attr, value)

        for attr, value in self.defaults.iteritems():
            if not hasattr(self, attr):
                setattr(self, attr, value)

    def value(self, obj):
        '''
        Computes the value of this field to update the index.
        :param obj: object instance, as a dictionary or as a model instance.
        '''
        if self.eval_func:
            try:
                return eval(self.eval_func)
            except Exception as e:
                raise type(e)('Could not compute value of {} field (eval_as=`{}`): {}.'.format(unicode(self), self.eval_func, unicode(e)))

        if isinstance(obj, dict):
            return obj[self.model_attr]
        return getattr(obj, self.model_attr)

    def json(self):
        return dict((attr, val) for attr, val in self.__dict__.iteritems() if attr not in ['eval_func', 'model_attr'])

# All the following definitions could probably be done with better polymorphism.

class StringField(AbstractField):
    coretype = 'string'
    fields = ['doc_values', 'term_vector', 'norms', 'index_options', 'analyzer', 'index_analyzer', 'search_analyzer', 'include_in_all', 'ignore_above', 'position_offset_gap', 'fielddata', 'similarity']
    defaults = {'analyzer': 'snowball'}

    def value(self, obj):
        return striptags(super(StringField, self).value(obj))

    def __unicode__(self):
        return 'StringField'

class NumberField(AbstractField):
    coretype = ['float', 'double', 'byte', 'short', 'integer', 'long']
    fields = ['doc_values', 'precision_step', 'include_in_all', 'ignore_malformed', 'coerce']

    def __unicode__(self):
        return 'NumberField'

class DateField(AbstractField):
    coretype = 'date'
    fields = ['format', 'doc_values', 'precision_step', 'include_in_all', 'ignore_malformed']

    def __unicode__(self):
        return 'DateField'

class BooleanField(AbstractField):
    coretype = 'boolean'
    fields = [] # No specific fields.

    def __unicode__(self):
        return 'BooleanField'

# Correspondence between a Django field and an elasticsearch field.
def django_field_to_index(field, **attr):
    '''
    Returns the index field type that would likely be associated with each Django type.
    '''

    dj_type = field.get_internal_type()

    if dj_type in ('DateField', 'DateTimeField'):
        return DateField(**attr)
    elif dj_type in ('BooleanField', 'NullBooleanField'):
        return BooleanField(**attr)
    elif dj_type in ('DecimalField', 'FloatField'):
        return NumberField(coretype='float', **attr)
    elif dj_type in ('PositiveSmallIntegerField', 'SmallIntegerField'):
        return NumberField(coretype='short', **attr)
    elif dj_type in ('IntegerField', 'PositiveIntegerField', 'AutoField'):
        return NumberField(coretype='integer', **attr)
    elif dj_type in ('BigIntegerField'):
        return NumberField(coretype='long', **attr)

    return StringField(**attr)
