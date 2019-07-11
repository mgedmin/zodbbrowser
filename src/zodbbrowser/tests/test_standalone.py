import errno
import os
import shutil
import socket
import tempfile
import unittest
import sys

import mock
from zope.app.server.servertype import IServerType
from zope.app.testing import setup
from zope.component import provideUtility
from zope.interface import implementer
from ZEO.Exceptions import ClientDisconnected

from zodbbrowser.compat import StringIO
from zodbbrowser.standalone import (
    Options, parse_args, start_server, serve_forever, main, open_db,
    stop_serving)
from zodbbrowser.tests.realdb import RealDatabaseTest


class SocketMixin(object):

    def make_socket(self):
        tempdir = tempfile.mkdtemp(prefix='test-zodbbrowser-')
        self.addCleanup(shutil.rmtree, tempdir)
        sockfilename = os.path.join(tempdir, 'zeosock')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        sock.bind(sockfilename)
        sock.listen(0)
        return sockfilename


class TestParseArgs(SocketMixin, unittest.TestCase):

    def test_sys_argv(self):
        with mock.patch('sys.argv', ['zodbbrowser', '/dev/null']):
            options = parse_args()
        self.assertEqual(options.db_filename, '/dev/null')

    def test_listen_port(self):
        options = parse_args(['--listen', '8000', '/dev/null'])
        self.assertEqual(options.listen_on, ('localhost', 8000))

    def test_listen_host_and_port(self):
        options = parse_args(['--listen', '0.0.0.0:8000', '/dev/null'])
        self.assertEqual(options.listen_on, ('0.0.0.0', 8000))

    def test_listen_bad_port(self):
        with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
            parse_args(['--listen', 'xyzzy', '/dev/null'])

    def test_too_many_args(self):
        with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
            parse_args(['Data-1.fs', 'Data-2.fs'])

    def test_too_few_args(self):
        with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
            parse_args([])

    def test_zeo_and_file(self):
        with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
            parse_args(['--zeo', '/tmp/zeosock', 'Data.fs'])

    def test_zeo_storage_no_zeo(self):
        with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
            parse_args(['--storage', '2', 'Data.fs'])

    def test_zeo_port(self):
        options = parse_args(['--zeo', 'localhost:7099'])
        self.assertEqual(options.zeo_address, ('localhost', 7099))

    def test_zeo_bad_port(self):
        with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
            parse_args(['--zeo', 'localhost:xyzzy'])

    def test_zeo_default_port(self):
        options = parse_args(['--zeo', 'localhost'])
        self.assertEqual(options.zeo_address, ('localhost', 8100))

    def test_zeo_storage(self):
        options = parse_args(['--zeo', 'localhost', '--storage', '2'])
        self.assertEqual(options.zeo_storage, '2')

    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'),
                         "No UNIX domain sockets on this platform")
    def test_zeo_socket(self):
        sockfilename = self.make_socket()
        options = parse_args(['--zeo', sockfilename])
        self.assertEqual(options.zeo_address, sockfilename)

    def test_bad_zeo_socket(self):
        with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
            parse_args(['--zeo', __file__])


class TestOpenDb(unittest.TestCase):

    @unittest.skipIf(sys.platform == 'win32', "This test hangs on Windows")
    def test_zeo(self):
        options = Options()
        options.zeo_address = '/no/such/zeo/socket'
        options.zeo_timeout = 0.001
        with self.assertRaises(ClientDisconnected):
            open_db(options)


@implementer(IServerType)
class FakeServerType(object):
    def create(self, **kw):
        if kw.get('port') == 80:
            raise socket.error(errno.EADDRINUSE, "port busy")
        if kw.get('port') == -1:
            raise socket.error(errno.EINVAL, "bad port")
        sock = mock.Mock()
        sock.getsockname.return_value = ('localhost', 8033)
        return mock.Mock(socket=sock)


class TestStartServer(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        provideUtility(FakeServerType(), name='FAKE')
        self.options = Options()
        self.options.server_type = 'FAKE'
        self.options.verbose = False
        self.db = None

    def tearDown(self):
        stop_serving()
        setup.placelessTearDown()

    def test_prints_clickable_url(self):
        self.options.verbose = True
        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            start_server(self.options, self.db)
        self.assertEqual(mock_stdout.getvalue(),
                         "Listening on http://localhost:8033/\n")

    def test_socket_error_handling_eaddrinuse(self):
        self.options.listen_on = ('localhost', 80)
        with self.assertRaises(SystemExit) as e:
            start_server(self.options, self.db)
        self.assertTrue(
            str(e.exception).startswith("Cannot listen on localhost:80"),
            str(e.exception))

    def test_socket_error_handling_other_kind_of_error(self):
        self.options.listen_on = ('localhost', -1)
        with self.assertRaises(socket.error):
            start_server(self.options, self.db)


class TestServeForever(unittest.TestCase):

    @mock.patch('asyncore.socket_map', {42: None})
    @mock.patch('asyncore.poll', mock.Mock(side_effect=KeyboardInterrupt))
    def test(self):
        serve_forever()


class TestMain(RealDatabaseTest):

    open_db = False

    def setUp(self):
        setup.placelessSetUp()
        RealDatabaseTest.setUp(self)

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    @mock.patch('logging.basicConfig', mock.Mock())
    @mock.patch('zodbbrowser.standalone.open_db', mock.Mock())
    @mock.patch('zodbbrowser.standalone.configure', mock.Mock())
    @mock.patch('zodbbrowser.standalone.start_server', mock.Mock())
    @mock.patch('zodbbrowser.standalone.serve_forever', mock.Mock())
    def test(self):
        main(['--quiet', '--listen', '0', '--rw', self.db_filename])
