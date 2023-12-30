from collections import defaultdict

import django
from typing import Type, Optional, List, Dict

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


def clear_query_ordering(query):  # type: (Query) -> Query
    """
    Resets query ordering. Parameters changed in django 4.0
    :param query: Query to change
    :return: Resulting query
    """
    attr_name = 'force_empty' if django.VERSION < (4,) else 'force'
    query.clear_ordering(**{attr_name: True})
    return query


def prepare_insert_query_kwargs(kwargs):
    """
    Prepares kwargs for InsertQuery method based on kwargs from QuerySet._insert(...)
    :param kwargs: Original kwargs from QuerySet._insert(obj, fields, **kwargs)
    :return: kwargs ready for InsertQuery(model, **kwargs)
    """
    if django.VERSION < (2, 2):
        query_kwargs = {}
    elif django.VERSION < (4, 1):
        query_kwargs = {'ignore_conflicts': kwargs.get('ignore_conflicts')}
    else:
        query_kwargs = {
            'on_conflict': kwargs.get('on_conflict'),
            'update_fields': kwargs.get('update_fields'),
            'unique_fields': kwargs.get('unique_fields')
        }

    return query_kwargs


def get_not_deferred_fields(qs):  # type: (QuerySet) -> Dict[Type[Model], List[Field]]
    """
    Gets model fields for query
    :param qs: QuerySet for which we get required fields
    :return: A dictionary of lists {Model: [Field, Field, ...]}
    """
    fields = {}

    if django.VERSION >= (4, 2):
        fields = qs.query.get_select_mask()
        result_fields = defaultdict(list)
        for field in fields.keys():
            result_fields[field.model].append(field)
        fields = result_fields

    elif django.VERSION >= (4, 1):
        # Django 4.0 changed fields format
        qs.query.deferred_to_data(fields)
        fields = {
            model: [
                model._meta.get_field(field_name)
                for field_name in field_names
            ] for model, field_names in fields.items()
        }

    elif django.VERSION >= (1, 10):
        qs.query.deferred_to_data(fields, qs._get_loaded_field_cb)

    else:
        # Before django 1.10 pk fields hasn't been returned from postgres.
        # In this case, I can't match bulk_create results and return values by primary key.
        # So I select all data from returned results
        pass

    return fields
