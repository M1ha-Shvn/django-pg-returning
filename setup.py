from setuptools import setup

requires = []
with open('requirements.txt') as f:
    for line in f.readlines():
        line = line.strip()  # Remove spaces
        line = line.split('#')[0]  # Remove comments
        if line:  # Remove empty lines
            requires.append(line)

setup(
    name='django-pg-returning',
    version='1.0.0',
    packages=['django_pg_returning'],
    package_dir={'': 'src'},
    url='https://github.com/M1hacka/django-pg-returning',
    license='BSD 3-clause "New" or "Revised" License',
    author='Mikhail Shvein',
    author_email='work_shvein_mihail@mail.ru',
    description='A small library implementing PostgreSQL ability to return rows in DML statements for Django',
    requires=requires
)
