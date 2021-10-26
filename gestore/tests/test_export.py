from collections import Counter
from io import StringIO
from unittest.mock import patch

import django
from django.core.management import CommandError, call_command
from django.test import TestCase

from demoapp.factories.demoapp import BookInstanceFactory
from gestore.management.commands.exportobjects import Command


class TestExportObjectsCommand(TestCase):
    def setUp(self):
        self.out = StringIO()
        self.command = Command(stdout=self.out)

        self.books_instances = [
            BookInstanceFactory.create() for _ in range(100)
        ]

    @patch('gestore.management.commands.exportobjects.get_pip_packages')
    @patch('gestore.management.commands.exportobjects.get_obj_from_str')
    @patch.object(Command, 'write_exports_file')
    @patch.object(Command, 'check')
    def test_handle(
            self,
            mock_check,
            mock_write_exports_file,
            get_obj_from_str,
            mock_get_pip_packages
    ):
        get_obj_from_str.return_value = self.books_instances[0]
        mock_write_exports_file.return_value = 'called'
        mock_get_pip_packages.return_value = {}

        objs = ['demoapp.book.1', 'demoapp.book.2', ]
        call_command('exportobjects', objs, stdout=self.out)

        self.assertTrue(mock_check.called)
        self.assertTrue(get_obj_from_str.called)
        self.assertTrue(mock_write_exports_file.called)
        self.assertTrue(mock_get_pip_packages.called)

        if django.VERSION < (3, 2, 0):
            self.assertIn(
                'Exporting ["%s"] in progress...' % objs, self.out.getvalue()
            )
        else:
            self.assertIn(
                'Exporting %s in progress...' % objs, self.out.getvalue()
            )
        self.assertIn('Objects successfully exported!', self.out.getvalue())
        self.assertNotIn('Command output >>>', self.out.getvalue())

    @patch('gestore.management.commands.exportobjects.get_pip_packages')
    @patch('gestore.management.commands.exportobjects.get_obj_from_str')
    @patch.object(Command, 'check')
    def test_handle_debug(
            self,
            mock_check,
            get_obj_from_str,
            mock_get_pip_packages
    ):
        get_obj_from_str.return_value = self.books_instances[0]
        mock_get_pip_packages.return_value = {}

        objs = ['demoapp.book.1', 'demoapp.book.2', ]
        call_command('exportobjects', objs, debug=True, stdout=self.out)

        self.assertTrue(mock_check.called)
        self.assertTrue(get_obj_from_str.called)
        self.assertTrue(mock_get_pip_packages.called)

        if django.VERSION < (3, 2, 0):
            self.assertIn(
                'Exporting ["%s"] in progress...' % objs, self.out.getvalue()
            )
        else:
            self.assertIn(
                'Exporting %s in progress...' % objs, self.out.getvalue()
            )
        self.assertIn('Objects successfully exported!', self.out.getvalue())
        self.assertIn('Command output >>>', self.out.getvalue())

    def test_handle_system_check_fails(self):
        """
        According to Django, serious problems are raised as a CommandError
        when calling `check` function. Processing should stop in case we got
        a serious problem.

        https://docs.djangoproject.com/en/3.2/howto/custom-management-commands/#django.core.management.BaseCommand.check
        """

        objs = ['demoapp.book.1', 'demoapp.book.2', ]
        with patch(
                'gestore.management.commands.exportobjects.Command.check',
                side_effect=CommandError()
        ):
            with self.assertRaises(CommandError):
                call_command(
                    'exportobjects',
                    objs,
                    debug=True,
                    stdout=self.out
                )

            with self.assertRaises(CommandError):
                call_command('exportobjects', objs, stdout=self.out)

    @patch('gestore.management.commands.exportobjects.get_model_name')
    @patch('gestore.management.commands.exportobjects.instance_representation')
    @patch.object(Command, 'process_instance')
    def test_generate_objects_dfs(
            self, mock_process_instance, mock_instance_rep, mock_get_model_name
    ):
        """
        To be able to test DFS we need a graph structure, this mimics database
        relations to some extent.
        """
        mock_instance_rep.side_effect = lambda x: x
        mock_get_model_name.side_effect = lambda x: x.split('_')[0]
        mock_process_instance.side_effect = self.fake_process_instance

        objects = self.command.generate_objects('Microsite_1')

        # The objects must be processed in the following order
        self.assertEqual(Counter(objects), Counter([
            'Microsite_1',
            'Organization_1',
            'Tier_1',
            'User_2',
            'AuthToken_2',
            'User_1',
            'UserTermsConditions_2',
            'Terms_2',
            'UserTermsConditions_1',
            'Terms_1',
            'AuthToken_1',
            'Organization_2',
        ]
        ))

    @patch('gestore.management.commands.exportobjects.get_model_name')
    @patch('gestore.management.commands.exportobjects.instance_representation')
    @patch.object(Command, 'process_instance')
    def test_generate_objects_integrity(
            self, mock_process_instance, mock_instance_rep, mock_get_model_name
    ):
        """
        makes sure that:
            - All required objects are processed.
            - Unrelated objects are not included.
            - No object appears more than once.
        """
        mock_instance_rep.side_effect = lambda x: x
        mock_get_model_name.side_effect = lambda x: x.split('_')[0]
        mock_process_instance.side_effect = self.fake_process_instance

        objects = self.command.generate_objects('Microsite_1')

        # Test duplicates
        self.assertEqual(len(objects), len(set(objects)))

        # Test exact items
        self.assertEqual(set(objects), {
            'Microsite_1',
            'Organization_1',
            'Tier_1',
            'User_2',
            'AuthToken_2',
            'User_1',
            'UserTermsConditions_2',
            'Terms_2',
            'UserTermsConditions_1',
            'Terms_1',
            'AuthToken_1',
            'Organization_2',
        })

    @staticmethod
    def fake_process_instance(instance):
        """
        Returns all this nodes relations; the ones that it points at, and the
        ones they point at it.

    Microsite_2                   Microsite_1
       ||                             ||
       v                              v
  Organization_2 <------        Organization_1 <-- Tier_1
                       \\---\\    //      \\
                            \\   //       \\
                            \\   v         v
            AuthToken_1 --> User_1    User_2 <-- AuthToken_2
                             ^ ^
                            // \\
                           //   \\
         UserTermsConditions_1  UserTermsConditions_2
                          ||          ||
                          v           v
                        Terms_1     Terms_2

                           --> ObjectNotUsed_1
                          //
        ShouldNotAppear_1
                          \\
                           --> ObjectNotUsed_2

        ShouldNotAppear_2 --> ObjectNotUsed_3
        """
        graph = {
            'Microsite_1': [
                'Organization_1',
            ],
            'Organization_1': [
                'User_1',
                'User_2',
            ],
            'Microsite_2': [
                'Organization_2',
            ],
            'Tier_1': [
                'Organization_1',
            ],
            'User_1': [
                'Organization_2'
            ],
            'User_2': [],
            'AuthToken_1': [
                'User_1',
            ],
            'AuthToken_2': [
                'User_2',
            ],
            'UserTermsConditions_1': [
                'User_1',
                'Terms_1',
            ],
            'UserTermsConditions_2': [
                'User_1',
                'Terms_2',
            ],
            'ShouldNotAppear_1': [
                'ObjectNotUsed_1',
                'ObjectNotUsed_2',
            ],
            'ShouldNotAppear_2': [
                'objectNotUsed_3',
            ],
        }

        objects = graph.get(instance, [])
        for key, value in graph.items():
            if instance in value:
                objects.append(key)

        return instance, objects
