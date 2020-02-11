# Copyright 2014-present PlatformIO <contact@platformio.org>
# Copyright 2019-present Nuclei <contact@nucleisys.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os.path import isfile, join
from platform import system

from platformio.managers.platform import PlatformBase


class NucleiPlatform(PlatformBase):
    def get_boards(self, id_=None):
        result = PlatformBase.get_boards(self, id_)
        if not result:
            return result
        if id_:
            return self._add_default_debug_tools(result)
        else:
            for key, value in result.items():
                result[key] = self._add_default_debug_tools(result[key])
        return result

    def _add_default_debug_tools(self, board):
        # debug tools
        debug = board.manifest.get("debug", {})
        build = board.manifest.get("build", {})
        non_ftdi_tools = ["jlink", "gd-link", "rv-link", "altera-usb-blaster"]
        upload_protocols = board.manifest.get("upload", {}).get("protocols", [])

        if "tools" not in debug:
            debug["tools"] = {}

        sdk_dir = self.get_package_dir("framework-nuclei-sdk") or ""
        build_soc = build.get("soc", "").strip().lower()
        build_board = board.id

        # Only FTDI based debug probes
        for link in upload_protocols:
            if link in debug["tools"]:
                continue

            if link == "rv-link":
                board_cfg = join(
                    sdk_dir,
                    "SoC",
                    build_soc,
                    "Board",
                    build_board,
                    "openocd_%s.cfg" % build_soc,
                )
                if not isfile(board_cfg):
                    board_cfg = join(
                        sdk_dir, "SoC", build_soc, "Board", build_board, "openocd.cfg",
                    )
                server_args = ["-f", board_cfg]
                debug["tools"]["rv-link"] = {
                    "hwids": [["0x28e9", "0x018a"]],
                    "require_debug_port": True,
                }
            elif link == "jlink":
                assert debug.get("jlink_device"), (
                    "Missed J-Link Device ID for %s" % board.id
                )
                debug["tools"][link] = {
                    "server": {
                        "package": "tool-jlink",
                        "arguments": [
                            "-singlerun",
                            "-if",
                            "JTAG",
                            "-select",
                            "USB",
                            "-jtagconf",
                            "-1,-1",
                            "-device",
                            debug.get("jlink_device"),
                            "-port",
                            "2331",
                        ],
                        "executable": (
                            "JLinkGDBServerCL.exe"
                            if system() == "Windows"
                            else "JLinkGDBServer"
                        ),
                    },
                    "init_cmds": [
                        "define pio_reset_halt_target",
                        "    monitor halt",
                        "end",
                        "",
                        "define pio_reset_run_target",
                        "    monitor clrbp",
                        "    monitor reset",
                        "    monitor go",
                        "end",
                        "",
                        "target extended-remote $DEBUG_PORT",
                        "monitor clrbp",
                        "monitor speed auto",
                        "pio_reset_halt_target",
                        "$LOAD_CMDS",
                        "$INIT_BREAK",
                    ],
                    "onboard": link in debug.get("onboard_tools", []),
                }
            else:
                openocd_interface = link if link in non_ftdi_tools else "ftdi/" + link
                server_args = [
                    "-s",
                    "$PACKAGE_DIR/share/openocd/scripts",
                    "-f",
                    "interface/%s.cfg" % openocd_interface,
                    "-c",
                    "transport select jtag",
                    "-f",
                    "target/%s.cfg" % build_soc,
                ]
                server_args.extend(
                    ["-c", "adapter_khz %d" % (8000 if link == "um232h" else 1000)]
                )

            if link != "jlink":
                debug["tools"][link] = {
                    "server": {
                        "package": "tool-openocd-nuclei",
                        "executable": "bin/openocd",
                        "arguments": server_args,
                    },
                    "init_cmds": [
                        "define pio_reset_halt_target",
                        "   monitor halt",
                        "end",
                        "define pio_reset_run_target",
                        "   monitor reset",
                        "end",
                        "target extended-remote $DEBUG_PORT",
                        "$LOAD_CMDS",
                        "pio_reset_halt_target",
                        "$INIT_BREAK",
                    ],
                    "onboard": link in debug.get("onboard_tools", []),
                    "default": link in debug.get("default_tools", []),
                }

        board.manifest["debug"] = debug
        return board
