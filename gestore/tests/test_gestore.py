import json
from io import BytesIO as StringIO
from socket import gaierror
from mock import Mock, mock_open, patch

from django.conf import settings
from django.core.management import CommandError
from django.test import TestCase, override_settings

from gestore.gestore_command import GestoreCommand


class TestGestoreCommand(TestCase):
    def setUp(self):
        self.command = GestoreCommand()

    def test_write_to_console(self):
        content = 'MyTest content somethigng'
        out = StringIO()

        self.command.stdout = out
        self.command.write_to_console(content)

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


class TestGestoreCommandBucketGeneral(TestCase):
    def setUp(self):
        self.command = GestoreCommand(stdout=StringIO())
        self.improperly_configured_text = \
            'Storage is improperly configured. Make sure that the ' \
            'following settings exist and properly defined before ' \
            'attempting again\n' \
            '\t* GESTORE_CREDENTIALS\n' \
            '\t* GESTORE_BUCKET_NAME\n' \
            '\t* GESTORE_PROJECT_NAME\n'

    @override_settings(GESTORE_CREDENTIALS='test')
    @override_settings(GESTORE_BUCKET_NAME='test')
    @override_settings(GESTORE_PROJECT_NAME='test')
    def test_correct_check_bucket_config(self):
        # Will raise an exception if something's wrong
        self.command.check_bucket_config()

    @override_settings(GESTORE_CREDENTIALS=None)
    @override_settings(GESTORE_BUCKET_NAME='test')
    @override_settings(GESTORE_PROJECT_NAME='test')
    def test_check_bucket_config_no_credentials(self):
        with self.assertRaisesMessage(
                CommandError,
                self.improperly_configured_text
        ):
            self.command.check_bucket_config()

    @override_settings(GESTORE_CREDENTIALS='test')
    @override_settings(GESTORE_BUCKET_NAME=None)
    @override_settings(GESTORE_PROJECT_NAME='test')
    def test_check_bucket_config_no_bucket_name(self):
        with self.assertRaisesMessage(
                CommandError,
                self.improperly_configured_text
        ):
            self.command.check_bucket_config()

    @override_settings(GESTORE_CREDENTIALS='test')
    @override_settings(GESTORE_BUCKET_NAME='test')
    @override_settings(GESTORE_PROJECT_NAME=None)
    def test_check_bucket_config_no_project_name(self):
        with self.assertRaisesMessage(
                CommandError,
                self.improperly_configured_text
        ):
            self.command.check_bucket_config()

    def test_shell_run(self):
        command = 'pwd'
        self.command._shell_run(command)
        self.assertIn('/gestore', self.command.stdout.getvalue())

    @patch('subprocess.Popen')
    def test_shell_run_errors(self, mock_popen):
        command = 'pwd'

        exception_message = 'Intentional Error'
        expected_message = 'Something wrong performing ' \
                           '`%s`:\n%s' % (command, exception_message)

        mock_popen.side_effect = Exception(exception_message)
        with self.assertRaisesMessage(CommandError, expected_message):
            self.command._shell_run(command)

    @patch('subprocess.Popen')
    def test_shell_run_returncode_not_zero(self, mock_popen):
        command = 'pwd'
        exception_message = 'Intentional Error'
        expected_message = 'Something wrong performing ' \
                           '`%s`:\n%s' % (command, exception_message)

        # Just configuring the mock
        process_mock = Mock()
        process_mock.configure_mock(**{
            'returncode': 1,
            'communicate.return_value': (
                b'output',
                exception_message.encode('utf-8')
            ),
        })
        mock_popen.return_value = process_mock

        with self.assertRaisesMessage(CommandError, expected_message):
            self.command._shell_run(command)


class TestGestoreCommandBucketExport(TestCase):
    def setUp(self):
        self.command = GestoreCommand(stdout=StringIO())

    @patch.object(GestoreCommand, '_write_to_bucket')
    @patch.object(GestoreCommand, '_write_to_file')
    def test_write_exports_file(self, mock_local, mock_bucket):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'

        self.command.use_bucket = False
        self.command.write_exports_file(path, content)
        mock_local.assert_called_once_with(path, content)
        mock_bucket.assert_not_called()

        mock_local.reset_mock()
        mock_bucket.reset_mock()

        self.command.use_bucket = True
        self.command.write_exports_file(path, content)
        mock_bucket.assert_called_once_with(path, content)
        mock_local.assert_not_called()

    @patch.object(GestoreCommand, '_shell_run')
    @patch.object(GestoreCommand, 'write_to_console')
    def test_write_to_bucket_debug(self, mock_write_console, mock_shell_run):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'

        self.command.debug = True
        self.command._write_to_bucket(path, content)

        mock_write_console.assert_called_once_with(content)
        mock_shell_run.assert_not_called()

    @patch.object(GestoreCommand, '_write_to_file')
    @patch.object(GestoreCommand, '_shell_run')
    def test_write_to_bucket(self, mock_shell_run, mock_write_to_file):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'

        self.command._write_to_bucket(path, content)
        mock_write_to_file.called_once_with(path, content)
        mock_shell_run.called_once_with("gsutil cp %s gs://%s/%s" % (
            path,
            settings.GESTORE_BUCKET_NAME,
            path
        ))

        self.assertIn(
            'Content saved in %s: %s' % (settings.GESTORE_BUCKET_NAME, path),
            self.command.stdout.getvalue()
        )

    @patch('django.core.files.File.write')
    def test_write_to_file(self, mock_write):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'

        self.command.stdout = StringIO()
        with patch('__builtin__.open', mock_open()) as mock_file:
            self.command._write_to_file(path, content)

        mock_file.assert_called_once_with(path, 'w')
        self.assertTrue(mock_write.called_with(content))

    @patch.object(GestoreCommand, 'write_to_console')
    def test_write_to_file_debug(self, mock_write_to_console):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'

        self.command.debug = True
        self.command._write_to_file(path, content)

        mock_write_to_console.assert_called_once_with(content)
        with patch('__builtin__.open', mock_open()) as mock_file:
            mock_file.assert_not_called()


class TestGestoreCommandBucketDownload(TestCase):
    def setUp(self):
        self.command = GestoreCommand(stdout=StringIO())

    @patch.object(GestoreCommand, '_load_exports_file_from_local')
    @patch.object(GestoreCommand, '_load_exports_file_from_bucket')
    def test_load_exports_file(self, mock_bucket, mock_local):
        path = '/dummy/path.json'

        self.command.use_bucket = False
        self.command.load_exports_file(path)
        mock_local.assert_called_once_with(path)
        mock_bucket.assert_not_called()

        mock_local.reset_mock()
        mock_bucket.reset_mock()

        self.command.use_bucket = True
        self.command.load_exports_file(path)
        mock_bucket.assert_called_once_with(path)
        mock_local.assert_not_called()

    def test_load_exports_file_from_local(self):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'

        # File doesn't exist
        with self.assertRaises(CommandError):
            self.command._load_exports_file_from_local(path)

        with patch('os.path.exists', return_value=True):
            with patch('__builtin__.open', mock_open(read_data=content)):
                data = self.command._load_exports_file_from_local(path)

        self.assertEqual(data, json.loads(content))

    @override_settings(GESTORE_BUCKET_NAME='test')
    @patch.object(GestoreCommand, 'generate_file_path')
    @patch.object(GestoreCommand, '_shell_run')
    @patch.object(GestoreCommand, '_load_exports_file_from_local')
    def test_load_exports_file_bucket(
            self,
            mock_load_exports_file_from_local,
            mock_shell_run,
            mock_generate_file_path,
    ):
        path = '/dummy/path.json'
        content = '{"tetst": "contetnt"}'

        mock_generate_file_path.return_value = path
        mock_load_exports_file_from_local.return_value = json.loads(content)

        exports = self.command._load_exports_file_from_bucket(path)
        mock_generate_file_path.assert_called_once_with(
            self.command.exports_dir
        )
        mock_shell_run.assert_called_once_with('gsutil cp gs://%s/%s %s' % (
            settings.GESTORE_BUCKET_NAME,
            path,
            path
        ))
        self.assertEqual(exports, json.loads(content))

        self.assertIn(
            'Fetching exports file content from bucket: %s...' % (
                settings.GESTORE_BUCKET_NAME
            ),
            self.command.stdout.getvalue()
        )
