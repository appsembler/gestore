import os
import socket
import time
from abc import ABC

from django.core.management.base import BaseCommand, CommandError

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

        super(GestoreCommand, self).__init__(*args, **kwargs)

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '-d', '--debug',
            action='store_true',
            help='Execute in debug mode (Will not commit or save changes)'
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

    def write_to_file(self, path: str, content: str) -> None:
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

    def write(self, message, *args, **kwargs) -> None:
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
