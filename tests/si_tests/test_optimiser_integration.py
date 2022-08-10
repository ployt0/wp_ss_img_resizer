import os
from pathlib import Path
from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from optimiser import ChangeManager
from wp_api.api_app import WP_API
import common_funcs as cmn


def setup_module(module):
    wp_api = WP_API()
    wp_api.delete_all_my("media")


@pytest.mark.parametrize("src_file", [
    ("Dr_IJsbrand_van_Diemerbroeck.png"),
    ("filestats.png"),
    ("grue_en_vol.jpg"),
    ("pierre-lemos-hippo-q90.webp"),
])
def test_optimiser(src_file):
    wp_api = WP_API()
    response = wp_api.upload_media(src_file)
    response.raise_for_status()
    jresp = response.json()
    full_served_path = "/var/www/html/wp-content/uploads/{}".format(
        jresp["media_details"]["file"])
    original_szs = {v["file"]: v["filesize"]
                    for k,v in jresp["media_details"]["sizes"].items()
                    if k not in ["full"]}
    original_szs[os.path.basename(full_served_path)] =\
        jresp["media_details"]["filesize"]
    uploads_sub = Path(full_served_path).parent.resolve()
    original_mtimes = {f: os.stat(os.path.join(uploads_sub, f)).st_mtime
                       for f in original_szs.keys()}
    response2 = wp_api.get("media/{}".format(jresp["id"]))
    assert response2.ok
    jresp2 = response2.json()
    with ChangeManager("config.json") as optimiser:
        optimiser.check_all_uploads()
    for fl_nm in original_szs.keys():
        # This is assuming we shrank *every* scaled copy!
        assert os.stat(os.path.join(uploads_sub, fl_nm)).st_mtime >\
               original_mtimes[fl_nm]
        assert cmn.get_file_size(os.path.join(uploads_sub, fl_nm)) <\
               original_szs[fl_nm]

    response3 = wp_api.get("media/{}".format(jresp["id"]))
    assert response3.ok
    jresp3 = response3.json()
    new_sizes = {f: cmn.get_file_size(os.path.join(uploads_sub, f))
                 for f in original_szs.keys()}
    # Check that we updated the SQL to include the new sizes:
    for k,v in jresp3["media_details"]["sizes"].items():
        if k not in ["full"]:
            assert v["filesize"] < \
                   jresp2["media_details"]["sizes"][k]["filesize"]
            assert v["filesize"] == new_sizes[v["file"]]
            jresp2["media_details"]["sizes"][k]["filesize"] = v["filesize"]

    # Check nothing else changed:
    jresp2["media_details"]["filesize"] = jresp3["media_details"]["filesize"]
    assert jresp3 == jresp2


def teardown_module(module):
    """teardown any state after all tests herein have run."""
    wp_api = WP_API()
    number_needing_deletion, number_after_deletion =\
        wp_api.delete_all_my("media")
    assert number_needing_deletion >= number_after_deletion
    assert number_after_deletion == 0


