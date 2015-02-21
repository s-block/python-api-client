python-api-client
=========================

Python client to connect to REST based api


This is still in its early stages and needs more tests and functionality for PUT, POST, PATCH and DELETE methods


To run the tests
----------------

pip install -r test_requirements.txt

python tests.py


Usage
-----

If you are using Django put the following in to your settings file:

```python
BASE_API_URL = "http://yourdomain.com/api/v2/"
```

If you are not using Django create a file called settings.py in your project and add the line to that.


Models:
```python
from python_api_client.models import Model


class MyModel(Model):
    """
    This assumes a url of http://yourdomain.com/api/v2/mymodels/...
    if this is not the case you can override

    @classmethod
    def url(cls):
        return 'whatever url you want'

    """
   pass
```

Views:
```python
from .models import MyModel


my_models = MyModel.objects.all()

some_of_my_models = MyModel.objects.filter(something='s)

my_model = MyModel.objects.get(pk=2)
my_model.field = 'changed'
my_model.save()

```