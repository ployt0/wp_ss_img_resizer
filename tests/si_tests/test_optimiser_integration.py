import os
from pathlib import Path
from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from optimiser import ChangeManager
from wp_api.api_app import WP_API
import common_funcs as cmn


def setup_module(module):
    wp_api = WP_API()
    # wp_api.delete_all_my("media")


def test_optimiser():
    wp_api = WP_API()
    src_file = "testing-how-it-looked-installed.png"
    response = wp_api.upload_media(src_file)
    response.raise_for_status()
    jresp = response.json()
    full_served_path = "/var/www/html/wp-content/uploads/{}".format(
        jresp["media_details"]["file"])
    original_szs = {v["file"]: v["filesize"]
                    for k,v in jresp["media_details"]["sizes"].items()
                    if k not in ["thumbnail", "full"]}
    uploads_sub = Path(full_served_path).parent.resolve()
    original_mtimes = {f: os.stat(os.path.join(uploads_sub, f)).st_mtime
                       for f in original_szs.keys()}
    response2 = wp_api.get("media/{}".format(jresp["id"]))
    assert response2.ok
    jresp2 = response2.json()
    with ChangeManager("config.json") as optimiser:
        optimiser.check_all_uploads()
    for fl_nm in original_szs.keys():
        assert os.stat(os.path.join(uploads_sub, fl_nm)).st_mtime >\
               original_mtimes[fl_nm]
        assert cmn.get_file_size(os.path.join(uploads_sub, fl_nm)) <\
               original_szs[fl_nm]

    # Checkt that we updated the SQL to include the new sizes and
    # nothing else changed:
    response3 = wp_api.get("media/{}".format(jresp["id"]))
    assert response3.ok
    jresp3 = response3.json()
    new_sizes = {f: cmn.get_file_size(os.path.join(uploads_sub, f))
                 for f in original_szs.keys()}
    for k,v in jresp3["media_details"]["sizes"].items():
        if k not in ["thumbnail", "full"]:
            assert v["filesize"] < \
                   jresp2["media_details"]["sizes"][k]["filesize"]
            assert v["filesize"] == new_sizes[v["file"]]
            jresp2["media_details"]["sizes"][k]["filesize"] = v["filesize"]
    assert jresp3 == jresp2


def teardown_module(module):
    """teardown any state after all tests herein have run."""
    wp_api = WP_API()
    number_needing_deletion, number_after_deletion =\
        wp_api.delete_all_my("media")
    assert number_needing_deletion >= number_after_deletion
    assert number_after_deletion == 0


