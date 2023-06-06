SQLAlchemy-Nested-Mutable
=========================

```shell
pip install sqlalchemy-nested-mutable
```

An advanced SQLAlchemy column type factory that helps map complex Python types (e.g. List, Dict, Pydantic Model and their hybrids) to database types (e.g. ARRAY, JSONB),
And keep track of mutations in deeply nested data structures so that SQLAlchemy can emit proper UPDATE statements.

SQLAlchemy-Nested-Mutable is highly inspired by SQLAlchemy-JSON <sup>[[0]](https://github.com/edelooff/sqlalchemy-json)</sup><sup>[[1]](https://variable-scope.com/posts/mutation-tracking-in-nested-json-structures-using-sqlalchemy)</sup>. However, it does not limit the mapped Python types to dict-like objects.

Documentation is not ready yet. Please refer to these test files for usage:

* test_mutable_list.py
* test_mutable_dict.py
* test_mutable_pydantic_type.py
