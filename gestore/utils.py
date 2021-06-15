from typing import Any, Callable, Dict

import pkg_resources

from django.apps import apps
from django.db.models import Model


def get_pip_packages() -> Dict[str, str]:
    """
    Returns a dictionary of pip packages names and their versions. Similar
    to `$ pip freeze`
    """
    return {
        package.project_name: package.version
        for package in pkg_resources.working_set
    }


def write_packages_diff(
        local_packages: Dict[str, str],
        exported_packages: Dict[str, str],
        writer: Callable = print
) -> None:
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


def has_conflict(model: Model, object_id: Any) -> bool:
    return model.objects.filter(id=object_id).exists()


def get_obj_from_str(object_rep: str) -> Model:
    app_label, model_name, obj_id = object_rep.split('.')
    Model = apps.get_model(app_label, model_name)
    return Model.objects.get(id=obj_id)


def get_str_from_model(model: Model, object_id=None) -> str:
    model_path = '.'.join([model._meta.app_label, model.__name__])

    if object_id:
        model_path += '.%s' % object_id

    return model_path
