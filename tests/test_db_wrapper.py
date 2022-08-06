from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

import mysql.connector
from db_wrapper import DBHandle

MOCK_CONFIG = {
    "host": "mock_host",
    "user": "mock_user",
    "password": "mock_password",
    "database": "mock_database",
}


def test_db_handle_init():
    dbh = DBHandle(MOCK_CONFIG)
    assert dbh.config == MOCK_CONFIG


@patch("db_wrapper.mysql.connector.connect", autospec=True)
def test_db_handle_connect(mock_connect):
    dbh = DBHandle(MOCK_CONFIG)
    dbh.connect()
    mock_connect.assert_called_once_with(
        host=MOCK_CONFIG["host"],
        user=MOCK_CONFIG["user"],
        password=MOCK_CONFIG["password"],
        database=MOCK_CONFIG["database"],
    )
    mock_connect.return_value.cursor.assert_called_once_with()


def test_query_all_media():
    dbh = DBHandle(MOCK_CONFIG)
    dbh.cursor = Mock(mysql.connector.connection_cext.CMySQLCursor)
    dbh.cursor.fetchall = Mock(autospec=True, return_value=[
        ("2022/08/mock.png", 11),
        ("2022/08/mock-1.png", 12),
        ("1999/12/amock.png", 13),
    ])
    original_filenames = dbh.query_all_media()
    dbh.cursor.execute.assert_called_once_with(
        "SELECT meta_value, post_id FROM wp_postmeta WHERE meta_key = '_wp_attached_file'"
    )
    dbh.cursor.fetchall.assert_called_once_with()
    assert original_filenames == {
        "2022/08/mock.png": 11,
        "2022/08/mock-1.png": 12,
        "1999/12/amock.png": 13,
    }


@patch("db_wrapper.cmn.php_unserialize_to_dict", autospec=True,
       side_effect=[sentinel.unsrlzd_1, sentinel.unsrlzd_2])
def test_query_media_metadata(mock_unserialize):
    dbh = DBHandle(MOCK_CONFIG)
    dbh.cursor = Mock(mysql.connector.connection_cext.CMySQLCursor)
    dbh.cursor.fetchall = Mock(autospec=True, return_value=[
        (16, sentinel.serialized1),
        (18, sentinel.serialized2),
    ])
    metadata = dbh.query_media_metadata()
    dbh.cursor.execute.assert_called_once_with(
        "SELECT meta_id, meta_value FROM wp_postmeta WHERE meta_key = '_wp_attachment_metadata'"
    )
    dbh.cursor.fetchall.assert_called_once_with()
    mock_unserialize.assert_has_calls([
        call(sentinel.serialized1),
        call(sentinel.serialized2)
    ])
    assert metadata == [
        (16, sentinel.unsrlzd_1),
        (18, sentinel.unsrlzd_2),
    ]


@patch("db_wrapper.cmn.php_serialize_from_dict", autospec=True,
       return_value='"sentinel.srlzd";s:8:"filesize";i:7345;')
def test_update_metadata(mock_serialize):
    dbh = DBHandle(MOCK_CONFIG)
    dbh.cursor = Mock(mysql.connector.connection_cext.CMySQLCursor)
    sentidict = {
        "sentinel": "but dict"
    }
    metadata = dbh.update_metadata(42, sentidict)
    dbh.cursor.execute.assert_called_once_with(
        "UPDATE wp_postmeta SET meta_value = '{}' WHERE meta_id = {}".format(
                mock_serialize.return_value, 42))

