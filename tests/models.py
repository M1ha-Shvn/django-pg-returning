"""
This file contains sample models to use in tests
"""
from django.db import models

from django_pg_returning.models import UpdateReturningModel


class TestModel(UpdateReturningModel):
    name = models.CharField(max_length=50, null=True, blank=True, default='')
    int_field = models.IntegerField(null=True, blank=True)


# This model creates reversed relations
# This is a simulation of issue-2 and issue-10
class TestRelModel(UpdateReturningModel):
    fk = models.ForeignKey(TestModel, on_delete=models.CASCADE, related_name='fk')
    m2m = models.ManyToManyField(TestModel, related_name='m2m')
    o2o = models.OneToOneField(TestModel, on_delete=models.CASCADE, related_name='o2o')
