from datetime import datetime

import json
import os

from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey

from gestore import processors
from gestore.encoders import GestoreEncoder
from gestore.gestore_command import GestoreCommand
from gestore.utils import get_obj_from_str, get_pip_packages


class Command(GestoreCommand):
    """
    Export a Tahoe website to be imported later.
    """
    def add_arguments(self, parser):
        parser.add_argument(
            'objects',
            help='List of all objects to export',
            nargs='+',
        )
        parser.add_argument(
            '-o', '--output',
            help='The location you want to direct your output to',
            default='%s/dist' % os.getcwd(),
            type=str,
        )
        parser.add_argument(
            '-d', '--debug',
            action='store_true',
            help='Execute in debug mode (Will not commit or save changes)'
        )

    def handle(self, *args, **options):
        """
        Verifies the input and packs the site objects.
        """
        self.debug = options['debug']

        self.write('Inspecting project for potential problems...')
        self.check(objects=options['objects'], display_num_errors=True)

        objects = [
            get_obj_from_str(obj) for obj in options['objects']
        ]
        self.write_migrate_heading(
            'Exporting "%s" in progress...' % options['objects']
        )

        # Processes the necessary data all exported objects share.
        # This data will be helpful if you are debugging or returning to an
        # earlier state later if any changes occur when packages gets updated,
        # or our code changes.
        # Also some instance tracking information has been added.
        export_data = {
            'version': str(self.version),
            'date': datetime.now(),
            'host_name': self.hostname,
            'ip_address': self.ip_address,
            'libraries': get_pip_packages(),
            'provided_objects': options['objects'],
            'objects': self.generate_objects(*objects),
        }

        output = json.dumps(
            export_data,
            sort_keys=True,
            indent=1,
            cls=GestoreEncoder
        )

        path = self.generate_file_path(options['output'])
        self.write_to_file(path, output)

        self.write_success('Objects successfully exported!')

    def generate_objects(self, *args):
        """
        A Breadth First Search technique to extract the objects and processing
        its children.
        What we are looking to achieve here is simply: Process the site; and
        any related object to it. This simply will give you all the data a site
        uses in order to operate properly when imported.

        We start with the site object, all discovered relations will be added
        to the queue to take part in the processing later. Same goes for any
        discovered relation.

        To avoid infinite loops and processing the same element more than one
        time, we check the discovered space (processing and processed objects)
        before adding new elements.

        :return: Simply all the discovered objects' data.
        """
        objects = []
        processing_queue = list(args)
        processed_objects = set()

        while processing_queue:
            instance = processing_queue.pop(0)
            item, pending_items = self.process_instance(instance)

            if item:
                objects.append(item)

            for pending_item in pending_items:
                is_processed = pending_item not in processed_objects
                is_processing = pending_item not in processing_queue
                should_process = bool(is_processed and is_processing)
                if should_process:
                    processing_queue.append(pending_item)

            processed_objects.add(instance)

        self.write('\n')
        return objects

    def process_instance(self, instance):
        """
        Inspired from: django.forms.models.model_to_dict
        Return a dict containing the data in ``instance`` suitable for passing
        as a Model's ``create`` keyword argument with all its discovered
        relations.
        """
        if not instance:
            return instance, []

        to_process = set()
        content_type = ContentType.objects.get_for_model(instance)
        opts = instance._meta  # pylint: disable=W0212

        data = {
            'model': '%s.%s' % (content_type.app_label, content_type.model),
            'fields': {},
        }

        if self.debug:
            self.write_migrate_label(
                'Processing a %s object...' % data['model']
            )

        # We are going to iterate over the fields one by one, and depending
        # on the type, we determine how to process them.
        for field in opts.get_fields():
            if isinstance(field, ForeignKey):
                value, item = processors.process_foreign_key(instance, field)
                data['fields'][field.name] = value
                to_process.add(item)

            elif field.one_to_many:
                items = processors.process_one_to_many_relation(
                    instance,
                    field
                )
                to_process.update(items)

            elif field.one_to_one:
                items = processors.process_one_to_one_relation(instance, field)
                to_process.update(items)

            elif field in opts.many_to_many:
                value, items = processors.process_many_to_many_relation(
                    instance, field
                )
                data['fields'][field.name] = value
                to_process.update(items)

            elif field in opts.concrete_fields or field in opts.private_fields:
                # Django stores the primary key under `id`
                if field.name == 'id':
                    data['pk'] = field.value_from_object(instance)
                else:
                    data['fields'][field.name] = field.value_from_object(
                        instance
                    )

        if self.debug:
            self.write(
                'Finished processing %s object successfully!' % data['model']
            )
            self.write('%d new items to process' % len(to_process))
        else:
            self.write('.', ending='')

        return data, to_process

    def check(self, *args, **kwargs):
        objects = kwargs.pop('objects', [])

        self.check_migrations()
        self.check_objects(objects)

        super(Command, self).check()

    def check_objects(self, objects):
        for obj in objects:
            try:
                _, _, _ = obj.split('.')
            except ValueError:
                self.print_help('manage.py', 'export')
                self.raise_error(
                    'Bad object "%s" representation. Should '
                    'be app_label.model_name.obj_id' % obj
                )
