from typing import Any, List, Optional, Tuple, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import (
    ForeignKey,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneField,
)


def process_foreign_key(
        instance: Model,
        field: ForeignKey
) -> Tuple[Any, Model]:
    """
    What we are looking to achieve here is to get the ID of the object this
    instance is pointing at, and to return that instance for later processing.

    Note: This will process both; ForeignKeys and OneToOneKey. As in
    Django a OneToOneKey is sub class of ForeignKey.
    """
    # Gets the ID of the instance pointed at
    value = field.value_from_object(instance)
    return value, getattr(instance, field.name)


def process_one_to_many_relation(
        instance: Model,
        field: ManyToOneRel
) -> List[Model]:
    """
    In OneToManyRelations, it is this model that other objects are
    pointing at.
    We are collecting these models to make sure that this we are not
    missing any data used in some apps, and to protect the organization
    integrity.

    Unlike ForeignKey, we just need to return the instances pointing at
    this object so we can process it later.
    """
    manager = getattr(instance, field.get_accessor_name())
    to_process = [obj for obj in manager.all()] if manager else []

    return to_process


def process_one_to_one_relation(
        instance: Model,
        field: OneToOneField
) -> Optional[List[Model]]:
    """
    This is a little bit similar to the OneToManyRel, except that we
    attribute returns one instance when called instead of a Model Manager.
    """
    try:
        obj = getattr(instance, field.name)
    except ObjectDoesNotExist:
        # Nothing to do, we didn't find any object related to this
        # in the other model.
        obj = None

    return [obj, ]


def process_many_to_many_relation(
        instance: Model,
        field: Union[ManyToManyRel, ManyToManyField]
) -> Tuple[Any, List[Model]]:
    """
    Extracts all objects this instance is pointing at for later processing.
    Also returns a list of these objects IDs to be used as a value under
    the field name.
    """
    data = []
    to_process = []

    if isinstance(field, ManyToManyRel):
        # This is a ManyToMany Field in another model
        manager = getattr(instance, field.get_accessor_name())
        return None, [x for x in manager.all()]

    for relation in field.value_from_object(instance):
        data.append(relation.id)
        to_process.append(relation)

    return data, to_process
