from datetime import datetime

import json

from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey, Model

from gestore import processors
from gestore.encoders import GestoreEncoder
from gestore.gestore_command import GestoreCommand
from gestore.utils import get_model_name, get_obj_from_str, get_pip_packages, \
    instance_representation


class Command(GestoreCommand):
    """
    Export objects in a format that can be imported later.
    """
    def add_arguments(self, parser) -> None:
        # Add common args
        super(Command, self).add_arguments(parser)

        parser.add_argument(
            'objects',
            help='List of all objects to export',
            nargs='+',
        )

        parser.add_argument(
            '-r', '--root',
            help='List of all model\'s names to consider as root',
            nargs='*',
        )
        parser.add_argument(
            '-o', '--output',
            help='The location you want to direct your output to',
            default=self.exports_dir,
            type=str,
        )

    def handle(self, *args, **options) -> None:
        """
        Verifies the input and packs the objects.
        """
        self.debug = options['debug']
        self.use_bucket = options['bucket']
        self.write('Inspecting project for potential problems...')
        self.check(objects=options['objects'], display_num_errors=True)

        objects = [
            get_obj_from_str(obj) for obj in options['objects']
        ]
        self.write_migrate_heading(
            'Exporting %s in progress...' % options['objects']
        )

        # Processes the necessary data all exported objects share.
        # This data will be helpful if you are debugging or returning to an
        # earlier state later if any changes occur when packages gets updated,
        # or our code changes.
        # Also some instance tracking information has been added.
        export_data = {
            'version': str(self.get_version()),
            'date': datetime.now(),
            'host_name': self.hostname,
            'ip_address': self.ip_address,
            'libraries': get_pip_packages(),
            'provided_objects': options['objects'],
            'objects': self.generate_objects(
                *objects, root_models=options['root']
            ),
        }

        output = json.dumps(
            export_data,
            sort_keys=True,
            indent=1,
            cls=GestoreEncoder
        )

        path = self.generate_file_path(options['output'])
        self.write_exports_file(path, output)

        self.write_success('Objects successfully exported!')

    def generate_objects(self, *args: [Model], root_models=None) -> list:
        """
        A Depth First Search implementation to extract the given objects and
        process their children.
        What we are looking to achieve here is simply: For each object; process
        it; and all objects related to it. This will give you all the data
        that object uses in order to operate properly when imported.

        When processing an object, some discovered relations will be added
        to the stack to take part in the processing later. Same goes for any
        discovered relation in that queue.

        The relations that are not going to be processed are objects of what
        we call Root Models. A root model is identified using two ways:
            - Any object in the same model of the object you're trying to
              export. For example; if you're exporting a user object from
              model User, we are not going to process any other user in that
              model except the given one.
            - A set of models the user manually provides.

        To avoid infinite loops caused by processing the same element multiple
        times, we check the discovered space (processing and processed objects)
        before adding new elements.

        :return: Simply all discovered objects' data.
        """
        objects = []
        visited = {}

        processing_stack = list(args)
        in_processing_stack = {
            instance_representation(instance): True
            for instance in args
        }

        if not root_models:
            root_models = set()

        root_models = set(get_model_name(i) for i in args).union(root_models)

        while processing_stack:
            instance = processing_stack.pop()
            instance_key = instance_representation(instance)

            in_processing_stack[instance_key] = False
            item, pending_items = self.process_instance(instance)

            if item:
                objects.append(item)

            for pending_item in pending_items:
                pending_item_key = instance_representation(pending_item)

                is_root_object = get_model_name(pending_item) in root_models
                is_processed = visited.get(pending_item_key, False)
                is_processing = in_processing_stack.get(
                    pending_item_key, False
                )

                # Equivalent to not is_processed and not is_...
                should_process = not (
                        is_processed or is_processing or is_root_object
                )
                if should_process:
                    processing_stack.append(pending_item)
                    in_processing_stack[pending_item_key] = True

            visited[instance_key] = True

        self.write('\n')
        for error in self.errors:
            self.write_warning('Error processing field %s from %s: %s' % error)

        self.write(
            'Total exported objects is %d (%d processed, %d errors)'
            % (len(objects), len(visited), len(self.errors))
        )

        return objects

    def process_instance(self, instance: Model):
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
                'Processing %s object with ID %s...' %
                (data['model'], instance.id)
            )

        # We are going to iterate over the fields one by one, and depending
        # on the type, we determine how to process them.
        for field in opts.get_fields():
            try:
                if isinstance(field, ForeignKey):
                    value, item = processors.process_foreign_key(
                        instance, field
                    )
                    data['fields'][field.name] = value
                    to_process.add(item)
                elif field.one_to_many:
                    items = processors.process_one_to_many_relation(
                        instance,
                        field
                    )
                    to_process.update(items)
                elif field.one_to_one:
                    items = processors.process_one_to_one_relation(
                        instance,
                        field
                    )
                    to_process.update(items)
                elif field.many_to_many:
                    value, items = processors.process_many_to_many_relation(
                        instance,
                        field
                    )

                    if value is not None:
                        data['fields'][field.name] = value

                    to_process.update(items)
                elif field in opts.concrete_fields \
                        or field in opts.private_fields:
                    # Django stores the primary key under `id`
                    if field.name == 'id':
                        data['pk'] = field.value_from_object(instance)
                    else:
                        data['fields'][field.name] = field.value_from_object(
                            instance
                        )
                else:
                    self.write_migrate_label('SKIPPED %s' % str(field))
            except Exception as e:
                self.errors.append((instance, field, e))

        if self.debug:
            self.write('Finished processing %s object' % data['model'])
            self.write('%d new items to process' % len(to_process))
        else:
            self.write('.', ending='')

        return data, to_process

    def check(self, *args, **kwargs) -> None:
        objects = kwargs.pop('objects', [])

        self.check_migrations()
        self.check_objects(objects)

        super(Command, self).check(*args, **kwargs)

    def check_objects(self, objects: str) -> None:
        for obj in objects:
            try:
                _, _, _ = obj.split('.')
            except ValueError:
                self.print_help('manage.py', 'export')
                self.raise_error(
                    'Bad object "%s" representation. Should '
                    'be app_label.model_name.obj_id' % obj
                )
