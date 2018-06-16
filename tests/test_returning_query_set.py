from django.db.models import F, ManyToOneRel
from django.test import TestCase

from tests.models import TestModel


class UpdateReturningTest(TestCase):
    fixtures = ['test_model']

    def test_count(self):
        result = TestModel.objects.filter(id__gt=2, id__lte=5).update_returning(int_field=21)
        self.assertEqual(3, result.count())

    def test_len(self):
        result = TestModel.objects.filter(id__gt=2, id__lte=5).update_returning(int_field=21)
        self.assertEqual(3, len(result))

    def test_index(self):
        result = TestModel.objects.filter(id=2).update_returning(int_field=F('pk') + 2)
        self.assertEqual(4, result[0].int_field)

    def test_slice(self):
        result = TestModel.objects.filter(id__gt=2, id__lte=5).update_returning(int_field=21)
        self.assertListEqual([3, 4, 5], [item.pk for item in result[0:3]])

    def test_values(self):
        result = TestModel.objects.filter(id=2).update_returning(int_field=21)
        self.assertListEqual([{'int_field': 21}], result.values('int_field'))
        self.assertListEqual([{'int_field': 21, 'id': 2, 'name': 'test2'}], result.values())

    def test_values_list(self):
        result = TestModel.objects.filter(id=2).only('id', 'int_field').update_returning(int_field=21)
        self.assertListEqual([(21,)], result.values_list('int_field'))
        self.assertListEqual([(21, 2)], result.values_list('int_field', 'id'))
        self.assertListEqual([21], result.values_list('int_field', flat=True))
        named_item = result.values_list('int_field', named=True)[0]
        self.assertEqual(21, named_item.int_field)

        with self.assertRaises(TypeError):
            result.values_list()

        with self.assertRaises(TypeError):
            result.values_list('int_field', flat=True, named=True)

        with self.assertRaises(TypeError):
            result.values_list('int_field', 'name', flat=True)

        with self.assertRaises(ValueError):
            result.values_list('int_field', 'name', invalid=True)

    def test_no_duplicate_query(self):
        pass
