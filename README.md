# django-pg-returning
A small library implementing PostgreSQL ability to return rows in DML statements for Django.  
[Link to PostgreSQL docs](https://www.postgresql.org/docs/10/static/sql-update.html)

## Requirements
* Python 2.7 or Python 3.3+
* django >= 1.7  
  Previous versions may also work, but haven't been tested.  
* pytz
* six
* typing
* psycopg2
* PostgreSQL 9.2+   
  Previous versions may also work, but haven't been tested.  

## Installation
Install via pip:  
`pip install django-pg-returning`    
or via setup.py:  
`python setup.py install`

## Usage

### Integration
To use library [QuerySet](https://docs.djangoproject.com/en/2.0/ref/models/querysets/) methods,
 just add UpdateReturningManager to your model:
```python
from django.db import models
from django_pg_returning import UpdateReturningManager

class MyModel(models.Model):
    objects = UpdateReturningManager()
    
    field = models.IntegerField()
```

If you already have custom manager, you can implement get_queryset() method in it:
```python
from django.db import models
from django_pg_returning import UpdateReturningQuerySet

class MyManager(models.Manager):
    def get_queryset(self):
        return UpdateReturningQuerySet(using=self.db, model=self.model)

class MyModel(models.Model):
    objects = MyManager()
    
    field = models.IntegerField()
```

And if you have custom manager you can use a mixin:
```python
from django.db import models
from django_pg_returning import UpdateReturningMixin

class MyQuerySet(models.QuerySet, UpdateReturningMixin):
    pass

class MyManager(models.Manager):
    def get_queryset(self):
        return MyQuerySet(using=self.db, model=self.model)

class MyModel(models.Model):
    objects = MyManager()
    
    field = models.IntegerField()
```

### Methods
After mixin is integrated with model, your QuerySet-s will have 2 additional methods:
```python
# Any django queryset you like
qs = MyModel.objects.all()

# Update and return a ReturningQuerySet, described below
result = qs.update_returning(field=1)

# Delete data and return a ReturningQuerySet, described below
result = qs.update_returning(field=1)
```
By default methods get all fields, fetched by the model. 
To limit fields returned, you can use standard 
[QuerySet.only()](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#django.db.models.query.QuerySet.only) 
and 
[QuerySet.defer()](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#defer) methods.

*Important notes*:
1) If you don't fetch field, and then try to get it, 
library acts as django does - makes extra database query to fetch attribute deferred.  
2) These queries are not lazy, as well as basic 
[QuerySet.update()](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#update) 
and 
[QuerySet.delete()](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#delete) 
methods.  
3) Primary key field is fetched not looking at limiting methods, as django needs it to form a QuerySet

### ReturningQuerySet
The result of returning functions is django_pg_returning.ReturningQuerySet. 
It is based on django's RawQuerySet, but adds some extra methods to be used easier.
The main difference is that *ReturningQuerySet caches query results*,
 while RawQuerySet executes query each time it is iterated.
All ReturningQuerySet methods are not executed on database side, they are executed in python on cached result.
The only way, ReturningQuerySet makes extra database query - is deferred field loading, described above.
Implemented methods:
```python
# UPDATE ... RETURNING query is executed here once. The result is cached.
result = MyModel.objects.all().update_returning(field=1)

# Get number of values fetched
print(result.count(), len(result))
# Output: 1, 1

# Index and slicing. Note that the order of result is not guaranteed by the database.
print(result[1], result[0:2])
# Output: MyModel(...), [MyModel(...), MyModel(...), MyModel(...)]

# Fetching values and values_list. Both methods use cache and return lists, not ValuesQuerySet like django does.
# values() method cakked without fields will return all fields, fetched in returning method.
# values_list() method called without fields will raise exception, as order or fields in result tuple is not obvious.

print(result.values())
# Output: [{'id': 1, 'field': 1}, {'id': 2, 'field': 2}]

print(result.values('field'))
# Output: [{'field': 1}, {'field': 2}]

print(result.values_list('field', flat=True))
# Output: [1, 2]

print(result.values_list('field', 'id', named=True))
# Output: [Row(field=1, id=1), Row(field=2, id=2)]
```
