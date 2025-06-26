import os
import pyarrow as pa
from pypaimon import Schema, Catalog

if 'HADOOP_HOME' not in os.environ:
    raise RuntimeError("环境变量 HADOOD_HOME 未设置！")

if 'HADOOP_CONF_DIR' not in os.environ:
    raise RuntimeError("环境变量 HADOOP_CONF_DIR 未设置！")

os.environ['HADOOP_USER_NAME'] = 'hadoop'

schema = Schema(
    pa.schema([
        ('user_id', pa.int32(), False),
        ('item_id', pa.int32()),
        ('behavior', pa.string()),
        ('dt', pa.string(), False)
    ]),
    partition_keys=['dt'],
    primary_keys=['dt', 'user_id'],
    options={
        'bucket': '2'
    })

catalog = Catalog.create({
    'warehouse': 'hdfs://xx.xxx.xxx.x:9000/tmp/paimon'
})
table = catalog.get_table('test_db.user_behavior')
read_builder = table.new_read_builder()
table_read = read_builder.new_read()
splits = read_builder.new_scan().plan().splits()
result = table_read.to_arrow(splits)
print(result)
