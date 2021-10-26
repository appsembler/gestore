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

    @patch('gestore.management.commands.exportobjects.instance_representation')
    @patch.object(Command, 'process_instance')
    def test_generate_objects_dfs(self, mock_process_instance, mock_instance_rep):
        """
        To be able to test DFS we need a graph structure, this mimics database
        relations to some extent.
        """
        mock_instance_rep.side_effect = lambda x: x
        mock_process_instance.side_effect = self.fake_process_instance
        objects = self.command.generate_objects('microsite')

        # The objects must be processed in the following order
        self.assertListEqual(
            objects,
            [
                'microsite',
                'organization_1',
                'tier',
                'user_2',
                'auth_token_2',
                'user_1',
                'user_terms_conditions_2',
                'terms_2',
                'user_terms_conditions_1',
                'terms_1',
                'auth_token_1'
            ]
        )

    @patch('gestore.management.commands.exportobjects.instance_representation')
    @patch.object(Command, 'process_instance')
    def test_generate_objects_integrity(self, mock_process_instance, mock_instance_rep):
        """
        makes sure that:
            - All required objects are processed.
            - Unrelated objects are not included.
            - No object appears more than once.
        """
        mock_instance_rep.side_effect = lambda x: x
        mock_process_instance.side_effect = self.fake_process_instance

        objects = self.command.generate_objects('microsite')

        # Test duplicates
        self.assertEqual(len(objects), len(set(objects)))

        # Test exact items
        self.assertEqual(set(objects), {
            'microsite',
            'organization_1',
            'user_1',
            'user_2',
            'tier',
            'user_terms_conditions_1',
            'auth_token_1',
            'user_terms_conditions_2',
            'auth_token_2',
            'terms_1',
            'terms_2'
        })

    @staticmethod
    def fake_process_instance(instance):
        """
        Returns all this nodes relations; the ones that it points at, and the
        ones they point at it.

                               microsite
                                  |
                                  v
                            organization_1 <-- tier
                                /     \
                               /       \
                              v         v
           auth_token_1 --> user_1    user_2 <-- auth_token_2
                             ^ ^
                            /   \
                           /     \
        user_terms_conditions_1  user_terms_conditions_2
                          |           |
                          v           v
                        terms_1     terms_2

                           --> object_not_used_1
                          /
        should_not_appear_1
                          \
                           --> object_not_used_2

        should_not_appear_2 --> object_not_used_3
        """
        graph = {
            'microsite': [
                'organization_1',
            ],
            'organization_1': [
                'user_1',
                'user_2',
            ],
            'tier': [
                'organization_1',
            ],
            'user_1': [],
            'user_2': [],
            'auth_token_1': [
                'user_1',
            ],
            'auth_token_2': [
                'user_2',
            ],
            'user_terms_conditions_1': [
                'user_1',
                'terms_1',
            ],
            'user_terms_conditions_2': [
                'user_1',
                'terms_2',
            ],
            'should_not_appear_1': [
                'object_not_used_1',
                'object_not_used_2',
            ],
            'should_not_appear_2': [
                'object_not_used_3',
            ],
        }

        objects = graph.get(instance, [])
        for key, value in graph.items():
            if instance in value:
                objects.append(key)

        return instance, objects
