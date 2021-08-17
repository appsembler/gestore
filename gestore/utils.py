from __future__ import print_function
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


def write_packages_diff(
        local_packages,
        exported_packages,
        writer=print
):
    """
    Checks the difference between two different packages dictionaries.
    """
    packages = {
        key: (local_packages.get(key), exported_packages.get(key))
        for key in set(local_packages).union(exported_packages)
    }

    for package, (local_version, exported_version) in packages.items():
        if local_version != exported_version:
            if not local_version:
                writer(
                    '%s==%s not found in your local '
                    'env' % (package, exported_version)
                )
            elif not exported_version:
                writer(
                    '%s==%s not found in your exported '
                    'env' % (package, local_version)
                )
            else:
                writer(
                    '%s local version is %s and exported version is %s'
                    % (package, local_version, exported_version)
                )


def has_conflict(model, object_id):
    return model.objects.filter(id=object_id).exists()


def get_obj_from_str(object_rep):
    app_label, model_name, obj_id = object_rep.split('.')
    Model = apps.get_model(app_label, model_name)
    return Model.objects.get(id=obj_id)


def get_str_from_model(model, object_id=None):
    model_path = '.'.join([model._meta.app_label, model.__name__])

    if object_id:
        model_path += '.%s' % object_id

    return model_path
