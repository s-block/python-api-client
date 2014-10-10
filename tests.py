import SimpleHTTPServer
import SocketServer
import threading
import unittest
import time

from mock import patch

from python_api_client.exceptions import NotFoundException, CantSaveException
from python_api_client.models import Model, BASE_API_URL


PORT = 8001


def build_url(self, lookup=None):
    url = self.url
    if lookup:
        url = '%s%s/' % (url, lookup)
    for key, val in self._filters.iteritems():
        if '{%s}' % key in url:
            url = url.replace('{%s}' % key, unicode(val))
    return url + 'response.json'


class TestTCPServer(SocketServer.TCPServer):
    allow_reuse_address = True


class TestModel(Model):
    pass


class RelatedModel(Model):
    @classmethod
    def url(cls):
        return '%stestmodels/{testmodel_pk}/%ss/' % (BASE_API_URL, cls.verbose_name())


class SaveModel(Model):
    _can_save = True


class ApiClientTestCase(unittest.TestCase):
    """
    This test is limited to GET requests at the moment
    """
    def setUp(self):
        super(ApiClientTestCase, self).setUp()
        handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        self.httpd = TestTCPServer(("", PORT), handler)
        self.httpd_thread = threading.Thread(target=self.httpd.serve_forever)
        self.httpd_thread.setDaemon(True)
        self.httpd_thread.start()

        self.patcher = patch('python_api_client.resource.ResourceSet.build_url', build_url)

    def tearDown(self):
        self.httpd.server_close()
        self.httpd.shutdown()
        try:
            self.patcher.stop()
        except RuntimeError:
            pass

    def test_url(self):
        rs = TestModel.objects.all()
        url = rs.build_url()
        self.assertEqual(url, '%stestmodels/' % BASE_API_URL,
                         'Base URL is not correct: %s != %stestmodels/' % (url, BASE_API_URL))

        rs = RelatedModel.objects.filter(testmodel_pk=1)
        url = rs.build_url()
        self.assertEqual(url, '%stestmodels/1/relatedmodels/' % BASE_API_URL,
                         'Base URL for related is not correct: %s != %stestmodels/1/relatedmodels/' % (url, BASE_API_URL))

        rs = rs.filter(test_param='test', test_param_two='test2')
        url = rs.build_url()
        self.assertEqual(url, '%stestmodels/1/relatedmodels/' % BASE_API_URL,
                         'Base URL is not correct after adding param: %s != %stestmodels/1/relatedmodels/' % (url, BASE_API_URL))
        qs = rs.query_string()
        self.assertEqual(qs, 'test_param=test&test_param_two=test2',
                         'Query String is not correct: %s != test_param=test&test_param_two=test2' % qs)

        rs = TestModel.objects.all()[4:6]
        url = rs.build_url()
        self.assertEqual(url, '%stestmodels/' % BASE_API_URL,
                         'Base URL is not correct after slicing: %s != %stestmodels/' % (url, BASE_API_URL))
        qs = rs.query_string()
        self.assertEqual(qs, 'limit_start=4&limit_stop=6',
                         'Query String is not correct after slicing: %s != limit_start=4&limit_stop=6' % qs)

    def test_model(self):
        self.patcher.start()
        m = TestModel.objects.get(pk=1)
        self.assertEqual(m.__class__.__name__, 'TestModel',
                         'Object returned from get should be TestModel but was %s' % m.__class__.__name__)
        self.assertEqual(m.name, 'Test Model One', 'Object attribute was not set correctly.')

    def test_resource_set(self):
        self.patcher.start()
        rs = TestModel.objects.all()
        self.assertEqual(rs.__class__.__name__, 'ResourceSet',
                         'Object returned from all should be ResourceSet but was %s' % rs.__class__.__name__)
        rs_len = len(rs)
        self.assertEqual(rs_len, 3, 'ResourceSet should have len() == 3, got %s' % rs_len)

        #TODO - need to implement limits on the test endpoint for the following to pass
        """
        rs = TestModel.objects.all()[:1]
        self.assertEqual(rs.__class__.__name__, 'ResourceSet',
                         'Object returned from all should be ResourceSet but was %s' % rs.__class__.__name__)
        rs_len = len(rs)
        self.assertEqual(rs_len, 2, 'ResourceSet should have len() == 2, got %s' % rs_len)

        m = TestModel.objects.all()[1]
        self.assertEqual(m.__class__.__name__, 'TestModel',
                         'Object returned from all should be TestModel but was %s' % m.__class__.__name__)
        self.assertEqual(m.pk, 2, 'Should return second object in list (pk=2), pk was %s' % m.pk)
        """

    def test_404(self):
        self.patcher.start()
        self.assertRaises(NotFoundException, TestModel.objects.get, pk=10)

    def test_save(self):
        self.patcher.start()
        m = TestModel.objects.get(pk=1)
        self.assertRaises(CantSaveException, m.save)

        #TODO - test endpoint needs to support patch to pass folowing
        """
        m = SaveModel.objects.get(pk=1)
        m.name = 'New Name'
        m.save()
        """

        #TODO - test endpoint needs to support post to pass folowing
        """
        m = SaveModel()
        m.name = 'New Name'
        m.description = 'Description'
        m.save()
        """

    def test_delete(self):
        pass

        #TODO - test endpoint needs to support delete to pass folowing
        """
        self.patcher.start()
        m = TestModel.objects.get(pk=1)
        m.delete()
        """


if __name__ == '__main__':
    unittest.main()

