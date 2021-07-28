from typing import List, Tuple

from django.conf import settings
from django.core.management import CommandError
from django.core.serializers.python import Deserializer
from django.core.management.color import no_style
from django.db import (
    connections,
    DatabaseError,
    DEFAULT_DB_ALIAS,
    IntegrityError,
    router,
    transaction,
)

from gestore.gestore_command import GestoreCommand
from gestore.typing import PK
from gestore.utils import (
    write_packages_diff,
    get_pip_packages,
    get_str_from_model,
    has_conflict
)


class Command(GestoreCommand):
    """
    Imports objects from an export file.
    """
    def __init__(self, *args, **kwargs):
        self.export_object_count = 0
        self.loaded_object_count = 0
        self.to_save_objects = []
        self.using = DEFAULT_DB_ALIAS
        self.ignore = False
        self.override = False

        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser) -> None:
        # Add common args
        super(Command, self).add_arguments(parser)

        parser.add_argument(
            'path',
            help='The path of the exports file',
            type=str,
        )
        parser.add_argument(
            '-o', '--override',
            action='store_true',
            default=False,
            help='Override conflicts in DB. This is very dangerous, please '
                 'use with care'
        )
        parser.add_argument(
            '--database', default=DEFAULT_DB_ALIAS,
            help='Nominates a specific database to load export data into. '
                 'Defaults to the "default" database',
        )
        parser.add_argument(
            '--ignorenonexistent', '-i',
            action='store_true',
            dest='ignore',
            help='Ignores entries in the serialized data for fields that do '
                 'not currently exist on the model',
        )

    def handle(self, *args, **options) -> None:
        """
        Verifies the input and extracts all objects.
        """
        self.debug = options['debug']
        self.ignore = options['ignore']
        self.using = options['database']
        self.override = options['override']
        self.use_bucket = options['bucket']

        path = options['path']

        if not settings.DEBUG and self.override:
            self.raise_error(
                'You cannot use --override in a production environment.\n'
                'If you are facing any issues importing your objects, please '
                'fix them manually or consult your team for support.'
            )

        super(Command, self).check()
        exports = self.load_exports_file(path)
        self.check(exports=exports, display_num_errors=True)

        self.write('Processing exported objects...')

        # If load_data is successfully completed, the changes are committed to
        # the database. If there is an exception, the changes are rolled back.
        with transaction.atomic(using=self.using):
            self.load_data(exports['objects'])

        # Close the DB connection -- unless we're still in a transaction. This
        # is required as a workaround for an edge case in MySQL: if the same
        # connection is used to create tables, load data, and query, the query
        # can return incorrect results. See Django #7572, MySQL #37735.
        if transaction.get_autocommit(self.using):
            connections[self.using].close()

        self.write_success(
            'Successfully imported "%s" objects.' % self.loaded_object_count
        )

    def check(self, *args, **kwargs):
        """
        Inspects project for potential problems.

        The functions check different areas in the project. These areas
        the most probably to cause a problem in case they changed.

            * Checks Django project for any problem.
            * Checks the format of the provided file.
            * Checks the version of the imported file. Unmatched versions might
              cause problems during the import process.
            * Checks the pip packages. Some pip packages contain models that
              were exported.

        If these don't check out, we might need to manually fix the problem.
        """
        self.write('Inspecting project for potential problems...')
        exports = kwargs.pop('exports', {})

        self.check_migrations()

        if not exports:
            return

        if not exports.get('provided_objects'):
            self.raise_error('Malformed exports file.')

        if 'version' not in exports:
            self.raise_error(
                'Version is missing. '
                'Please check the input file for missing data.'
            )

        if exports['version'] != str(self.get_version()):
            self.write_warning(
                'Version mismatch between exported input and the importer.'
            )

            self.write_info(
                'Objects will be created as long as no errors '
                'happen on the way.'
            )

        local_packages = get_pip_packages()
        if 'libraries' not in exports:
            self.raise_error(
                '`libraries` is missing. '
                'Please check the input file for missing data.'
            )
        exported_packages = exports['libraries']

        # exported_packages and local_packages are dictionaries
        if exported_packages != local_packages:
            self.write_warning(
                'Pip packages mismatch between exported input '
                'and the importer.'
            )
            self.write_info(
                'Objects will be created as long as no errors '
                'happen on the way.'
            )
            write_packages_diff(
                local_packages,
                exported_packages,
                writer=self.write
            )

    def load_data(self, objects_data: dict) -> None:
        """
        Searches for and loads the contents of the objects_data into the
        database.
        Each time we run load_data, the data will be read from objects_data
        and re-loaded into the database.

        Note: this means that if we change one of the rows created in the
        database and then run load_data again, we’ll wipe out any changes
        we’ve made.
        """
        models = set()
        connection = connections[self.using]

        with connection.constraint_checks_disabled():
            self.load_objects(objects_data)

        # Since we disabled constraint checks, we must manually check for
        # any invalid keys that might have been added
        table_names = [model._meta.db_table for model in models]

        try:
            connection.check_constraints(table_names=table_names)
        except Exception as e:
            e.args = ('Problem loading object: %s' % e,)
            raise

        # If we found even one object in a export, we need to reset the
        # database sequences.
        if self.loaded_object_count > 0:
            sequence_sql = connection.ops.sequence_reset_sql(
                no_style(), models
            )
            if sequence_sql:
                self.stdout.write('Resetting sequences\n')
                with connection.cursor() as cursor:
                    for line in sequence_sql:
                        cursor.execute(line)

        self.print_to_save_objects()

        if self.export_object_count == self.loaded_object_count:
            self.write('Installed %d object(s)' % self.loaded_object_count)
        else:
            self.write(
                'Installed %d object(s) (of %d)'
                % (self.loaded_object_count, self.export_object_count)
            )

    def load_objects(self, objects_data: dict) -> None:
        """
        Iterates over the objects_data, deserializes them, and put them
        in the database one by one.
        """
        self.stdout.write('Processing objects in progress...')

        models = set()
        conflicts = []

        objects = Deserializer(
            objects_data,
            using=self.using,
            ignorenonexistent=self.ignore
        )

        try:
            for obj in objects:
                self.export_object_count += 1
                Model = obj.object.__class__
                if router.allow_migrate_model(self.using, Model):
                    self.loaded_object_count += 1
                    models.add(Model)

                    object_id = obj.object.pk
                    if has_conflict(Model, object_id):
                        mpath = get_str_from_model(Model)
                        conflicts.append((object_id, mpath))

                    try:
                        if self.debug:
                            self.to_save_objects.append(
                                get_str_from_model(Model, object_id=object_id)
                            )
                        else:
                            obj.save(using=self.using)
                        self.write(
                            '\rProcessed %i '
                            'object(s)' % self.loaded_object_count,
                            ending=''
                        )
                    except AttributeError:
                        continue
                    except (DatabaseError, IntegrityError) as e:
                        e.args = (
                            'Could not load '
                            '%(app_label)s.%(object_name)s(pk=%(pk)s): '
                            '%(error_msg)s' % {
                                'app_label': obj.object._meta.app_label,
                                'object_name': obj.object._meta.object_name,
                                'pk': obj.object.pk,
                                'error_msg': e,
                            },
                        )
                        raise

            if objects:
                # Add a newline after progress indicator.
                self.stdout.write('')
        except Exception as e:
            if not isinstance(e, CommandError):
                e.args = ('Problem loading object %s' % e,)
            raise

        if conflicts:
            self.print_conflicts(conflicts)

            # When raising the error, no objects will be stored because
            # of the atomic transaction
            if not self.override:
                self.raise_for_conflicts()

        # Warn if the the export file we loaded contains 0 objects.
        if self.export_object_count == 0:
            self.write_warning('No data found for provided export file')

    def print_conflicts(self, conflicts: List[Tuple[PK, str]]) -> None:
        conflicts_message = ''.join([
            '\t- Object ID {} in model {}\n'.format(c, m)
            for c, m in conflicts
        ])

        self.write_error(
            '\nConflict detected in the following '
            'objects:\n %s' % conflicts_message
        )

    def raise_for_conflicts(self) -> None:
        self.write_warning('PLEASE READ:')
        self.write_warning(
            'Conflict detected between database and export data...'
        )
        self.write(
            'This error was raised to prevent overriding the object in your '
            'database.\n'
            'Solving this issue is typically \033[1mmanual\033[0m, here is '
            'some suggestions, but feel free to be creative.\n'
            '\t* Make sure you are importing objects in a clean environment.\n'
            '\t* Change the ID of the object in the imported file if the '
            'object in the database is completly different than the one being '
            'imported.\n'
            '\t* Remove the object from the database if it is outdated.\n'
            '\t* Use \033[1m--override\033[0m option if you are confident the '
            'imported data will not raise any issues in the future '
            '\033[3m(Could be dangerous)\033[0m.\n'
            '\t* Consult your Team for support.\n'
        )

        self.raise_error(
            'Data conflict detected between objects in the database and the '
            'imported file'
        )

    def print_to_save_objects(self) -> None:
        if not self.debug:
            return

        for obj in self.to_save_objects:
            self.write(obj)
