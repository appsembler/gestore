from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist


def process_foreign_key(instance, field):
    """
    What we are looking to achieve from here is the to get the ID of the
    object this instance is pointing at, and to return that instance for
    later processing.

    Note: This will process both; ForeignKeys and OneToOneKey. As in
    Django a OneToOneKey is sub class of ForeignKey.
    """
    # Gets the ID of the instance pointed at
    value = field.value_from_object(instance)
    return value, getattr(instance, field.name)


def process_one_to_many_relation(instance, field):
    """
    In OneToManyRelations, it is this model that other objects are
    pointing at.
    We are collecting these models to make sure that this we are not
    missing any data used in some apps, and to protect the organization
    integrity.

    Unlike ForeignKey, we just need too return the instances pointing at
    this object so we can process them later.
    """
    manager = getattr(instance, field.name, [])
    to_process = [obj for obj in manager.all()] if manager else []

    return to_process


def process_one_to_one_relation(instance, field):
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


def process_many_to_many_relation(instance, field):
    """
    Extracts all objects this instance is pointing at for later processing.
    Also returns a list of these objects IDs to be used as a value under
    the field name.
    """
    data = []
    to_process = []

    for relation in field.value_from_object(instance):
        data.append(relation.id)
        to_process.append(relation)

    return data, to_process
