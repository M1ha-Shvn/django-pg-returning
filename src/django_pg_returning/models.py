from typing import Iterable, Optional, List

from django.db import models

from .manager import UpdateReturningManager, UpdateReturningMixin, UpdateReturningQuerySet


class UpdateReturningModel(models.Model):
    class Meta:
        abstract = True

    objects = UpdateReturningManager()

    def __init__(self, *args, **kwargs):
        super(UpdateReturningModel, self).__init__(*args, **kwargs)
        self._returning_save = False

    def _do_update_and_refresh(self, qs, values, update_fields):
        # type: (UpdateReturningMixin, List[tuple], Optional[Iterable[str]]) -> int
        """
        Tries updating filtered QuerySet, returning update_fields.
        If succeeded, updates current object with results.
        :param qs: QuerySet to update
        :param values: Values to update
        :param update_fields: Fields to update
        :return: Number of records updated
        """
        self._returning_save = False

        # Return only fields we need to update
        # This method should be supported by any django QuerySet
        if update_fields is not None:
            qs = qs.only(*update_fields)

        # In earlier django there is no ability to change base QuerySet
        qs = UpdateReturningQuerySet.clone_query_set(qs)

        res = qs._update_returning(values)
        if res.count() > 0:
            for k, v in res.values()[0].items():
                setattr(self, k, v)

        return res.count()

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        """
        Try to update the model. Return True if the model was updated (if an
        update query was done and a matching row was found in the DB).
        """
        # If object has been saved in cache using pickle before library update
        # It can cause getting attribute fail
        is_returning_save = getattr(self, '_returning_save', False)

        filtered = base_qs.filter(pk=pk_val)
        if not values:
            # We can end up here when saving a model in inheritance chain where
            # update_fields doesn't target any field in current model. In that
            # case we just say the update succeeded. Another case ending up here
            # is a model with just PK - in that case check that the PK still
            # exists.
            return update_fields is not None or filtered.exists()
        if self._meta.select_on_save and not forced_update:
            if filtered.exists():
                # It may happen that the object is deleted from the DB right after
                # this check, causing the subsequent UPDATE to return zero matching
                # rows. The same result can occur in some rare cases when the
                # database returns zero despite the UPDATE being executed
                # successfully (a row is matched and updated). In order to
                # distinguish these two cases, the object's existence in the
                # database is again checked for if the UPDATE query returns 0.
                if is_returning_save:
                    updated_count = self._do_update_and_refresh(filtered, values, update_fields)
                else:
                    updated_count = filtered._update(values)
                return updated_count > 0 or filtered.exists()
            else:
                return False

        if is_returning_save:
            return self._do_update_and_refresh(filtered, values, update_fields) > 0
        else:
            return filtered._update(values) > 0

    def _do_insert(self, manager, using, fields, returning_fields, raw):
        # NOTE returning_fields was renamed from update_pk in django 3.0.
        #  But function signature has not changed, so it can be used in such a way.

        # If object has been saved in cache using pickle before library update
        # It can cause getting attribute fail
        is_returning_save = getattr(self, '_returning_save', False)

        # _do_insert is called with cls._base_manager, which has no returning features
        if is_returning_save:
            manager = self.__class__.objects
            setattr(manager.model, '_insert_returning', is_returning_save)

        res = super(UpdateReturningModel, self)._do_insert(manager, using, fields, returning_fields, raw)
        if is_returning_save:
            returning_cache = getattr(manager.model, '_insert_returning_cache', None)

            if returning_cache and returning_cache.count():
                for attr, val in returning_cache.values()[0].items():
                    setattr(self, attr, val)

        self._returning_save = False
        return res

    def save_returning(self, *args, **kwargs):
        """
        A version of save() methods that reloads field values after update.
        It may be useful if fields are updated with F object, and you need to get resulting value.
        :param args: Arguments to pass to basic save() method
        :param kwargs: Arguments to pass to basic save() method
        :return: Updated instance
        """
        self._returning_save = True
        return super(UpdateReturningModel, self).save(*args, **kwargs)
