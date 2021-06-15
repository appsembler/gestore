import os
import socket
from abc import ABC
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from semantic_version import Version


class GestoreCommand(BaseCommand, ABC):
    """
    Parent management command for Gestore.
    """
    # Increase this version by 1 after every backward-incompatible
    # change in the exported data format
    VERSION = Version('0.1.0')

    def __init__(self, *args, **kwargs):
        self.debug = False
        self.hostname = socket.gethostname()
        self.ip_address = self._get_ip_address(self.hostname)

        self.version = self.VERSION

        super(GestoreCommand, self).__init__(*args, **kwargs)

    def generate_file_path(self, path):
        """
        Determines and returns the output file name.
        If the user specified a full path, then just return it. If a partial
        path has been specified, we add the file name to it and return. Other
        wise, we combine our base path with the file name and return them.
        """
        if path.endswith('.json'):
            return path

        timestamp = (datetime.now() - datetime(1970, 1, 1)).total_seconds()
        file_name = '%s_%s.json' % (self.hostname, timestamp)

        if not os.path.exists(path):
            os.makedirs(path)

        path = os.path.join(path, file_name)
        return path

    def _get_ip_address(self, hostname):
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            pass

        return '127.0.0.1'

    def write(self, message, *args, **kwargs):
        self.stdout.write(message, *args, **kwargs)

    def write_info(self, message, *args, **kwargs):
        self.write(self.style.HTTP_INFO(message), *args, **kwargs)

    def write_success(self, message, *args, **kwargs):
        self.write(self.style.SUCCESS(message), *args, **kwargs)

    def write_warning(self, message, *args, **kwargs):
        self.write(self.style.WARNING(message), *args, **kwargs)

    def write_sql_coltype(self, message, *args, **kwargs):
        self.write(self.style.SQL_COLTYPE(message), *args, **kwargs)

    def write_migrate_heading(self, message, *args, **kwargs):
        self.write(self.style.MIGRATE_HEADING(message), *args, **kwargs)

    def write_migrate_label(self, message, *args, **kwargs):
        self.write(self.style.MIGRATE_LABEL(message), *args, **kwargs)

    def write_sql_keyword(self, message, *args, **kwargs):
        self.write(self.style.SQL_KEYWORD(message), *args, **kwargs)

    def write_error(self, message, *args, **kwargs):
        self.write(self.style.ERROR(message), *args, **kwargs)

    def write_to_file(self, path, content):
        """
        Writes content in the specified path.
        """
        if self.debug:
            self.write_warning(
                'You are running in DEBUG mode. '
                'Output will be printed to console'
            )
            self.write('Command output >>>')
            self.write_migrate_label(content)

            return

        with open(path, 'w') as file:
            file.write(content)

        self.write_migrate_heading('Content saved in %s' % path)

    def raise_error(self, message):
        raise CommandError(message)
