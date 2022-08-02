from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from common_funcs import run_shell_cmd, get_file_size, get_img_wxh, \
    get_name_decor, split_fstring_not_args, php_unserialize_to_dict, \
    php_serialize_from_dict


def test_run_shell_cmd():
    result_text = run_shell_cmd(['stat', '-c' '%s %n', "white_100x100.png"])
    assert result_text.strip() == '694 white_100x100.png'


def test_get_file_size():
    assert get_file_size("white_100x100.png") == 694


def test_get_img_wxh():
    wxh = get_img_wxh("white_100x100.png")
    assert wxh == [100, 100]


def test_get_name_decor():
    decor = get_name_decor(640, 480, "xzmp")
    assert decor == "-640x480.xzmp"


def test_split_fstring_not_args():
    in_fstr = "split into words {except_where} we are substituting {var1} " \
              "fstrings. {snippet1}."
    f_str_vars = {
        "except_where": "except where",
        "var1": "for",
        "snippet1": "Here's another preserved bit"
    }
    results = split_fstring_not_args(f_str_vars, in_fstr)
    assert results == [
        "split", "into", "words", "except where", "we", "are", "substituting",
        "for", "fstrings.", "Here's another preserved bit."]


PY_IMG_META = {"image_meta": {
    "aperture": "0", "credit": "", "camera": "", "caption": "",
    "created_timestamp": "0", "copyright": "", "focal_length": "0",
    "iso": "0", "shutter_speed": "0", "title": "", "orientation": "0",
    "keywords": {}}}


PHP_IMG_META = 'a:1:{s:10:"image_meta";a:12:{s:8:"aperture";s:1:"0";' \
               's:6:"credit";s:0:"";s:6:"camera";s:0:"";s:7:"caption";' \
               's:0:"";s:17:"created_timestamp";s:1:"0";s:9:"copyright";' \
               's:0:"";s:12:"focal_length";s:1:"0";s:3:"iso";s:1:"0";' \
               's:13:"shutter_speed";s:1:"0";s:5:"title";s:0:"";' \
               's:11:"orientation";s:1:"0";s:8:"keywords";a:0:{}}}'


PHP_META_NEST = \
    'a:5:{s:5:"width";i:1080;s:6:"height";i:424;s:4:"file";s:43:' \
    '"2022/08/testing-how-it-looked-installed.png";s:8:"filesize";i:7345;' \
    's:5:"sizes";a:4:{s:6:"medium";a:5:{s:4:"file";s:43:' \
    '"testing-how-it-looked-installed-300x118.png";s:5:"width";i:300;' \
    's:6:"height";i:118;s:9:"mime-type";s:9:"image/png";s:8:"filesize";' \
    'i:10938;}s:5:"large";a:5:{s:4:"file";s:44:' \
    '"testing-how-it-looked-installed-1024x402.png";s:5:"width";i:1024;' \
    's:6:"height";i:402;s:9:"mime-type";s:9:"image/png";s:8:"filesize";' \
    'i:53945;}s:9:"thumbnail";a:5:{s:4:"file";s:43:' \
    '"testing-how-it-looked-installed-150x150.png";s:5:"width";i:150;' \
    's:6:"height";i:150;s:9:"mime-type";s:9:"image/png";s:8:"filesize";' \
    'i:7168;}s:12:"medium_large";a:5:{s:4:"file";' \
    's:43:"testing-how-it-looked-installed-768x302.png";s:5:"width";i:768;' \
    's:6:"height";i:302;s:9:"mime-type";s:9:"image/png";s:8:"filesize";' \
    'i:39396;}}}'


PY_META_NEST = {
    'width': 1080, 'height': 424,
    'file': '2022/08/testing-how-it-looked-installed.png', 'filesize': 7345,
    'sizes': {
        'medium': {'file': 'testing-how-it-looked-installed-300x118.png',
                   'width': 300, 'height': 118, 'mime-type': 'image/png',
                   'filesize': 10938},
        'large': {'file': 'testing-how-it-looked-installed-1024x402.png',
                  'width': 1024, 'height': 402, 'mime-type': 'image/png',
                  'filesize': 53945},
        'thumbnail': {'file': 'testing-how-it-looked-installed-150x150.png',
                      'width': 150, 'height': 150, 'mime-type': 'image/png',
                      'filesize': 7168}, 'medium_large': {
            'file': 'testing-how-it-looked-installed-768x302.png',
            'width': 768, 'height': 302, 'mime-type': 'image/png',
            'filesize': 39396}}}


def test_php_unserialize_to_dict():
    pydict_vers = php_unserialize_to_dict(PHP_IMG_META)
    assert pydict_vers == PY_IMG_META


def test_php_unserialize_to_nested_dict():
    pydict_vers = php_unserialize_to_dict(PHP_META_NEST)
    assert pydict_vers == PY_META_NEST


def test_php_serialize_from_dict():
    pydict_vers = php_serialize_from_dict(PY_IMG_META)
    assert pydict_vers == PHP_IMG_META

