from io import BytesIO as StringIO
from mock import patch
import pkg_resources

from django.contrib.auth.models import User
from django.test import TestCase

from demoapp.factories.django import UserFactory
from gestore import utils


class TestUtils(TestCase):
    def test_get_pip_packages(self):
        packages = utils.get_pip_packages()
        self.assertIsInstance(packages, dict)

        # Get packages should match all the libraries fetched
        # from pkg_resources
        for package in pkg_resources.working_set:
            self.assertEqual(
                packages.pop(package.project_name),
                package.version
            )

        # No more packages should be left after the popping thing above
        self.assertEqual(len(packages), 0)

    def test_has_conflict(self):
        user = UserFactory()
        self.assertTrue(utils.has_conflict(User, user.id))
        self.assertFalse(utils.has_conflict(User, 99999))

    def test_get_obj_from_str(self):
        user = UserFactory()

        # Make sure we get the right object
        representation = 'auth.User.%s' % user.id
        fetched_object = utils.get_obj_from_str(representation)
        self.assertEqual(user, fetched_object)

        # Test object in DB
        representation = 'auth.User.99999999999'
        with self.assertRaises(User.DoesNotExist):
            utils.get_obj_from_str(representation)

        # Test wrong representation
        representation = 'auth.User'
        with self.assertRaisesMessage(
                ValueError, 'need more than 2 values to unpack'
        ):
            utils.get_obj_from_str(representation)

        representation = 'auth.something.User.someid'
        with self.assertRaisesMessage(
                ValueError, 'too many values to unpack'
        ):
            utils.get_obj_from_str(representation)


class TestGetStrFromModel(TestCase):
    def setUp(self):
        self.obj = UserFactory()

    def test_no_object_id(self):
        path = utils.get_str_from_model(User)
        self.assertEqual(path, 'auth.User')

    def test_with_object_id(self):
        path = utils.get_str_from_model(User, object_id=123)
        self.assertEqual(path, 'auth.User.123')


class TestUtilsWritePackagesDiff(TestCase):
    def setUp(self):
        self.local = {
            'a': '1.2.3',
            'b': '2.3.4',
            'c': '3.4.5',
        }

    @patch('sys.stdout', new_callable=StringIO)
    def test_packages_equal(self, mock_print):
        # Test local packages equals exported packages
        utils.write_packages_diff(self.local, self.local)
        self.assertFalse(mock_print.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_packages_not_in_local(self, mock_print):
        # Test package not in local packages but exists in exported packages
        exported = {
            'a': '1.2.3',
            'b': '2.3.4',
            'c': '3.4.5',
            'd': '4.5.6',
        }
        utils.write_packages_diff(self.local, exported)
        self.assertEqual(
            mock_print.getvalue(),
            'd==4.5.6 not found in your local env\n'
        )

    @patch('sys.stdout', new_callable=StringIO)
    def test_packages_not_in_exported(self, mock_print):
        # Test package exists in local packages but not in exported packages
        exported = {
            'b': '2.3.4',
            'c': '3.4.5',
        }
        utils.write_packages_diff(self.local, exported)
        self.assertEqual(
            mock_print.getvalue(),
            'a==1.2.3 not found in your exported env\n'
        )

    @patch('sys.stdout', new_callable=StringIO)
    def test_packages_mismatch(self, mock_print):
        # Test package exists in local packages but not in exported packages
        exported = {
            'a': '1.2.3',
            'b': '2.3.4',
            'c': '5.6.7',
        }
        utils.write_packages_diff(self.local, exported)
        self.assertEqual(
            mock_print.getvalue(),
            'c local version is 3.4.5 and exported version is 5.6.7\n'
        )

    @patch('sys.stdout', new_callable=StringIO)
    def test_packages_mess(self, mock_print):
        # Test package exists in local packages but not in exported packages
        exported = {
            'a': '1.2.3',
            'b': '3.3.4',
            'd': '5.6.7',
        }
        utils.write_packages_diff(self.local, exported)

        self.assertCountEqual(
            mock_print.getvalue(),
            'd==5.6.7 not found in your local env\n'
            'c==3.4.5 not found in your exported env\n'
            'b local version is 2.3.4 and exported version is 3.3.4\n'
        )
