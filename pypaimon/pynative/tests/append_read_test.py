import time

import pyarrow as pa

from pypaimon.api.catalog_factory import CatalogFactory

if __name__ == '__main__':

    catalog = CatalogFactory.create({
        "warehouse": "/tmp/paimon/warehouse"
    })

    table = catalog.get_table("test_db.native_write")

    read_builder = table.new_read_builder()
    # read_builder.with_filter(read_builder.new_predicate_builder().equal('dt', '20'))
    # read_builder.with_projection(['user_id', 'behavior', 'dt'])
    # read_builder.with_limit(30)
    table_scan = read_builder.new_scan()
    table_read = read_builder.new_read()
    splits = table_scan.plan().splits()


    start = time.time()

    record_iter = table_read.to_iterator(splits)

    count = 0
    value = 0
    for record in record_iter:
        print(record)
        count += 1
        value += len(record)

    print(count)
    print(value)

    # result = table_read.to_arrow(splits)
    # print(len(result))


    end = time.time()
    print(f"cost time: {end - start}")
