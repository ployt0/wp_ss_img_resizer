#!/usr/bin/env python3
"""
Requires a working image magick installation.
I am aware Wand https://docs.wand-py.org/en/0.6.8/ is the python interface
to ImageMagick, but not only does that require ImageMagick, it also
requires ImageMagick-devel, is yet another dependency and obfuscates
the command lines used to prototype/learn the operations performed.
"""
import argparse
import csv
import json
import os
import sys
from typing import List, Tuple, Any, Dict, Optional, Callable

# print(sys.path)

import common_funcs as cmn
from db_wrapper import DBHandle

NV_RECORD_PATH = "latest_mods.csv"


class CompressorException(Exception):
    pass


def _magick_on_img(f_str_vars: dict, command: str) -> Optional[int]:
    """
    Supplied command uses f-string (py 3.6) with lookups from the supplied
    dict. Only the command is split, dict values are not.

    We run to a staging tmp file and only if the result saves space
    do we copy it over the original and return True.
    """
    final_destination = f_str_vars["dest_img"]
    tmp_name = "/tmp/staged_" + os.path.basename(final_destination)
    f_str_vars["dest_img"] = tmp_name
    split_cmd = cmn.split_fstring_not_args(f_str_vars, command)
    cmn.run_shell_cmd(split_cmd)
    existing_size = cmn.get_file_size(final_destination)
    magicked_size = cmn.get_file_size(tmp_name)
    if magicked_size < existing_size:
        owner = cmn.get_file_owner(final_destination)
        group = cmn.get_file_group(final_destination)
        cmn.run_shell_cmd(["sudo", "mv", tmp_name, final_destination])
        cmn.run_shell_cmd(["sudo", "chown", "{}:{}".format(owner, group), final_destination])
        return magicked_size
    cmn.run_shell_cmd(["rm", tmp_name])
    return None


def _get_recorded_mtimes() -> Dict[str, float]:
    inode_last_mtimes = {}
    if os.path.exists(NV_RECORD_PATH):
        with open(NV_RECORD_PATH, "r", newline='') as lmcv:
            for row in csv.reader(lmcv):
                inode_last_mtimes[row[0]] = float(row[1])
    return inode_last_mtimes


def _save_recorded_mtimes(recorded_mtimes: Dict[str, float]) -> None:
    with open(NV_RECORD_PATH, "w", newline='') as lmcv:
        ad_writer = csv.writer(lmcv)
        for fl_nm, last_m in recorded_mtimes.items():
            ad_writer.writerow([fl_nm, last_m])


class ChangeManager:
    def __init__(self, conf_location: str):
        config = self.validate_config(conf_location)
        self.config = config["wp_server"]
        self.root_dir = self.config["wp_uploads"]
        self.db = DBHandle(config["sql"])
        self.noresize_cmds = {
            "png": "convert -strip -colors {q} {src_img} {dest_img}",
            "webp": "convert -strip -define webp:method=6 -quality {q}"
                    " {src_img} {dest_img}"
        }
        self.scaling_cmds = {
            "png": "convert -strip -resize {w}x{h} -colors {q}"
                   " {src_img} {dest_img}",
            "webp": "convert -strip -resize {w}x{h} -define webp:method=6 "
                    "-quality {q} {src_img} {dest_img}"
        }

    def validate_config(self, conf_location: str):
        with open(conf_location) as f:
            config = json.load(f)
        if not os.path.exists(config["wp_server"]["wp_uploads"]):
            from pathlib import Path
            raise FileNotFoundError(
                "\"{}\", from the config at: \"{}\", does not exist.".format(
                    Path(config["wp_server"]["wp_uploads"]).resolve(),
                        Path(conf_location).resolve()))
        return config

    def __enter__(self):
        self.db.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.disconnect()

    def check_all_uploads(self):
        """
        :param img_name: absolute or relative path of source image
        :param conf_file: path to config json with keys "ssh" and "api".
        :return:
        """
        current_img_mtimes = self.stat_all_imgs()
        recorded_mtimes = _get_recorded_mtimes()
        # Capture detected changes in subdirectories, prior to query.
        imgs_facts = self.sequester_data_by_rel_file_paths()
        # This is still a point in time. But at least anything seen on
        # our FS scan is more likely to be there than had we done the
        # file scan later. Our output will update the FS anyway.
        f_str_vars = {
            "q": None,
            "src_img": None,
            "dest_img": None
        }
        any_change = False

        for subfolder, mtimes in current_img_mtimes.items():
            for file_nm, cur_m in mtimes.items():
                rel_path_to_file = os.path.join(subfolder, file_nm)
                img_facts = imgs_facts.get(rel_path_to_file)
                last_m = recorded_mtimes.get(rel_path_to_file)
                if not img_facts or not(last_m is None or last_m < cur_m):
                    # If it isn't a named file, it's a resize, our output.
                    # To proceed we shouldn't have recorded an mtime, or it
                    # is behind that observed.
                    continue
                extension = rel_path_to_file.split(".")[-1]
                megapix = img_facts["megapix"]
                metadata = img_facts["metadata"]

                f_str_vars["src_img"] = os.path.join(
                    self.root_dir, rel_path_to_file)
                f_str_vars["q"] = self.get_q(extension, megapix)
                latest_mtime: float = self.try_improve_downscales(
                    extension, f_str_vars, metadata, subfolder)

                f_str_vars["dest_img"] = f_str_vars["src_img"]
                new_sz = _magick_on_img(
                    f_str_vars, self.noresize_cmds[extension])
                if new_sz is not None:
                    latest_mtime = max(latest_mtime, os.stat(
                        f_str_vars["src_img"]).st_mtime)
                    metadata["filesize"] = new_sz
                if latest_mtime > 0:
                    recorded_mtimes[rel_path_to_file] = latest_mtime
                    any_change = True
                    self.db.update_metadata(img_facts["id"], metadata)

        if any_change:
            self.db.cnxn.commit()
            _save_recorded_mtimes(recorded_mtimes)

    def try_improve_downscales(
            self, extension: str, f_str_vars: dict, metadata: dict,
            subfolder: str) -> float:
        """
        Returns a dict of base file names to their sizes, if reduced.
        """
        latest_mtime = 0
        for label, resize in metadata["sizes"].items():
            if label == "thumbnail":
                continue  # this uses a different algo, and is tiny
            abs_out_name = os.path.join(
                self.root_dir, subfolder, resize["file"])
            f_str_vars["w"] = resize["width"]
            f_str_vars["h"] = resize["height"]
            f_str_vars["dest_img"] = abs_out_name
            new_fl_sz = _magick_on_img(
                f_str_vars, self.scaling_cmds[extension])
            if new_fl_sz is not None:
                metadata["sizes"][label]["filesize"] = new_fl_sz
                latest_mtime = os.stat(abs_out_name).st_mtime
        return latest_mtime

    def sequester_data_by_rel_file_paths(self) -> dict:
        # These file names include only the path after "uploads".
        metadata = self.db.query_media_metadata()
        img_facts = {}
        for media_meta in metadata:
            img_facts[media_meta[1]["file"]] = {
                "metadata": media_meta[1],
                "megapix": media_meta[1]["width"] * media_meta[1]["height"]
                           / 1_000_000,
                "id": media_meta[0]
            }
        return img_facts

    def get_q(self, extension: str, src_mp: float):
        if extension == "png":
            return self.config["png_q"]
        max_q = 10
        for mp, q in sorted(self.config["webp_mp_to_max_q"].items()):
            if float(mp) > src_mp:
                break
            max_q = q
        return max_q

    def stat_all_imgs(self) -> Dict[str, Dict[str, float]]:
        """
        :return: relative directories mapping to maps of leaf file names
            mapping to mtime floats
        """
        img_mtimes = {}
        for folder, _, files in os.walk(self.root_dir):
            if not files:
                continue
            subfolder = folder[len(self.root_dir):]
            img_mtimes[subfolder] = {
                f: os.stat(os.path.join(folder, f)).st_mtime
                for f in files if f.split(".")[-1] in ["png", "webp"]
            }
        return img_mtimes


def process_args(args_list: List[str]):

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Image shrinkage optimisation for WordPress.

Uses config.json:

{
  "sql": {
    "host": "172.17.0.2",
    "user": "wordpressuser232",
    "password": "galoshes",
    "database": "wordpress"
  },
  "wp_server": {
    "wp_uploads": "/var/www/html/wp-content/uploads/",
    "png_q": 32,
    "webp_mp_to_max_q": {
      "0": 70, 
      "1": 60, 
      "2": 50,
      "4": 50
    },
  }
}

"png_q": colour quantisation level.
"webp_mp_to_max_q": Map of MP sizes from which quality is set. These are bottom
bounds, only key "0" is required. Images use the quality of the next key
smaller than their MP.
# "webm_q_upto_2MP": webp quality upto 2MP (FHD).
# "webm_q_over_2MP": webp quality when images over 2MP (FHD).
""")
    parser.add_argument(
        "-c", "--config_file",
        help="Name of json file describing containing WordPress credentials.",
        default="config.json")
    args = parser.parse_args(args_list)
    with ChangeManager(args.config_file) as optimiser:
        optimiser.check_all_uploads()


def main(args_list: List[str]):
    process_args(args_list)


if __name__ == "__main__":
    main(sys.argv[1:])
