import six
import pytz
import dateutil.parser
from abc import ABCMeta

from .resource import ResourceSet
from .exceptions import ApiException, CantSaveException

try:
    from django.conf import settings
    BASE_API_URL = settings.BASE_API_URL
    TIME_ZONE = settings.TIME_ZONE
except Exception:
    try:
        import settings
        BASE_API_URL = settings.BASE_API_URL
        TIME_ZONE = settings.TIME_ZONE
    except AttributeError:
        raise Exception('You must set BASE_API_URL in in a settings.py file in your path.')
    except ImportError:
        # Assume testcase for now
        BASE_API_URL = 'http://localhost:8001/api/'
        TIME_ZONE = 'Europe/London'

bst = pytz.timezone(TIME_ZONE)


class ValidationError(Exception):
    pass


class Manager(object):

    def get_resource(self):
        try:
            return ResourceSet(self.model)
        except AttributeError:
            raise Exception('Manager must have a model to get the resource.')

    def get(self, *args, **kwargs):
        return self.get_resource().get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        return self.get_resource().filter(*args, **kwargs)

    def all(self, *args, **kwargs):
        return self.get_resource().all(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.get_resource().delete(*args, **kwargs)


class ModelBase(ABCMeta):
    """
    Abstract Metaclass for all models.
    Adds Model to Manager
    Adds Manager to access the resource
    """
    def __new__(mcs, name, bases, attrs):
        new_class = super(ModelBase, mcs).__new__(mcs, name, bases, attrs)

        manager = Manager()
        setattr(manager, 'model', new_class)
        setattr(new_class, 'objects', manager)

        return new_class


class Model(six.with_metaclass(ModelBase)):
    """
    Abstract model
    To be extended.
    By default the resource url is constructed from the classname but this can be overridden
    """

    _can_save = False
    _initial_data = None

    @property
    def pk(self):
        try:
            return self.id
        except AttributeError:
            return None

    @classmethod
    def verbose_name(cls):
        return cls.__name__.lower()

    @classmethod
    def validate_data(cls, data):
        return data

    @classmethod
    def url(cls):
        """
        Can be overriden to insert filter kwargs in to the url
        return '%s%ss/{item_pk}/relateditems/' % (BASE_API_URL, cls.verbose_name())
        item_pk filter kwarg will be inserted in to the url
        """
        return '%s%ss/' % (BASE_API_URL, cls.verbose_name())

    @classmethod
    def get_resource(cls):
        return cls.objects.get_resource()

    def serialize(self):
        return self.__dict__

    def serialize_changed(self):
        """
        returns changed data so we can do a patch request
        """
        if self._initial_data is None:
            return self.serialize()
        else:
            changed = {}
            for key, val in self.serialize().iteritems():
                initial_val = self._initial_data.get(key, None)
                if not initial_val or val != initial_val:
                    changed[key] = val
            return changed

    def deserialize(self, data_dict):
        """
        Store the values so we can check for updated fields
        """
        self._initial_data = data_dict
        for key, value in data_dict.iteritems():
            if hasattr(self, '_deserialize_%s' % key):
                value = getattr(self, '_deserialize_%s' % key)(value, data_dict)
            setattr(self, key, value)
        return self

    def save(self, **kwargs):
        if not self._can_save:
            raise CantSaveException('You cant save a %s.' % self.__class__.__name__)
        self.get_resource().save(self, **kwargs)

    def delete(self, **kwargs):
        return self.get_resource().delete(self, **kwargs)

    def deserialize_date(self, date_string):
        return dateutil.parser.parse(date_string)
