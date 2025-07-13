import pyarrow as pa

from pypaimon.api import Schema
from pypaimon.api.catalog_factory import CatalogFactory

if __name__ == '__main__':

    catalog = CatalogFactory.create({
        "warehouse": "/tmp/paimon/warehouse"
    })

    catalog.create_database("test_db", True)

    simple_pa_schema = pa.schema([
            ('f0', pa.int32()),
            ('f1', pa.string()),
            ('f2', pa.string())
        ])
    catalog.create_table("test_db.native_write", Schema(simple_pa_schema, options={}), False)

    table = catalog.get_table("test_db.native_write")

    write_builder = table.new_batch_write_builder()
    table_write = write_builder.new_write()
    table_commit = write_builder.new_commit()

    data = {
        'f0': [1, 2, 3],
        'f1': ['a', 'b', 'c'],
        'f2': ['X', 'Y', 'Z']
    }
    pa_table = pa.Table.from_pydict(data, schema=simple_pa_schema)
    table_write.write_arrow(pa_table)

    commit_messages = table_write.prepare_commit()
    table_commit.commit(commit_messages)

    table_write.close()
    table_commit.close()
