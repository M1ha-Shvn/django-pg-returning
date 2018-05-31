"""
This file contains sample models to use in tests
"""
from django.db import models

from django_pg_returning import UpdateReturningManager


class TestModel(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True, default='')
    int_field = models.IntegerField(null=True, blank=True)

    objects = UpdateReturningManager()

