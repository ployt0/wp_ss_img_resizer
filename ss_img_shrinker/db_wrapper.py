from typing import List, Tuple, Any, Dict, Optional, Callable

import mysql.connector

import common_funcs as cmn


class DBHandle:
    def __init__(self, config: dict):
        self.cnxn = None
        self.cursor = None
        self.config = config

    def connect(self):
        self.cnxn = mysql.connector.connect(
            host=self.config["host"],
            user=self.config["user"],
            password=self.config["password"],
            database=self.config["database"],
        )
        self.cursor = self.cnxn.cursor()

    def query_all_media(self) -> Dict[str, int]:
        self.cursor.execute(
            "SELECT * FROM wp_postmeta WHERE meta_key = '_wp_attached_file'")
        results = self.cursor.fetchall()
        original_filenames = {x[3]: x[1] for x in results}
        return original_filenames

    def query_media_metadata(self) -> List[Tuple[int, Dict]]:
        """Returns a list of 2-tuples of the meta_id and meta_value."""
        self.cursor.execute(
            "SELECT * FROM wp_postmeta WHERE meta_key = '_wp_attachment_metadata'")
        results = self.cursor.fetchall()
        metadata = [(x[0], cmn.php_unserialize_to_dict(x[3])) for x in results]
        return metadata

    def update_metadata(self, post_meta_id, metadata: dict):
        serialized = cmn.php_serialize_from_dict(metadata)
        self.cursor.execute(
            "UPDATE wp_postmeta SET meta_value = '{}' WHERE meta_id = {}".format(
                serialized, post_meta_id
            ))

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.cnxn:
            self.cnxn.close()


