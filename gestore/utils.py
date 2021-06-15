import pkg_resources

from django.apps import apps


def get_pip_packages():
    """
    Returns a dictionary of pip packages names and their versions. Similar
    to `$ pip freeze`
    """
    return {
        package.project_name: package.version
        for package in pkg_resources.working_set
    }


def has_conflict(Model, object_id):
    return Model.objects.filter(id=object_id).exists()


def get_obj_from_str(object_rep):
    app_label, model_name, obj_id = object_rep.split('.')
    Model = apps.get_model(app_label, model_name)
    return Model.objects.get(id=obj_id)


def get_str_from_model(Model, object_id=None):
    model_path = '.'.join([Model._meta.app_label, Model.__name__])

    if object_id:
        model_path += '.%s' % object_id

    return model_path

