from io import StringIO
from socket import gaierror
from unittest.mock import mock_open, patch

from django.core.management import CommandError
from django.test import TestCase

from gestore.gestore_command import GestoreCommand


class TestGestoreCommand(TestCase):
    def setUp(self):
        self.command = GestoreCommand()

    @patch('django.core.files.File.write')
    def test_write_to_file(self, mock_write):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'

        self.command.stdout = StringIO()
        with patch('builtins.open', mock_open()) as mock_file:
            self.command.write_to_file(path, content)

        mock_file.assert_called_once_with(path, 'w')
        self.assertTrue(mock_write.called_with(content))

    @patch('django.core.files.File.write')
    def test_write_to_file_debug(self, mock_write):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'
        out = StringIO()

        self.command.debug = True
        self.command.stdout = out

        self.command.write_to_file(path, content)

        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.assert_not_called()

        self.assertIn('You are running in DEBUG mode', out.getvalue())
        self.assertIn('Output will be printed to console', out.getvalue())
        self.assertIn(content, out.getvalue())

    def test_raise_error(self):
        message = 'test message'
        with self.assertRaisesMessage(CommandError, message):
            self.command.raise_error(message)

    @patch('gestore.gestore_command.socket.gethostbyname')
    def test_get_ip_address_socket(self, mock_gethostbyname):
        hostname = 'test_hostname'
        mock_gethostbyname.return_value = '1.2.3.4'
        ip_address = self.command._get_ip_address(hostname)

        self.assertTrue(mock_gethostbyname.called)
        self.assertTrue(mock_gethostbyname.called_with(hostname))
        self.assertEqual(ip_address, '1.2.3.4')

    @patch('gestore.gestore_command.socket.gethostbyname')
    def test_get_ip_address(self, mock_gethostbyname):
        hostname = 'test_hostname'
        mock_gethostbyname.side_effect = gaierror

        ip_address = self.command._get_ip_address(hostname)

        self.assertTrue(mock_gethostbyname.called)
        self.assertEqual(ip_address, '127.0.0.1')

    def test_generate_file_path_ends_with_json(self):
        path = 'a/b/c.json'
        rpath = self.command.generate_file_path(path)

        self.assertEqual(path, rpath)

    @patch('gestore.gestore_command.os.makedirs')
    @patch('gestore.gestore_command.os.path.exists')
    def test_generate_file_path_not_exists(self, mock_exists, mock_makedirs):
        path = 'a/b/c'
        mock_exists.return_value = False

        rpath = self.command.generate_file_path(path)

        self.assertTrue(mock_exists.called)
        self.assertTrue(mock_makedirs.called)
        self.assertTrue(mock_makedirs.called_with(path))

        self.assertTrue(rpath.endswith('.json'))
        self.assertTrue(rpath.startswith(path))

    @patch('gestore.gestore_command.os.makedirs')
    @patch('gestore.gestore_command.os.path.exists')
    def test_generate_file_path_exists(self, mock_exists, mock_makedirs):
        path = 'a/b/c'
        mock_exists.return_value = True

        rpath = self.command.generate_file_path(path)

        self.assertTrue(mock_exists.called)
        self.assertFalse(mock_makedirs.called)

        self.assertTrue(rpath.endswith('.json'))
        self.assertTrue(rpath.startswith(path))
