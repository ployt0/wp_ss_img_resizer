import subprocess
from typing import List, Dict, Any

from phpserialize import phpobject, unserialize, serialize


def run_shell_cmd(cmd: List[str]) -> str:
    result = subprocess.run(cmd, capture_output=True)
    result_text = None
    if result.returncode == 0:
        result_text = result.stdout.decode()
    return result_text


def get_file_size(file_name: str) -> int:
    return int(run_shell_cmd(['stat', '-c' '%s', file_name]))


def get_file_owner(file_name: str) -> str:
    return run_shell_cmd(['stat', '-c' '%U', file_name]).strip()


def get_file_group(file_name: str) -> str:
    return run_shell_cmd(['stat', '-c' '%G', file_name]).strip()


def get_img_wxh(file_name: str) -> List[int]:
    result_text = run_shell_cmd(['identify', '-ping', '-format', '"%wx%h"', file_name])
    return list(map(int, result_text.strip("\"").split("x")))


def split_fstring_not_args(f_str_vars: Dict[str, Any], in_fstr: str) -> List[str]:
    """
    Formats an fstring and splits on space. The spaces in any of arguments
    are however preserved.

    subprocess.run likes the split string format best.

    :param f_str_vars: dictionary of arguments to the f string.
    :param cmd: the command including f-string place holders.
    :return: list of input tokens.
    """
    curlied_dict = {"{" + k + "}": str(v) for k,v in f_str_vars.items()}
    rebuilt_cmd = []
    for token in in_fstr.split():
        for k, v in curlied_dict.items():
            token = token.replace(k, v)
        rebuilt_cmd.append(token)
    return rebuilt_cmd


def get_name_decor(w: int, h: int, ext: str):
    return '-{}x{}.{}'.format(w, h, ext)


def php_unserialize_to_dict(serialized: str) -> dict:
    byte_dict = unserialize(bytes(serialized, 'utf-8'), object_hook=phpobject)
    return decode_dict(byte_dict)


def decode_dict(byte_dict):
    py_dict = {}
    for k, v in byte_dict.items():
        if isinstance(v, bytes):
            v = v.decode()
        elif isinstance(v, dict):
            v = decode_dict(v)
        py_dict[k.decode()] = v
    return py_dict


def php_serialize_from_dict(src_dict: dict) -> str:
    return serialize(src_dict).decode()



