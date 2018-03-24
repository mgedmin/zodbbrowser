import os
import shutil
import socket
import tempfile
import unittest

import mock
from zope.app.testing import setup

from zodbbrowser.standalone import parse_args, serve_forever, main
from zodbbrowser.tests.realdb import RealDatabaseTest


class TestParseArgs(unittest.TestCase):

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

    def make_socket(self):
        tempdir = tempfile.mkdtemp(prefix='test-zodbbrowser-')
        self.addCleanup(shutil.rmtree, tempdir)
        sockfilename = os.path.join(tempdir, 'zeosock')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        sock.bind(sockfilename)
        sock.listen(0)
        return sockfilename

    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'),
                         "No UNIX domain sockets on this platform")
    def test_zeo_socket(self):
        sockfilename = self.make_socket()
        options = parse_args(['--zeo', sockfilename])
        self.assertEqual(options.zeo_address, sockfilename)

    def test_bad_zeo_socket(self):
        with self.assertRaises(SystemExit), mock.patch('sys.stderr'):
            parse_args(['--zeo', __file__])


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
    @mock.patch('zodbbrowser.standalone.serve_forever', mock.Mock())
    def test(self):
        main(['--quiet', '--listen', '0', '--rw', self.db_filename])
