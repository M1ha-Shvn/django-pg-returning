import django
from django.db import transaction, models
from django.db.models import sql
from typing import Dict, Any, List, Type

from .queryset import ReturningQuerySet


class UpdateReturningMixin(object):
    @staticmethod
    def _get_loaded_field_cb(target, model, fields):
        """
        Callback used by get_deferred_field_names().
        """
        target[model] = fields

    def _get_fields(self):  # type: () -> Dict[models.Model: List[models.Field]]
        """
        Gets a dictionary of fields for each model, selected by .only() and .defer() methods
        :return: A dictionary with model as key, fields list as value
        """
        fields = {}
        self.query.deferred_to_data(fields, self._get_loaded_field_cb)

        # No .only() or .defer() operations
        if not fields:
            if django.VERSION < (1, 8):
                fields = self.model._meta.local_fields
            else:
                fields = self.model._meta.get_fields()

            # Remove all related fields - they are not from this model
            fields = {self.model: [f for f in fields if not getattr(f, 'is_relation', False)]}

        return fields

    def _get_returning_qs(self, query_type, **updates):
        # type: (Type[sql.Query], **Dict[str, Any]) -> ReturningQuerySet
        """
        Partial for update_returning functions
        :param updates: Data to pass to update(**updates) method
        :return: RawQuerySet of results
        :raises AssertionError: If input data is invalid
        """
        assert self.query.can_filter(), "Can not update or delete once a slice has been taken."
        assert getattr(self, '_fields', None) is None,\
            "Can not call delete() or update() after .values() or .values_list()"

        # Returns attname, not column.
        fields = self._get_fields()
        assert len(fields) == 1 and list(fields.keys())[0] == self.model,\
            "You can't fetch relative model fields with returning operation"

        field_str = ', '.join('"%s"' % str(f.column) for f in fields[self.model])

        self._for_write = True

        # In django 2 query.clone() method in update was replaced with chain method
        if django.VERSION >= (2,):
            query = self.query.chain(query_type)
        else:
            query = self.query.clone(query_type)

        if updates:
            query.add_update_values(updates)

        # Disable not supported fields.
        query._annotations = None
        query.select_for_update = False
        query.select_related = False
        query.clear_ordering(force_empty=True)

        query_sql, query_params = query.get_compiler(self.db).as_sql()
        query_sql = query_sql + ' RETURNING %s' % field_str
        with transaction.atomic(using=self.db, savepoint=False):
            return ReturningQuerySet(query_sql, model=self.model, params=query_params, using=self.db,
                                     fields=[f.attname for f in fields[self.model]])

    def update_returning(self, **updates):
        # type: (**Dict[str, Any]) -> ReturningQuerySet
        """
        Gets RawQuerySet of all fields, got with UPDATE ... RETURNING fields
        :return: RawQuerySet
        """
        assert updates, "No updates where provided"
        return self._get_returning_qs(sql.UpdateQuery, **updates)

    def delete_returning(self):
        # type: (**Dict[str, Any]) -> ReturningQuerySet
        """
        Gets RawQuerySet of all fields, got with DELETE ... RETURNING
        :return: RawQuerySet
        """
        return self._get_returning_qs(sql.DeleteQuery)


class UpdateReturningQuerySet(UpdateReturningMixin, models.QuerySet):
    pass


class UpdateReturningManager(models.Manager):
    def get_queryset(self):
        return UpdateReturningQuerySet(using=self.db, model=self.model)