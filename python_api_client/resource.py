import requests
import six
import json
from urllib import urlencode

from .exceptions import ResourceSetException, AuthFailureException, NotFoundException, ApiException, get_exception_class

CHUNK_SIZE = 100
ITER_CHUNK_SIZE = CHUNK_SIZE

DELETE_STATUS = [200, 202, 204]


class Meta(object):
    def __init__(self, **vars):
        self.__dict__.update(vars)


class ResourceSet(object):
    """
    ResourceSet uses python requests to send requests to an api endpoint.

    The url of the endpoint is built using the model.url() and then adds to this
    depending on the request params/type.

    It will return a deserialized model object for item/get requests or a
    lazy loading iterator of model objects for filter/list requests.
    """

    def __init__(self, model, *args, **kwargs):
        self.model = model
        self._meta = None
        self._result_cache = None
        self._iter = None
        self._limit_start = None
        self._limit_stop = None
        self._filters = {}
        self._token = None

    def __len__(self):
        if self._result_cache is None:
            if self._iter:
                self._result_cache = list(self._iter)
            else:
                self._result_cache = list(self.iterator())
        elif self._iter:
            self._result_cache.extend(self._iter)
        return len(self._result_cache)

    def __iter__(self):
        if self._result_cache is None:
            self._iter = self.iterator()
            self._result_cache = []
        if self._iter:
            return self._result_iter()
        return iter(self._result_cache)

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."

        if self._result_cache is not None:
            if self._iter is not None:
                # See if we need to get more items for the result cache
                if isinstance(k, slice):
                    if k.stop is not None:
                        # convert to int if string
                        bound = int(k.stop)
                    else:
                        bound = None
                else:
                    bound = k + 1
                if len(self._result_cache) < bound:
                    self._fill_cache(bound - len(self._result_cache))
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.set_limits(start, stop)
            return k.step and list(qs)[::k.step] or qs
        try:
            qs = self._clone()
            qs.set_limits(k, k + 1)
            return list(qs)[0]
        except self.model.DoesNotExist as e:
            raise IndexError(e.args)

    def _result_iter(self):
        pos = 0
        while 1:
            upper = len(self._result_cache)
            while pos < upper:
                yield self._result_cache[pos]
                pos = pos + 1
            if not self._iter:
                raise StopIteration
            if len(self._result_cache) <= pos:
                self._fill_cache()

    def _fill_cache(self, num=None):
        if self._iter:
            try:
                for i in range(num or ITER_CHUNK_SIZE):
                    self._result_cache.append(next(self._iter))
            except StopIteration:
                self._iter = None

    def iterator(self, *args, **kwargs):
        """
        Make the request and yield the results
        """
        response = self.send('get', self.build_url(), params=self.params, **kwargs)

        response_json = response.json()

        #TODO - standardize the list response to a dict with objects
        # at the moment the api returns a list with no meta in a couple of places
        if isinstance(response_json, list):
            data_list = response_json
        else:
            #TODO - make 'objects' configurable so we can have any api list structure
            data_list = response_json.get('objects', response_json)
            self._meta = Meta(**response_json.get('meta', {}))

        for data in data_list:
            instance = self.model()
            instance.deserialize(data)
            yield instance

    def set_limits(self, start, stop):
        self._limit_start = start
        self._limit_stop = stop

    def filter(self, **kwargs):
        self._token = kwargs.pop('token', self._token)
        self._filters.update(kwargs)
        return self

    def all(self, **kwargs):
        self._token = kwargs.pop('token', self._token)
        return self

    def get(self, pk=None, slug=None, code=None, **kwargs):
        self._token = kwargs.pop('token', self._token)
        lookup = pk or slug or code
        if not lookup and not self._token:
            raise ResourceSetException('You need to specify a pk, slug, code or a token to use get()')
        url = self.build_url(lookup=lookup)

        response = self.send('get', url, **kwargs)
        data = response.json()
        instance = self.model()
        instance.deserialize(data)
        return instance

    def patch(self, instance, **kwargs):
        self._token = kwargs.pop('token', self._token)
        url = self.build_url(lookup=instance.pk)
        data = self.model.validate_data(instance.serialize_changed())
        if data:
            response = self.send('patch', url, data=json.dumps(data), **kwargs)
            if response.status_code not in [200, 201, 202]:
                raise ResourceSetException('Expected status code 200, 201, 202, got %s' % (response.status_code))
        return instance

    def save(self, instance, **kwargs):
        self._token = kwargs.pop('token', self._token)
        if instance.pk:
            return self.patch(instance)
        data = self.model.validate_data(instance.serialize())
        response = self.send('post', self.url, data=json.dumps(data), **kwargs)
        if response.status_code != 201:
            raise ResourceSetException('Expected status code 201, got %s' % (response.status_code))
        return instance

    def delete(self, instance, **kwargs):
        self._token = kwargs.pop('token', self._token)
        url = self.build_url(lookup=instance.pk)
        response = self.send('delete', url, **kwargs)
        if response.status_code not in DELETE_STATUS:
            raise ResourceSetException('Expected status code %s, got %s' % (DELETE_STATUS, response.status_code))
        self._result_cache = None

    @property
    def url(self):
        return self.model.url()

    @property
    def params(self):
        data = {k: v for k, v in self._filters.iteritems() if '{%s}' % k not in self.url}
        if self._limit_start:
            data['limit_start'] = self._limit_start
        if self._limit_start:
            data['limit_stop'] = self._limit_stop
        return data

    @property
    def meta(self):
        if self._meta is None:
            # force lazy load to load
            len(self)
        return self._meta

    def query_string(self):
        return urlencode(self.params)

    def build_url(self, lookup=None):
        url = self.url
        if lookup:
            url = '%s%s/' % (url, lookup)
        for key, val in self._filters.iteritems():
            if '{%s}' % key in url:
                url = url.replace('{%s}' % key, unicode(val))
        return url

    def send(self, method, url, **kwargs):
        """
        Send the request and return the result

        If a token is passed then we add the JWT token to the request headers

        If the API is in debug, we add the traceback to a new exception so it can be seen on the front end
        """

        self._token = kwargs.pop('token', self._token)

        headers = kwargs.pop('headers', {})
        if self._token:
            headers['AUTHORIZATION'] = 'JWT %s' % self._token
        data = kwargs.pop('data', None)
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        if data and method in ['put', 'post']:
            headers.update({
                'Content-type': 'application/json',
                'Accept': 'text/plain'
            })
        response = requests.request(method, url, headers=headers, data=data, **kwargs)
        error_message = None
        error = None
        try:
            response_json = response.json()
        except ValueError:
            response_json = None
        # If the API is in debug, add the traceback to a new exception so it can be seen on the front end
        if response.status_code >= 400 or response_json is None or \
                'traceback' in response_json or 'error' in response_json:
            error = 'Unknown error'
            traceback = 'No traceback'
            content = response.content
            try:
                error = response_json.get('error', error)
                traceback = response_json.get('traceback', traceback)
                content = response_json
            except AttributeError:
                pass

            error_message = 'API %s error on %s with method=%s - %s' % (response.status_code, url, method, error)
            error_message += "\n%s" % error
            error_message += "\n%s" % traceback
            error_message += "\n%s" % content

        if error_message and error:
            e = get_exception_class(response.status_code, error)(error_message)
            e.message = error
            raise e
        return response

    def _clone(self):
        clone = self.__class__(self.model)
        clone._token = self._token
        clone._limit_start = self._limit_start
        clone._limit_stop = self._limit_stop
        clone._filters = self._filters
        return clone
