from django.db.models import F, Value
from django.db.models.functions import Concat
from django.test import TestCase

from tests.models import TestModel


class SaveReturningTest(TestCase):
    fixtures = ['test_model']

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
