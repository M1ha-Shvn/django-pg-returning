"""
This file contains tests for UpdateReturningManager
"""
from unittest import skipIf

import django
from django.db import connection
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


def create_int_field_trigger():
    """
    Creates a trigger which replaces int_field value with 100500 if it is odd
    :return: None
    """
    cursor = connection.cursor()
    cursor.execute('''
        CREATE OR REPLACE FUNCTION int_field_trigger()
        RETURNS trigger AS
        $BODY$
        BEGIN
           IF NEW.int_field % 2 = 1 THEN
               NEW.int_field = 100500;
           END IF;

           RETURN NEW;
        END;
        $BODY$ LANGUAGE plpgsql;
    ''')
    cursor.execute('''
        CREATE TRIGGER last_name_changes
        BEFORE INSERT
        ON tests_testmodel
        FOR EACH ROW
        EXECUTE PROCEDURE int_field_trigger();
    ''')


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

    def test_empty_filter(self):
        # This test originates from https://github.com/M1hacka/django-pg-returning/issues/9
        res = TestModel.objects.filter(id__in=[]).update_returning(name='abc')
        self.assertEqual(0, res.count())

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

    def test_empty_filter(self):
        # This test originates from https://github.com/M1hacka/django-pg-returning/issues/9
        res = TestModel.objects.filter(id__in=[]).update_returning(name='abc')
        self.assertEqual(0, res.count())

    def test_foreign_key_not_deferred(self):
        # This test originates from https://github.com/M1hacka/django-pg-returning/issues/10

        result = TestRelModel.objects.filter(pk__in={1, 2}).delete_returning()
        for item in result:
            self.assertFalse(_attr_is_deferred(item, 'fk_id'))
            self.assertFalse(_attr_is_deferred(item, 'o2o_id'))


class BulkCreateReturningTest(TestCase):
    fixtures = ['test_model']

    def setUp(self):
        create_int_field_trigger()

    def _test_result(self, create_objs, result, expected_count, replaced=True):
        expected_replaces = {item['name'] for item in create_objs if item['int_field'] % 2 == 1}

        # Data updated
        self.assertEqual(expected_count, TestModel.objects.count())

        # Trigger worked fine
        for item in create_objs:
            val = TestModel.objects.get(name=item['name']).int_field
            if item['name'] in expected_replaces:
                self.assertEqual(100500, val)
            else:
                self.assertEqual(item['int_field'], val)

        # Result returned correct
        for item in result:
            self.assertIsInstance(item, TestModel)
            if django.VERSION >= (1, 10):
                self.assertIsInstance(item.pk, int)

            if item.name in expected_replaces and replaced:
                self.assertEqual(item.int_field, 100500)
            else:
                self.assertEqual("name%d" % item.int_field, item.name)

    def test_simple(self):
        create_objs = [
            {'name': 'name1', 'int_field': 1},
            {'name': 'name2', 'int_field': 2}
        ]
        result = TestModel.objects.bulk_create_returning([TestModel(**data) for data in create_objs])
        self._test_result(create_objs, result, 11)

    @skipIf(django.VERSION < (1, 10), "Not supported for django before 1.10")
    def test_only(self):
        create_objs = [
            {'name': 'name1', 'int_field': 1},
            {'name': 'name2', 'int_field': 2}
        ]
        result = TestModel.objects.only('name').bulk_create_returning([TestModel(**data) for data in create_objs])
        self._test_result(create_objs, result, 11, replaced=False)

        create_objs = [
            {'name': 'name3', 'int_field': 3},
            {'name': 'name4', 'int_field': 4}
        ]
        result = TestModel.objects.only('int_field').bulk_create_returning([TestModel(**data) for data in create_objs])
        self._test_result(create_objs, result, 13)

    @skipIf(django.VERSION < (1, 10), "Not supported for django before 1.10")
    def test_defer(self):
        create_objs = [
            {'name': 'name1', 'int_field': 1},
            {'name': 'name2', 'int_field': 2}
        ]
        result = TestModel.objects.defer('int_field').bulk_create_returning([TestModel(**data) for data in create_objs])
        self._test_result(create_objs, result, 11, replaced=False)

        create_objs = [
            {'name': 'name3', 'int_field': 3},
            {'name': 'name4', 'int_field': 4}
        ]
        result = TestModel.objects.defer('name').bulk_create_returning([TestModel(**data) for data in create_objs])
        self._test_result(create_objs, result, 13)

    def test_foreign_key_not_deferred(self):
        # This test originates from https://github.com/M1hacka/django-pg-returning/issues/10

        result = TestRelModel.objects.bulk_create_returning([
            TestRelModel(fk_id=1, o2o_id=2),
            TestRelModel(fk_id=3, o2o_id=4)
        ])
        for item in result:
            self.assertFalse(_attr_is_deferred(item, 'fk_id'))
            self.assertFalse(_attr_is_deferred(item, 'o2o_id'))

    def test_base_bulk_create(self):
        create_objs = [
            {'name': 'name1', 'int_field': 1},
            {'name': 'name2', 'int_field': 2}
        ]
        result = TestModel.objects.bulk_create([TestModel(**data) for data in create_objs])
        self._test_result(create_objs, result, 11, replaced=False)


class CreateReturningTest(TestCase):
    fixtures = ['test_model']

    def setUp(self):
        create_int_field_trigger()

    def test_simple(self):
        instance = TestModel.objects.create_returning(name='hello', int_field=1)

        # returned data
        self.assertEqual('hello', instance.name)
        # self.assertEqual(100500, instance.int_field)

        # Database data
        instance.refresh_from_db()
        self.assertEqual('hello', instance.name)
        self.assertEqual(100500, instance.int_field)
