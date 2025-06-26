################################################################################
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
# limitations under the License.
################################################################################
import os
import subprocess
from typing import Optional, List
from urllib.parse import urlparse, splitport

import pyarrow.dataset as ds
from pyarrow import fs

from pypaimon import Predicate
from pypaimon.pynative.common.row.internal_row import InternalRow
from pypaimon.pynative.reader.core.columnar_row_iterator import ColumnarRowIterator
from pypaimon.pynative.reader.core.file_record_iterator import FileRecordIterator
from pypaimon.pynative.reader.core.file_record_reader import FileRecordReader
from pypaimon.pynative.util.predicate_converter import convert_predicate


class PyArrowDatasetReader(FileRecordReader[InternalRow]):
    """
    A PyArrowDatasetReader that reads data from a dataset file using PyArrow,
    and filters it based on the provided predicate and projection.
    """

    def __init__(self, format, file_path, batch_size, projection,
                 predicate: Predicate, primary_keys: List[str], fields: List[str]):

        if primary_keys is not None:
            # TODO: utilize predicate to improve performance
            predicate = None

        if predicate is not None:
            predicate = convert_predicate(predicate)

        scheme, netloc, path = self.parse_location(str(file_path))
        if scheme in {"hdfs", "viewfs"}:
            self._file_path = path
            self._filesystem = self._initialize_hdfs_fs(scheme, netloc)
        elif scheme in {"file"}:
            self._file_path = path
            self._filesystem = fs.LocalFileSystem()
        else:
            raise ValueError(f"Unrecognized filesystem type in URI: {scheme}")

        self.dataset = ds.dataset(self._file_path, format=format, filesystem=self._filesystem)
        self.scanner = self.dataset.scanner(
            columns=fields,
            filter=predicate,
            batch_size=batch_size
        )
        self.batch_iterator = self.scanner.to_batches()

    def read_batch(self) -> Optional[FileRecordIterator[InternalRow]]:
        try:
            record_batch = next(self.batch_iterator, None)
            if record_batch is None:
                return None

            return ColumnarRowIterator(
                self._file_path,
                record_batch
            )
        except Exception as e:
            print(f"Error reading batch: {e}")
            raise

    def close(self):
        pass

    def _initialize_hdfs_fs(self, scheme, netloc):
        if 'HADOOP_HOME' not in os.environ:
            raise RuntimeError("HADOOP_HOME environment variable is not set.")

        if 'HADOOP_CONF_DIR' not in os.environ:
            raise RuntimeError("HADOOP_CONF_DIR environment variable is not set.")

        hadoop_home = os.environ.get("HADOOP_HOME")
        native_lib_path = f"{hadoop_home}/lib/native"
        os.environ['LD_LIBRARY_PATH'] = f"{native_lib_path}:{os.environ.get('LD_LIBRARY_PATH', '')}"

        class_paths = subprocess.run(
            [f'{hadoop_home}/bin/hadoop', 'classpath', '--glob'],
            capture_output=True,
            text=True,
            check=True
        )
        os.environ['CLASSPATH'] = class_paths.stdout.strip()

        host, port_str = splitport(netloc)
        return fs.HadoopFileSystem(
            host=host,
            port=int(port_str),
            user=os.environ.get('HADOOP_USER_NAME', 'hadoop')
        )

    @staticmethod
    def parse_location(location: str):
        uri = urlparse(location)
        if not uri.scheme:
            return "file", uri.netloc, os.path.abspath(location)
        elif uri.scheme in ("hdfs", "viewfs"):
            return uri.scheme, uri.netloc, uri.path
        else:
            return uri.scheme, uri.netloc, f"{uri.netloc}{uri.path}"
