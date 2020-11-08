from typing import Dict, Any, List, Type, Optional, Tuple

import django
from django.db import transaction, models
from django.db.models import sql, Field, QuerySet

from .compatibility import chain_query, get_model_fields
from .queryset import ReturningQuerySet

# DEPRECATED class package changed in django 1.11
#  link has been removed in django 3.1
try:
    from django.core.exceptions import EmptyResultSet
except ImportError:
    from django.db.models.query import EmptyResultSet


class UpdateReturningMixin(object):
    @staticmethod
    def _get_loaded_field_cb(target, model, fields):
        """
        Callback used by get_deferred_field_names().
        """
        target[model] = fields

    def _insert(self, objs, fields, **kwargs):
        """
        Replaces standard insert procedure for bulk_create_returning
        """
        if not getattr(self.model, '_insert_returning', False):
            return QuerySet._insert(self, objs, fields, **kwargs)

        # Returns attname, not column.
        # Before django 1.10 pk fields hasn't been returned from postgres.
        # In this case, I can't match bulk_create results and return values by primary key.
        # So I select all data from returned results
        return_fields = self._get_fields(ignore_deferred=(django.VERSION < (1, 10)))
        assert len(return_fields) == 1 and list(return_fields.keys())[0] == self.model, \
            "You can't fetch relative model fields with returning operation"

        self._for_write = True
        using = kwargs.get('using', None) or self.db

        query_kwargs = {} if django.VERSION < (2, 2) else {'ignore_conflicts': kwargs.get('ignore_conflicts')}
        query = sql.InsertQuery(self.model, **query_kwargs)
        query.insert_values(fields, objs, raw=kwargs.get('raw'))

        self.model._insert_returning_cache = self._execute_sql(query, return_fields, using=using)
        if django.VERSION < (3,):
            if not kwargs.get('return_id', False):
                return None

            inserted_ids = self.model._insert_returning_cache.values_list(self.model._meta.pk.column, flat=True)
            if not inserted_ids:
                return None

            return list(inserted_ids) if len(inserted_ids) > 1 else inserted_ids[0]
        else:
            returning_fields = kwargs.get('returning_fields', None)
            if returning_fields is None:
                return None

            columns = [f.column for f in returning_fields]

            # In django 3.0 single result is returned if single object is returned...
            flat = django.VERSION < (3, 1) and len(objs) <= 1

            return self.model._insert_returning_cache.values_list(*columns, flat=flat)

    _insert.alters_data = True
    _insert.queryset_only = False

    def _get_fields(self, ignore_deferred=False):  # type: (bool) -> Dict[models.Model: List[models.Field]]
        """
        Gets a dictionary of fields for each model, selected by .only() and .defer() methods
        :param ignore_deferred: If set, ignores .only() and .defer() filters
        :return: A dictionary with model as key, fields list as value
        """
        fields = {}

        if not ignore_deferred:
            self.query.deferred_to_data(fields, self._get_loaded_field_cb)

        # No .only() or .defer() operations
        if not fields:
            # Remove all fields without columns in table
            fields = {self.model: get_model_fields(self.model, concrete=True)}

        return fields

    def _execute_sql(self, query, return_fields, using=None):
        return_fields_str = ', '.join('"%s"' % str(f.column) for f in return_fields[self.model])

        if using is None:
            using = self.db

        self._result_cache = None
        try:
            res = query.get_compiler(using).as_sql()
            if isinstance(res, list):
                assert len(res) == 1, "Can't update relative model with returning"
                res = res[0]
            query_sql, query_params = res
        except EmptyResultSet:
            return ReturningQuerySet(None)

        query_sql = query_sql + ' RETURNING %s' % return_fields_str
        with transaction.atomic(using=using, savepoint=False):
            return ReturningQuerySet(query_sql, model=self.model, params=query_params, using=using,
                                     fields=[f.attname for f in return_fields[self.model]])

    def _get_returning_qs(self, query_type, values=None, **updates):
        # type: (Type[sql.Query], Optional[Any], **Dict[str, Any]) -> ReturningQuerySet
        """
        Partial for update_returning functions
        :param updates: Data to pass to update(**updates) method
        :return: RawQuerySet of results
        :raises AssertionError: If input data is invalid
        """
        assert self.query.can_filter(), "Can not update or delete once a slice has been taken."
        assert getattr(self, '_fields', None) is None, \
            "Can not call delete() or update() after .values() or .values_list()"

        # Returns attname, not column.
        fields = self._get_fields()
        assert len(fields) == 1 and list(fields.keys())[0] == self.model, \
            "You can't fetch relative model fields with returning operation"

        self._for_write = True

        query = chain_query(self, query_type)

        if updates:
            query.add_update_values(updates)

        if values:
            query.add_update_fields(values)

        # Disable not supported fields.
        query._annotations = None
        query.select_for_update = False
        query.select_related = False
        query.clear_ordering(force_empty=True)

        return self._execute_sql(query, fields)

    def create_returning(self, **kwargs):
        """
        Just copies native create method, replacing save(...) call to save_returning(...) call
        :param kwargs: Parameters to create model with
        :return: Model instance, saved to database
        """
        obj = self.model(**kwargs)
        self._for_write = True
        obj.save_returning(force_insert=True, using=self.db)
        return obj

    def update_returning(self, **updates):
        # type: (**Dict[str, Any]) -> ReturningQuerySet
        """
        Gets RawQuerySet of all fields, got with UPDATE ... RETURNING fields
        :return: RawQuerySet
        """
        assert updates, "No updates where provided"
        return self._get_returning_qs(sql.UpdateQuery, **updates)

    def _update_returning(self, values):
        # type: (List[Tuple[Field, Any, Any]]) -> ReturningQuerySet
        """
        A version of update_returning() that accepts field objects instead of field names.
        Used primarily for model saving and not intended for use by general
        code (it requires too much poking around at model internals to be
        useful at that level).
        """
        assert values, "No updates where provided"
        return self._get_returning_qs(sql.UpdateQuery, values=values)

    def delete_returning(self):  # type: () -> ReturningQuerySet
        """
        Gets RawQuerySet of all fields, got with DELETE ... RETURNING
        :return: RawQuerySet
        """
        return self._get_returning_qs(sql.DeleteQuery)

    def bulk_create_returning(self, objs, batch_size=None):
        # It's more logical to use QuerySet object to store this data.
        # But django before 1.10 calls self.model._base_manager._insert instead of self._insert
        # And generates other QuerySet.
        self.model._insert_returning = True
        self.model._insert_returning_cache = {}

        if django.VERSION < (1, 10):
            base_manager = self.model._base_manager
            try:
                # Compatibility for old django versions which call self.model._base_manager._insert instead of self._insert
                self.model._base_manager = self.as_manager()
                self.model._base_manager.model = self.model
                result = self.bulk_create(objs, batch_size=batch_size)
            finally:
                # Restore base manager after operation, event if it failed.
                # If not restored, it will be shared by other code
                self.model._base_manager = base_manager
        else:
            result = self.bulk_create(objs, batch_size=batch_size)

        # Replace values fetched from returned data
        if result and result[0].pk:
            # For django 1.10+ where objects can be matched
            values_dict = {item[self.model._meta.pk.column]: item for item in
                           self.model._insert_returning_cache.values()}
            for item in result:
                for k, v in values_dict[item.pk].items():
                    setattr(item, k, v)
        else:
            # For django before 1.10 which doesn't fetch primary key
            result = list(self.model._insert_returning_cache)

        # Clean up
        self.model._insert_returning = False
        self.model._insert_returning_cache = {}

        return result


class UpdateReturningQuerySet(UpdateReturningMixin, models.QuerySet):
    @classmethod
    def clone_query_set(cls, qs):  # type: (QuerySet) -> UpdateReturningQuerySet
        """
        Copies standard QuerySet.clone() method, changing base class name
        :param qs: QuerySet to copy from
        :return: An UpdateReturningQuerySet, cloned from qs
        """
        query = chain_query(qs)
        c = cls(model=qs.model, query=query, using=qs._db, hints=qs._hints)
        c._sticky_filter = qs._sticky_filter
        c._for_write = qs._for_write
        c._prefetch_related_lookups = qs._prefetch_related_lookups[:]
        c._known_related_objects = qs._known_related_objects

        # Some fields are absent in earlier django versions
        if hasattr(qs, '_iterable_class'):
            c._iterable_class = qs._iterable_class

        if hasattr(qs, '_fields'):
            c._fields = qs._fields

        return c


class UpdateReturningManager(models.Manager):
    def bulk_create_returning(self, objs, batch_size=None):
        # In early django automatic fetching QuerySet public methods fails
        return self.get_queryset().bulk_create_returning(objs, batch_size=batch_size)

    def create_returning(self, **kwargs):
        # In early django automatic fetching QuerySet public methods fails
        return self.get_queryset().create_returning(**kwargs)

    def update_returning(self, **updates):
        # In early django automatic fetching QuerySet public methods fails
        return self.get_queryset().update_returning(**updates)

    def delete_returning(self):
        # In early django automatic fetching QuerySet public methods fails
        return self.get_queryset().delete_returning()

    def get_queryset(self):
        return UpdateReturningQuerySet(using=self.db, model=self.model)
