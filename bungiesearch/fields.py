from django.template import Context, loader
from django.template.defaultfilters import striptags
from six import iteritems

from elasticsearch_dsl.analysis import Analyzer


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
        self.template_name = args.pop('template', None)

        for attr, value in iteritems(args):
            if attr not in self.fields and attr not in AbstractField.common_fields:
                raise KeyError('Attribute `{}` is not allowed for core type {}.'.format(attr, self.coretype))
            setattr(self, attr, value)

        for attr, value in iteritems(self.defaults):
            if not hasattr(self, attr):
                setattr(self, attr, value)

    def value(self, obj):
        '''
        Computes the value of this field to update the index.
        :param obj: object instance, as a dictionary or as a model instance.
        '''
        if self.template_name:
            t = loader.select_template([self.template_name])
            return t.render(Context({'object': obj}))

        if self.eval_func:
            try:
                return eval(self.eval_func)
            except Exception as e:
                raise type(e)('Could not compute value of {} field (eval_as=`{}`): {}.'.format(unicode(self), self.eval_func, unicode(e)))

        elif self.model_attr:
            if isinstance(obj, dict):
                return obj[self.model_attr]
            current_obj = getattr(obj, self.model_attr)

            if callable(current_obj):
                return current_obj()
            else:
                return current_obj

        else:
            raise KeyError('{0} gets its value via a model attribute, an eval function, a template, or is prepared in a method '
                           'call but none of `model_attr`, `eval_as,` `template,` `prepare_{0}` is provided.'.format(unicode(self)))

    def json(self):
        json = {}
        for attr, val in iteritems(self.__dict__):
            if attr in ('eval_func', 'model_attr', 'template_name'):
                continue
            elif attr in ('analyzer', 'index_analyzer', 'search_analyzer') and isinstance(val, Analyzer):
                json[attr] = val.to_dict()
            else:
                json[attr] = val

        return json

# All the following definitions could probably be done with better polymorphism.
class StringField(AbstractField):
    coretype = 'string'
    fields = ['doc_values', 'term_vector', 'norms', 'index_options', 'analyzer', 'index_analyzer', 'search_analyzer', 'include_in_all', 'ignore_above', 'position_offset_gap', 'fielddata', 'similarity']
    defaults = {'analyzer': 'snowball'}

    def value(self, obj):
        val = super(StringField, self).value(obj)
        if val is None:
            return None
        return striptags(val)

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
