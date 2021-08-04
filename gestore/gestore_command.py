import json
import os
import shlex
import socket
import subprocess
import time
from abc import ABC

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from gestore import __version__ as VERSION
from gestore.typing import IP_ADDRESS


class GestoreCommand(BaseCommand, ABC):
    """
    Parent management command for Gestore.
    """

    def __init__(self, *args, **kwargs):
        self.errors = []
        self.debug = False
        self.hostname = socket.gethostname()
        self.ip_address = self._get_ip_address(self.hostname)
        self.exports_dir = 'exports'
        self.use_bucket = False

        super(GestoreCommand, self).__init__(*args, **kwargs)

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '-d', '--debug',
            action='store_true',
            help='Execute in debug mode (Will not commit or save changes)'
        )
        parser.add_argument(
            '-b', '--bucket',
            help="Upload exports file to bucket instead of local machine",
            action='store_true',
        )

    def generate_file_path(self, path: str) -> str:
        """
        Determines and returns the output file name.
        If the user specified a full path, then just return it. If a partial
        path has been specified, we add the file name to it and return. Other
        wise, we combine our base path with the file name and return them.
        """
        if path.endswith('.json'):
            return path

        file_name = '%s_%s.json' % (self.hostname, time.time())

        if not os.path.exists(path):
            os.makedirs(path)

        path = os.path.join(path, file_name)
        return path

    def check_bucket_config(self):
        """
        Makes sure bucket is prpoerly configured in settings.
        """
        # Something is wrong with the bucket configuration.
        if not (
                settings.GESTORE_CREDENTIALS
                and settings.GESTORE_BUCKET_NAME
                and settings.GESTORE_PROJECT_NAME
        ):
            self.raise_error(
                'Storage is improperly configured. Make sure that the '
                'following settings exist and properly defined before '
                'attempting again\n'
                '\t* GESTORE_CREDENTIALS\n'
                '\t* GESTORE_BUCKET_NAME\n'
                '\t* GESTORE_PROJECT_NAME\n'
            )

    def write_to_console(self, content: str) -> None:
        """
        Writing export content to console.
        """
        self.write_warning(
            'You are running in DEBUG mode. '
            'Output will be printed to console'
        )
        self.write('Command output >>>')
        self.write_migrate_label(content)

    def _shell_run(self, command: str):
        args = shlex.split(command)

        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            self.raise_error(
                'Something wrong performing `%s`:\n%s' % (
                    command,
                    e
                )
            )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            self.raise_error(
                'Something wrong performing `%s`:\n%s' % (
                   command,
                   stderr.decode('utf-8')
                )
            )

        self.write(stdout.decode('utf-8'))
        # It looks weird ignoring stderr output, but the fact is gsutil on
        # redirect their output to stderr, so stdout is always empty.
        self.write(stderr.decode('utf-8'))

    def _write_to_bucket(self, path: str, content: str) -> None:
        """
        Writes content in the specified path.
        """
        if self.debug:
            self.write_to_console(content)
            return

        self._write_to_file(path, content)
        self.write(
            'Uploading exports to your '
            'GCP bucket: %s...' % settings.GESTORE_BUCKET_NAME
        )

        self._shell_run("gsutil cp %s gs://%s/%s" % (
            path,
            settings.GESTORE_BUCKET_NAME,
            path
        ))

        self.write_migrate_heading(
            'Content saved in %s: %s' % (settings.GESTORE_BUCKET_NAME, path)
        )

    def _write_to_file(self, path: str, content: str) -> None:
        """
        Writes content in the specified path.
        """
        if self.debug:
            self.write_to_console(content)
            return

        with open(path, 'w') as file:
            file.write(content)

        self.write_migrate_heading('Content saved in %s' % path)

    def _load_exports_file_from_local(self, path: str) -> dict:
        """
        Processes the input path, by fetching the file and returning the JSON
        representation of it.
        """
        self.write('Fetching exports file content...')

        if not os.path.exists(path):
            self.raise_error('Exports file path does not exist: %s' % path)

        with open(path) as f:
            data = json.load(f)

        return data

    def _load_exports_file_from_bucket(self, path: str) -> dict:
        """
        Downloads the export file in a given location from a bucket.
        """
        self.write(
            'Fetching exports file content '
            'from bucket: %s...' % settings.GESTORE_BUCKET_NAME
        )

        download_path = self.generate_file_path(self.exports_dir)
        self._shell_run('gsutil cp gs://%s/%s %s' % (
            settings.GESTORE_BUCKET_NAME,
            path,
            download_path
        ))
        return self._load_exports_file_from_local(download_path)

    def load_exports_file(self, path: str) -> dict:
        """
        Reroute the call to either local fetch or bucket fetch, and returns
        the result back in a dict object.
        """
        return self._load_exports_file_from_bucket(path) \
            if self.use_bucket \
            else self._load_exports_file_from_local(path)

    def write_exports_file(self, path: str, content: str) -> dict:
        """
        Reroute the call to either local write or bucket write.
        """
        self._write_to_bucket(path, content) \
            if self.use_bucket \
            else self._write_to_file(path, content)

    def raise_error(self, message: str) -> None:
        raise CommandError(message)

    def get_version(self):
        return VERSION

    def _get_ip_address(self, hostname: str) -> IP_ADDRESS:
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            pass

        return '127.0.0.1'

    def write(self, message: str, *args, **kwargs) -> None:
        self.stdout.write(message, *args, **kwargs)

    def write_info(self, message: str, *args, **kwargs) -> None:
        self.write(self.style.HTTP_INFO(message), *args, **kwargs)

    def write_success(self, message: str, *args, **kwargs) -> None:
        self.write(self.style.SUCCESS(message), *args, **kwargs)

    def write_warning(self, message: str, *args, **kwargs) -> None:
        self.write(self.style.WARNING(message), *args, **kwargs)

    def write_sql_coltype(self, message: str, *args, **kwargs) -> None:
        self.write(self.style.SQL_COLTYPE(message), *args, **kwargs)

    def write_migrate_heading(self, message: str, *args, **kwargs) -> None:
        self.write(self.style.MIGRATE_HEADING(message), *args, **kwargs)

    def write_migrate_label(self, message: str, *args, **kwargs) -> None:
        self.write(self.style.MIGRATE_LABEL(message), *args, **kwargs)

    def write_sql_keyword(self, message: str, *args, **kwargs) -> None:
        self.write(self.style.SQL_KEYWORD(message), *args, **kwargs)

    def write_error(self, message: str, *args, **kwargs) -> None:
        self.write(self.style.ERROR(message), *args, **kwargs)

    def check(self, *args, **kwargs):
        super(GestoreCommand, self).check(*args, **kwargs)

        if self.use_bucket:
            self.check_bucket_config()
