"""
This file contains tests for UpdateReturningManager
"""
import django
from django.db.models import Model, F
from django.db.models.query_utils import DeferredAttribute
from django.test import TestCase

from tests.models import TestModel, TestRelModel


def _attr_is_deferred(instance, attname):  # type: (Model, str) -> bool
    """
    Tests if attname is a Defered attribute, not got by the query
    From https://stackoverflow.com/questions/28222469/determine-if-an-attribute-is-a-deferredattribute-in-django
    :return: Bool
    """
    if django.VERSION < (1, 8):
        return isinstance(instance.__class__.__dict__.get(attname), DeferredAttribute)
    else:
        return attname in instance.get_deferred_fields()


class UpdateReturningTest(TestCase):
    fixtures = ['test_model', 'test_rel_model']

    def test_simple(self):
        result = TestModel.objects.filter(pk__in={3, 4, 5}).update_returning(name='updated')

        # Data updated
        for item in TestModel.objects.filter(pk__in={3, 4, 5}):
            self.assertEqual("updated", item.name)

        # Result returned correct
        for i, item in enumerate(sorted(result, key=lambda x: x.pk)):
            self.assertIsInstance(item, TestModel)
            self.assertEqual(3 + i, item.pk)
            self.assertEqual("updated", item.name)
            self.assertEqual(3 + i, item.int_field)

    def test_only(self):
        result = TestModel.objects.filter(pk__in={3, 4, 5}).only('int_field').update_returning(name='updated')

        # Data updated
        for item in TestModel.objects.filter(pk__in={3, 4, 5}):
            self.assertEqual("updated", item.name)

        # Result returned correct
        for i, item in enumerate(sorted(result, key=lambda x: x.pk)):
            self.assertIsInstance(item, TestModel)

            # Test correct items are deferred
            self.assertFalse(_attr_is_deferred(item, 'int_field'))
            self.assertFalse(_attr_is_deferred(item, 'id'))  # Id is selected for RawQuerySet work
            self.assertTrue(_attr_is_deferred(item, 'name'))

            # Test data
            self.assertEqual(3 + i, item.int_field)
            self.assertEqual(3 + i, item.id)

    def test_defer(self):
        result = TestModel.objects.filter(pk__in={3, 4, 5}).defer('name').update_returning(name='updated')

        # Data updated
        for item in TestModel.objects.filter(pk__in={3, 4, 5}):
            self.assertEqual("updated", item.name)

        # Result returned correct
        for i, item in enumerate(sorted(result, key=lambda x: x.pk)):
            self.assertIsInstance(item, TestModel)

            # Test correct items are deferred
            self.assertFalse(_attr_is_deferred(item, 'int_field'))
            self.assertFalse(_attr_is_deferred(item, 'id'))  # Id is selected for RawQuerySet work
            self.assertTrue(_attr_is_deferred(item, 'name'))

            # Test data
            self.assertEqual(3 + i, item.int_field)
            self.assertEqual(3 + i, item.id)

    def test_foreign_key_not_deferred(self):
        # This test originates from https://github.com/M1hacka/django-pg-returning/issues/10

        result = TestRelModel.objects.filter(pk__in={1, 2}).update_returning(fk=F('pk'))
        for item in result:
            self.assertFalse(_attr_is_deferred(item, 'fk_id'))
            self.assertFalse(_attr_is_deferred(item, 'o2o_id'))


class DeleteReturningTest(TestCase):
    fixtures = ['test_model']

    def test_simple(self):
        result = TestModel.objects.filter(pk__in={3, 4, 5}).delete_returning()

        # Data updated
        self.assertFalse(TestModel.objects.filter(pk__in={3, 4, 5}).exists())

        # Result returned correct
        for i, item in enumerate(sorted(result, key=lambda x: x.pk)):
            self.assertIsInstance(item, TestModel)
            self.assertEqual(3 + i, item.pk)
            self.assertEqual("test%d" % (3 + i), item.name)
            self.assertEqual(3 + i, item.int_field)

    def test_only(self):
        result = TestModel.objects.filter(pk__in={3, 4, 5}).only('int_field').delete_returning()

        # Data updated
        self.assertFalse(TestModel.objects.filter(pk__in={3, 4, 5}).exists())

        # Result returned correct
        for i, item in enumerate(sorted(result, key=lambda x: x.pk)):
            self.assertIsInstance(item, TestModel)

            # Test correct items are deferred
            self.assertFalse(_attr_is_deferred(item, 'int_field'))
            self.assertFalse(_attr_is_deferred(item, 'id'))  # Id is selected for RawQuerySet work
            self.assertTrue(_attr_is_deferred(item, 'name'))

            # Test data
            self.assertEqual(3 + i, item.int_field)
            self.assertEqual(3 + i, item.id)

    def test_defer(self):
        result = TestModel.objects.filter(pk__in={3, 4, 5}).defer('name').delete_returning()

        # Data updated
        self.assertFalse(TestModel.objects.filter(pk__in={3, 4, 5}).exists())

        # Result returned correct
        for i, item in enumerate(sorted(result, key=lambda x: x.pk)):
            self.assertIsInstance(item, TestModel)

            # Test correct items are deferred
            self.assertFalse(_attr_is_deferred(item, 'int_field'))
            self.assertFalse(_attr_is_deferred(item, 'id'))  # Id is selected for RawQuerySet work
            self.assertTrue(_attr_is_deferred(item, 'name'))

            # Test data
            self.assertEqual(3 + i, item.int_field)
            self.assertEqual(3 + i, item.id)

    def test_foreign_key_not_deferred(self):
        # This test originates from https://github.com/M1hacka/django-pg-returning/issues/10

        result = TestRelModel.objects.filter(pk__in={1, 2}).delete_returning()
        for item in result:
            self.assertFalse(_attr_is_deferred(item, 'fk_id'))
            self.assertFalse(_attr_is_deferred(item, 'o2o_id'))
