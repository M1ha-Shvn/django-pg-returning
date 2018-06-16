"""
This file contains sample models to use in tests
"""
from django.db import models

from django_pg_returning import UpdateReturningManager


class TestModel(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True, default='')
    int_field = models.IntegerField(null=True, blank=True)

    objects = UpdateReturningManager()


# This model is not used in testing, but it creates reversed relations
# This is a simulation of issue-2
class TestRelModel(models.Model):
    fk = models.ForeignKey(TestModel, on_delete=models.CASCADE, related_name='fk')
    m2m = models.ManyToManyField(TestModel, related_name='m2m')
    o2m = models.OneToOneField(TestModel, on_delete=models.CASCADE, related_name='o2m')
