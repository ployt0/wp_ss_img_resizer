from unittest.mock import patch, sentinel, Mock, mock_open, call

import pytest

from optimiser import process_args, _magick_on_img, ChangeManager, _get_recorded_mtimes, _save_recorded_mtimes, NV_RECORD_PATH


def test_parse_args_for_monitoring_help():
    with pytest.raises(SystemExit):
        process_args(["-h"])


@patch("optimiser.ChangeManager", autospec=True)
def test_parse_args(mock_change_mngr):
    MOCK_ARGS_LIST = ["-c", "top_secret_conf.json"]
    process_args(MOCK_ARGS_LIST)
    mock_change_mngr.assert_called_once_with(MOCK_ARGS_LIST[1])
    # Maybe why colleagues dislike context managers is that they don't
    # test logically.
    mock_change_mngr.return_value.__enter__.return_value.check_all_uploads.assert_called_once_with()
    mock_change_mngr.return_value.__enter__.assert_called_once_with()


@patch("optimiser.cmn.split_fstring_not_args", autospec=True)
@patch("optimiser.cmn.run_shell_cmd", autospec=True)
@patch("optimiser.cmn.get_file_size", autospec=True, side_effect=[50, 50])
def test_magick_on_img_no_change(mock_get_file_size, mock_run_shell, mock_split_not_args):
    final_destination = "/blah/prefix/blah/dest_img_value.decoration"
    f_str_vars = {
        "dest_img": final_destination
    }
    mock_cmd = "sub me a {6inchsub} for a {footlong}"
    assert not _magick_on_img(f_str_vars, mock_cmd)
    tmp_name = "/tmp/staged_dest_img_value.decoration"
    assert f_str_vars["dest_img"] == tmp_name
    mock_split_not_args.assert_called_once_with(f_str_vars, mock_cmd)
    mock_get_file_size.assert_has_calls([
        call(final_destination),
        call(tmp_name)
    ])
    mock_run_shell.assert_has_calls([
        call(mock_split_not_args.return_value),
        call(["rm", tmp_name])
    ])


@patch("optimiser.DBHandle", autospec=True)
@patch("optimiser.ChangeManager.validate_config",
       return_value={
           "wp_server": {
               "wp_uploads": sentinel.uploads_dir
           },
           "sql": sentinel.sql,
       })
def test_change_manager(mock_validate, mock_db_handle):
    optimiser = ChangeManager(sentinel.conf_location)
    assert optimiser.config == {
               "wp_uploads": sentinel.uploads_dir
           }
    assert optimiser.root_dir == sentinel.uploads_dir
    assert optimiser.db == mock_db_handle.return_value
    mock_db_handle.assert_called_once_with(sentinel.sql)
    mock_validate.assert_called_once_with(sentinel.conf_location)


@patch("optimiser.json.load", autospec=True, return_value={
    "wp_server": {"wp_uploads": sentinel.uploads_dir}})
@patch("optimiser.os.path.exists", autospec=True, return_value=True)
def test_validate_config(mock_exists, mock_json_load):
    fake_instance = Mock()
    with patch("builtins.open") as mocked_open:
        config = ChangeManager.validate_config(fake_instance, sentinel.location)
    mock_exists.assert_called_once_with(sentinel.uploads_dir)
    mocked_open.assert_called_once_with(sentinel.location)
    mock_json_load.assert_called_once_with(mocked_open.return_value.__enter__.return_value)
    assert config == mock_json_load.return_value


@patch("optimiser.json.load", autospec=True, return_value={
    "wp_server": {"wp_uploads": sentinel.uploads_dir}})
@patch("optimiser.os.path.exists", autospec=True, return_value=False)
@patch("optimiser.Path", autospec=True)
def test_validate_config_missing(mock_path, mock_exists, mock_json_load):
    mock_path.return_value.resolve = Mock(return_value="mock_fullpath")
    fake_instance = Mock()
    with pytest.raises(FileNotFoundError) as fnferr:
        with patch("builtins.open") as mocked_open:
            ChangeManager.validate_config(fake_instance, sentinel.location)
        assert "mock_fullpath" in fnferr
    mock_exists.assert_called_once_with(sentinel.uploads_dir)
    mocked_open.assert_called_once_with(sentinel.location)
    mock_json_load.assert_called_once_with(mocked_open.return_value.__enter__.return_value)


def test_get_q_webp():
    fake_instance = Mock()
    fake_instance.config = {
        "webp_mp_to_max_q": {
            0: 60,
            1: 40,
            2: 20
        }
    }
    assert ChangeManager.get_q(fake_instance, "webp", 3) == 20
    assert ChangeManager.get_q(fake_instance, "webp", 2.1) == 20
    assert ChangeManager.get_q(fake_instance, "webp", 2) == 20
    assert ChangeManager.get_q(fake_instance, "webp", 1.9) == 40
    assert ChangeManager.get_q(fake_instance, "webp", 1) == 40
    assert ChangeManager.get_q(fake_instance, "webp", 0.9) == 60


def test_get_q_png():
    fake_instance = Mock()
    fake_instance.config = {
        "png_q": 50
    }
    for i in range (30):
        assert ChangeManager.get_q(fake_instance, "png", i/10) == 50


@patch("optimiser.cmn.get_file_group", autospec=True, return_value="mock_group")
@patch("optimiser.cmn.get_file_owner", autospec=True, return_value="mock_owner")
@patch("optimiser.cmn.split_fstring_not_args", autospec=True)
@patch("optimiser.cmn.run_shell_cmd", autospec=True)
@patch("optimiser.cmn.get_file_size", autospec=True, side_effect=[150, 50])
def test_magick_on_img_replacing(mock_get_file_size, mock_run_shell, mock_split_not_args, mock_get_owner, mock_get_group):
    final_destination = "/blah/prefix/blah/dest_img_value.decoration"
    f_str_vars = {
        "dest_img": final_destination
    }
    mock_cmd = "sub me a {6inchsub} for a {footlong}"
    assert _magick_on_img(f_str_vars, mock_cmd)
    tmp_name = "/tmp/staged_dest_img_value.decoration"
    assert f_str_vars["dest_img"] == tmp_name
    mock_split_not_args.assert_called_once_with(f_str_vars, mock_cmd)
    mock_get_file_size.assert_has_calls([
        call(final_destination),
        call(tmp_name)
    ])
    mock_run_shell.assert_has_calls([
        call(mock_split_not_args.return_value),
        call(["sudo", "mv", tmp_name, final_destination]),
        call(["sudo", "chown", "mock_owner:mock_group", final_destination]),
    ])


@patch("optimiser.os.path.exists", autospec=True, return_value=True)
def test_get_recorded_mtimes(mock_exists):
    with patch("builtins.open", mock_open(read_data="path1,384.31\nroot1/path1/file1,41.949\n")) as mocked_open:
        inode_last_mstats = _get_recorded_mtimes()
    mock_exists.assert_called_once_with(NV_RECORD_PATH)
    mocked_open.assert_called_once_with(NV_RECORD_PATH, "r", newline='')
    assert inode_last_mstats["path1"] == 384.31
    assert inode_last_mstats["root1/path1/file1"] == 41.949


@patch("optimiser.csv.writer", autospec=True)
def test_record_mstats(mock_csv_out):
    mocked_mstats = {
        "path1": 384.31,
        "root1/path1/file1": 41.949,
    }
    with patch("builtins.open", mock_open()) as mocked_open:
        _save_recorded_mtimes(mocked_mstats)
    mocked_open.assert_called_once_with(NV_RECORD_PATH, "w", newline='')
    mock_csv_out.assert_called_once_with(mocked_open.return_value)
    mock_csv_out.return_value.writerow.assert_has_calls([call([x, y]) for x,y in mocked_mstats.items()])



