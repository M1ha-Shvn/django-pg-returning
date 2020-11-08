from unittest.case import skipIf

import django
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.test import TestCase

from tests.models import TestModel


class SaveReturningTest(TestCase):
    fixtures = ['test_model']

    @skipIf(django.VERSION < (1, 9), 'Django before 1.9 does not support saving functions')
    def test_create(self):
        instance = TestModel(name=Concat(Value("hello "), Value("world")))
        instance.save_returning()
        self.assertEqual('hello world', instance.name)

    def test_no_update_fields(self):
        instance = TestModel.objects.get(pk=1)
        instance.int_field = F('int_field') + 10
        instance.name = 'saved_value'
        instance.save_returning()

        self.assertEqual(11, instance.int_field)
        self.assertEqual('saved_value', instance.name)

    def test_no_extra_fields_updated(self):
        instance = TestModel.objects.get(pk=1)
        instance.int_field = F('int_field') + 10
        instance.name = 'not_saved_value'
        instance.save_returning(update_fields=['int_field'])

        self.assertEqual(11, instance.int_field)
        self.assertEqual('not_saved_value', instance.name)

    def test_native_create(self):
        instance = TestModel.objects.create(name='abc', int_field=100)
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(100, instance.int_field)
        self.assertEqual('abc', instance.name)
        self.assertIsInstance(instance.pk, int)

    def test_native_update(self):
        instance = TestModel.objects.get(pk=1)
        instance.int_field = 2
        instance.save(update_fields=['int_field'])
        instance.refresh_from_db()
        self.assertEqual(2, instance.int_field)
