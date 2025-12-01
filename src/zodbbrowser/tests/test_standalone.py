import errno
import logging
import os
import shutil
import socket
import sys
import tempfile
import unittest

import mock
from ZEO.Exceptions import ClientDisconnected
from zope.app.testing import setup

from zodbbrowser.compat import StringIO
from zodbbrowser.standalone import (
    Options,
    close_database,
    format_exception,
    main,
    open_db,
    parse_args,
    print_exception,
    serve_forever,
    start_server,
)
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


class TestExceptionFormatting(unittest.TestCase):

    def test_print_exception(self):
        file = StringIO()
        try:
            raise Exception('hello')
        except Exception as e:
            print_exception(e, file=file)
        output = file.getvalue()
        self.assertTrue(
            output.startswith('Traceback (most recent call last):'), output
        )
        self.assertTrue(
            output.endswith('Exception: hello\n'), output
        )

    def test_format_exception(self):
        file = StringIO()
        try:
            raise Exception('hello')
        except Exception as e:
            output = format_exception(e, file=file)
        self.assertEqual(output[0], 'Traceback (most recent call last):\n')
        self.assertEqual(output[-1], 'Exception: hello\n')


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


class TestStartServer(unittest.TestCase):

    def setUp(self):
        setup.placelessSetUp()
        self.options = Options()
        self.options.listen_on = ('127.0.0.1', 8070)  # Don't want IPv6
        self.options.verbose = False
        self.db = None

    def tearDown(self):
        close_database()
        setup.placelessTearDown()

    def start_server(self, options, db):
        server = start_server(self.options, self.db)
        self.addCleanup(server.close)
        self.addCleanup(server.task_dispatcher.shutdown)
        return server

    @mock.patch('socket.socket')
    def test_prints_clickable_url(self, mock_socket):
        mock_socket.return_value.getsockopt.return_value = 0
        mock_socket.return_value.getsockname.return_value = ('127.0.0.1', 8070)
        self.options.verbose = True
        with self.assertLogs('waitress', level='INFO') as cm:
            self.start_server(self.options, self.db)
        self.assertEqual(
            cm.output, ['INFO:waitress:Listening on http://127.0.0.1:8070/']
        )

    @mock.patch(
        'waitress.server.create_server',
        mock.Mock(side_effect=socket.error(errno.EADDRINUSE, "port busy")),
    )
    def test_socket_error_handling_eaddrinuse(self):
        self.options.listen_on = ('localhost', 80)
        with self.assertRaises(SystemExit) as e:
            start_server(self.options, self.db)
        self.assertTrue(
            str(e.exception).startswith("Cannot listen on localhost:80"),
            str(e.exception))

    @mock.patch(
        'waitress.server.create_server',
        mock.Mock(side_effect=socket.error(errno.EINVAL, "bad port")),
    )
    def test_socket_error_handling_other_kind_of_error(self):
        self.options.listen_on = ('localhost', -1)
        with self.assertRaises(socket.error):
            start_server(self.options, self.db)


class TestServeForever(unittest.TestCase):

    def test(self):
        server = mock.Mock(run=mock.Mock(side_effect=KeyboardInterrupt))
        serve_forever(server)
        server.close.assert_called_once()


@mock.patch('zodbbrowser.standalone.open_db', mock.Mock())
@mock.patch('zodbbrowser.standalone.configure', mock.Mock())
@mock.patch('zodbbrowser.standalone.start_server', mock.Mock())
@mock.patch('zodbbrowser.standalone.serve_forever', mock.Mock())
class TestMain(RealDatabaseTest):

    open_db = False

    def setUp(self):
        setup.placelessSetUp()
        RealDatabaseTest.setUp(self)

    def tearDown(self):
        RealDatabaseTest.tearDown(self)
        setup.placelessTearDown()

    @mock.patch('logging.basicConfig')
    def test(self, mock_basicConfig):
        main(['--quiet', '--listen', '0', '--rw', self.db_filename])
        mock_basicConfig.assert_called_with(
            format="%(message)s", level=logging.INFO
        )

    @mock.patch('logging.basicConfig')
    def test_doubly_verbose(self, mock_basicConfig):
        main(['--quiet', '--listen', '0', '-vv', '--rw', self.db_filename])
        mock_basicConfig.assert_called_with(
            format="%(name)s: %(message)s", level=logging.INFO
        )

    @mock.patch('logging.basicConfig')
    def test_debug_logging(self, mock_basicConfig):
        main(['--quiet', '--listen', '0', '--debug', '--rw', self.db_filename])
        self.assertEqual(logging.getLogger('zodbbrowser').level, logging.DEBUG)
