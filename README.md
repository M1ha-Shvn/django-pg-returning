# django-pg-returning
A small library implementing PostgreSQL ability to return rows in DML statements for Django.  
[Link to PostgreSQL docs](https://www.postgresql.org/docs/10/static/sql-update.html)

## <a name="requirements">Requirements</a>
* Python Python 3.5+
 Previous versions may also work, but are not tested with CI  
* django >= 1.8  
  Previous versions may also work, but are not tested with CI.   
  bulk_create_returning method doesn't support .only() and .defer() filters for django before 1.10.
* psycopg2-binary
* typing for python < 3.5
* PostgreSQL 9.4+   
  Previous versions may also work, but are not tested with CI.  

## <a name="installation">Installation</a>
Install via pip:  
`pip install django-pg-returning`    
or via setup.py:  
`python setup.py install`

## <a name="usage">Usage</a>

### <a name="integration">Integration</a>
The easiest way to integrate, is to inherit your model from `UpdateReturningModel` instead of `django.db.models.Model`.
It already has redeclared Manager, supporting returning operations.
```python
from django.db import models
from django_pg_returning import UpdateReturningModel

class MyModel(UpdateReturningModel):   
    field = models.IntegerField()
```

If you already have custom manager, you can implement `get_queryset()` method in it:
```python
from django.db import models
from django_pg_returning import UpdateReturningQuerySet, UpdateReturningModel

class MyManager(models.Manager):
    def get_queryset(self):
        return UpdateReturningQuerySet(using=self.db, model=self.model)

class MyModel(UpdateReturningModel):
    objects = MyManager()
    
    field = models.IntegerField()
```

And if you have custom manager you can use a mixin:
```python
from django.db import models
from django_pg_returning import UpdateReturningMixin, UpdateReturningModel

class MyQuerySet(models.QuerySet, UpdateReturningMixin):
    pass

class MyManager(models.Manager):
    def get_queryset(self):
        return MyQuerySet(using=self.db, model=self.model)

class MyModel(UpdateReturningModel):
    objects = MyManager()
    
    field = models.IntegerField()
```

### <a name="methods">Methods</a>
#### <a name="queryset_methods">QuerySet methods</a>
After QuerySet mixin is integrated with your model, your QuerySet-s will have 3 additional methods:
```python
from django.db.models import Value

# Any django queryset you like
qs = MyModel.objects.all()

# Update and return a ReturningQuerySet, described below
result = qs.update_returning(field=1)

# Delete data and return a ReturningQuerySet, described below
result = qs.delete_returning()

# Acts like django's QuerySet.create() method, but updates all model fields to values stored in database
# Can be used to retrieve values, saved by database default/triggers etc.
result = MyModel.objects.create_returning(field=Value(1) + Value(2))
print(result.field)  # prints: "3" instead of "Value(1) + Value(2)"

# Acts like django's QuerySet.bulk_create() method, but updates all model fields to values stored in database
# Can be used to retrieve values, saved by database default/triggers etc.
result = MyModel.objects.bulk_create_returning([MyModel(field=Value(1) + Value(2))])
print(result[0].field)  # prints: "3" instead of "Value(1) + Value(2)"
```
By default methods get all fields, fetched by the model. 
To limit fields returned, you can use standard 
[QuerySet.only()](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#django.db.models.query.QuerySet.only) 
and 
[QuerySet.defer()](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#defer) methods.  
`create_returning` doesn't support these methods.  
`bulk_create_returning` doesn't support these methods for django before 1.10.  


#### <a name="model_methods">Model methods</a>
If model instance is created, basic `save()` method is called.  
If model is updated, database record is updated, and saved fields are refreshed with database values.
This may be useful, if you update fields with [F() expressions](https://docs.djangoproject.com/en/2.1/ref/models/expressions/#f-expressions).
By default all fields are saved and refreshed. 
Use [update_fields](https://docs.djangoproject.com/en/2.1/ref/models/instances/#specifying-which-fields-to-save) to specify concrete fields to save and refresh.
```python
from django.db.models import Value, F

instance = MyModel(pk=1, field=Value(1))
instance.save_returning()
print(instance.field)
# Output: 2 
# if basic save() called: F('field') + Value(1)

instance.field = F('field') + 1

# Basic save method will not change field and you don't know, what value is in database
instance.save()
print(instance.field)
# Output: F('field') + Value(1)

# Library method gives ability to fetch updated result 
instance.save_returning()
print(instance.field)
# Output: 2
```

*Important notes*:
1) If you don't fetch field, and then try to get it, 
library acts as django does - makes extra database query to fetch attribute deferred.  
2) These queries are not lazy, as well as basic 
[QuerySet.update()](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#update) 
and 
[QuerySet.delete()](https://docs.djangoproject.com/en/2.0/ref/models/querysets/#delete) 
methods.  
3) Primary key field is fetched not looking at limiting methods, as django needs it to form a QuerySet

### <a name="returning_queryset">ReturningQuerySet</a>
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

# Sintax sugar for indexing
print(result.first(), result.last())
# Output: MyModel(...), MyModel(...)

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
