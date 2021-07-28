from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from gestore.gestore_command import GestoreCommand

from gestore.management.commands.importobjects import Command


class TestImportObjectsCommand(TestCase):
    def setUp(self):
        self.out = StringIO()
        self.command = Command(stdout=self.out)

        self.exports = {'objects': []}

    @override_settings(DEBUG=False)
    def test_override_flag_not_debug(self):
        # Command should fail in case override is requested in a non debug env.
        message = 'You cannot use --override in a production environment.'
        with self.assertRaisesMessage(CommandError, message):
            call_command(
                'importobjects', '/dummy/path.json',
                override=True, stdout=self.out
            )

    @patch.object(Command, 'load_exports_file')
    @patch.object(Command, 'check')
    def test_check(self, mock_check, mock_load_exports_file):
        mock_load_exports_file.return_value = self.exports

        # Should not fail, even if objects and libraries are empty
        call_command('importobjects', '/dummy/path.json', stdout=self.out)

        # Check if check called
        self.assertTrue(mock_check.called)

        # Check check called with the output of load_exports_file
        self.assertTrue(mock_check.called_with(self.exports))

    @patch('django.db.backends.sqlite3.base.DatabaseWrapper.check_constraints')
    @patch('django.db.backends.base.base.BaseDatabaseWrapper'
           '.constraint_checks_disabled')
    @patch.object(Command, 'load_objects', return_value=None)
    def test_load_data(
            self,
            mock_load_objects,
            mock_constraint_checks_disabled,
            mock_check_constraints
    ):
        self.command.load_data({})
        self.assertTrue(mock_constraint_checks_disabled.called)

        # Since we disabled constraint checks, we must manually check for
        # any invalid keys that might have been added
        self.assertTrue(mock_check_constraints.called)

        # If constraints fail, load_data should fail
        with self.assertRaises(Exception):
            mock_check_constraints.side_effect = Exception('mocked error')
            self.command.load_data({})

    @patch.object(Command, 'load_exports_file', return_value={'objects': []})
    @patch.object(GestoreCommand, 'check', return_value=None)
    @patch.object(Command, 'check', return_value=None)
    @patch.object(Command, 'load_data', return_value=None)
    def test_handle(
            self,
            mock_load_data,
            mock_check,
            mock_gestore_check,
            mock_load_exports_file
    ):
        with patch('django.db.transaction.atomic') as m:
            call_command('importobjects', '/dummy/path.json', stdout=self.out)
            self.assertTrue(m.called)

        mock_gestore_check.assert_called_once_with()

    @patch('django.db.utils.ConnectionRouter.allow_migrate_model')
    def test_load_objects(self, mock_allow_migrate_model):
        objects = MagicMock()
        with patch('gestore.management.commands.importobjects.Deserializer'):
            self.command.export_object_count = 0
            self.command.loaded_object_count = 0
            self.command.load_objects(objects)

        self.assertEqual(self.command.export_object_count, len(objects))


class TestImportObjectsCheck(TestCase):
    def setUp(self) -> None:
        self.out = StringIO()

    @patch('gestore.management.commands.importobjects.get_pip_packages')
    @patch.object(Command, 'load_exports_file')
    def test_check_pip(self, mock_load_exports_file, mock_get_pip_packages):
        mock_get_pip_packages.return_value = {}
        mock_load_exports_file.return_value = {
            'objects': [],
            'provided_objects': ['a.b.1'],
            'version': '1.2.3',
            'libraries': {}
        }

        # Should not fail, even if objects and libraries are empty
        call_command('importobjects', '/dummy/path.json', stdout=self.out)

        # Check get_pip_packages called with the output of load_exports_file
        self.assertTrue(mock_get_pip_packages.called)

    @patch.object(Command, 'load_exports_file', return_value={'objects': []})
    def test_check_not_provided_objects(self, mock_load_exports_file):
        expected_message = 'Malformed exports file.'
        with self.assertRaisesMessage(CommandError, expected_message):
            call_command('importobjects', '/dummy/path.json', stdout=self.out)

    @patch.object(Command, 'load_exports_file', return_value={
        'objects': [],
        'provided_objects': ['a.b.1', 'c.d.1'],
    })
    def test_check_not_version(self, mock_load_exports_file):
        expected_message = 'Version is missing. ' \
                           'Please check the input file for missing data.'
        with self.assertRaisesMessage(CommandError, expected_message):
            call_command('importobjects', '/dummy/path.json', stdout=self.out)

    @patch.object(Command, 'load_exports_file', return_value={
        'version': '2.3.4',
        'objects': [],
        'provided_objects': ['a.b.1', 'c.d.1'],
        'libraries': {},
    })
    def test_check_wrong_version(self, mock_load_exports_file):
        warning_message = 'Version mismatch between ' \
                           'exported input and the importer.'
        info_message = 'Objects will be created as long ' \
                       'as no errors happen on the way.'

        call_command('importobjects', '/dummy/path.json', stdout=self.out)
        self.assertIn(info_message, self.out.getvalue())
        self.assertIn(warning_message, self.out.getvalue())

    @patch.object(Command, 'load_exports_file', return_value={
        'version': '2.3.4',
        'objects': [],
        'provided_objects': ['a.b.1', 'c.d.1'],
    })
    def test_check_missing_libraries(self, mock_load_exports_file):
        expected_message = '`libraries` is missing. ' \
                           'Please check the input file for missing data.'

        with self.assertRaisesMessage(CommandError, expected_message):
            call_command('importobjects', '/dummy/path.json', stdout=self.out)

    @patch('gestore.management.commands.importobjects.write_packages_diff')
    @patch('gestore.management.commands.importobjects.get_pip_packages')
    @patch.object(Command, 'load_exports_file', return_value={
        'version': '2.3.4',
        'objects': [],
        'provided_objects': ['a.b.1', 'c.d.1'],
        'libraries': {
            'a': '1.2.3',
            'b': '2.3.4',
            'c': '3.4.5',
        },
    })
    def test_check_libraries_mismatch(
            self,
            mock_load_exports_file,
            mock_get_pip_packages,
            mock_write_packages_diff,
    ):
        mock_get_pip_packages.return_value = {
            'a': '1.2.3',
        }
        warning_message = 'Pip packages mismatch between ' \
                          'exported input and the importer.'
        info_message = 'Objects will be created as long as ' \
                       'no errors happen on the way.'

        call_command('importobjects', '/dummy/path.json', stdout=self.out)
        self.assertIn(warning_message, self.out.getvalue())
        self.assertIn(info_message, self.out.getvalue())

        self.assertTrue(mock_write_packages_diff.called)
