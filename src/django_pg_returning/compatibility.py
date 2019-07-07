import django
from typing import Type, Optional, List

from django.db.models import Model, QuerySet, Field
from django.db.models.sql import Query


def chain_query(qs, query_type=None):  # type: (QuerySet, Optional[Type[Query]]) -> QuerySet
    """
    In django 2 query.clone() method in update was replaced with chain method
    """
    args = (query_type,) if query_type else ()
    if django.VERSION >= (2,):
        return qs.query.chain(*args)
    else:
        return qs.query.clone(*args)


def get_model_fields(model, concrete=False):  # type: (Type[Model], Optional[bool]) -> List[Field]
    """
    Gets model field
    :param model: Model to get fields for
    :param concrete: If set, returns only fields with column in model's table
    :return: A list of fields
    """
    if django.VERSION < (1, 8):
        if concrete:
            res = model._meta.concrete_fields
        else:
            res = model._meta.fields + model._meta.many_to_many
    else:
        res = model._meta.get_fields()

        if concrete:
            # Many to many fields have concrete flag set to True. Strange.
            res = [f for f in res if getattr(f, 'concrete', True) and not getattr(f, 'many_to_many', False)]

    return res
