import django


def chain_query(qs, query_type=None):
    """
    In django 2 query.clone() method in update was replaced with chain method
    """
    args = (query_type,) if query_type else ()
    if django.VERSION >= (2,):
        return qs.query.chain(*args)
    else:
        return qs.query.clone(*args)
