# Copyright 2019-present PlatformIO <contact@platformio.org>
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

"""
Nuclei N/NX embedded Software Development Kit

Open Source Software for Developing on the Nuclei N/NX processors

https://github.com/Nuclei-Software/nuclei-sdk
"""
import os
from os import listdir
from os.path import isdir, join
import re

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
board = env.BoardConfig()
build_board = board.id

FRAMEWORK_DIR = env.PioPlatform().get_package_dir("framework-nuclei-sdk")
FRAMEWORK_NUCLEI_SOC_CORES_MK = join(FRAMEWORK_DIR, "Build", "Makefile.core")

def is_valid_soc(soc):
    soc_dir = join(FRAMEWORK_DIR, "SoC", soc)
    return isdir(soc_dir)

def get_extra_soc_board_incdirs(soc, board):
    soc_inc_dir_root = join(FRAMEWORK_DIR, "SoC", soc, "Common", "Include")
    board_inc_dir_root = join(FRAMEWORK_DIR, "SoC", soc, "Board", board, "Include")
    incdirs = []

    # Add include directories in SoC/<soc>/Common/Include/<sub>
    if isdir(soc_inc_dir_root):
        for dir in listdir(soc_inc_dir_root):
            dir_path = join(soc_inc_dir_root, dir)
            if isdir(dir_path):
                incdirs.append(dir_path)

    # Add include directories in SoC/<soc>/Board/<board>/Include/<sub>
    if isdir(board_inc_dir_root):
        for dir in listdir(board_inc_dir_root):
            dir_path = join(board_inc_dir_root, dir)
            if isdir(dir_path):
                incdirs.append(dir_path)

    return incdirs

def select_rtos_package(build_rtos):
    SUPPORTED_RTOSES = ["FreeRTOS", "UCOSII"]
    selected_rtos = None
    build_rtos = build_rtos.strip().lower()
    for rtos in SUPPORTED_RTOSES:
        if rtos.lower() == build_rtos:
            selected_rtos = rtos
    return selected_rtos

def parse_nuclei_soc_predefined_cores(core_mk):
    if not os.path.isfile(core_mk):
        return dict()
    core_arch_abis = dict()
    core_arch_abi_re = re.compile(r'^([A-Z]+\d+[A-Z]*)_CORE_ARCH_ABI\s*=\s*(rv\d+\w*)\s+(i*lp\d+\w*)')
    with open(core_mk, "r") as core_mk_file:
        for line in core_mk_file.readlines():
            line = line.strip()
            matches = core_arch_abi_re.match(line)
            if matches:
                core_lower = matches.groups()[0].lower()
                core_arch_abis[core_lower] = (matches.groups()[1:3])
    return core_arch_abis

core_arch_abis = parse_nuclei_soc_predefined_cores(FRAMEWORK_NUCLEI_SOC_CORES_MK)

build_soc = board.get("build.soc", "").strip()

if build_soc == "":
    print("build.soc is not defined in board description json file, please check!")
    env.Exit(1)

BUILTIN_ALL_DOWNLOADED_MODES = ["ilm", "flash", "flashxip"]

build_core = board.get("build.core", "").lower().strip()
build_mabi = board.get("build.mabi", "").lower().strip()
build_march = board.get("build.march", "").lower().strip()
build_mcmodel = board.get("build.mcmodel", "medany").lower().strip()
build_rtos = board.get("build.rtos", "").lower().strip()

selected_rtos = select_rtos_package(build_rtos)

build_download_mode = board.get("build.download", "").lower().strip()

build_supported_download_modes = board.get("build.download_modes", [])

# Get supported download modes
build_supported_download_modes = [ mode.lower().strip() for mode in build_supported_download_modes ]
# intersection of BUILTIN_ALL_DOWNLOADED_MODES, build.download_modes, build.download
mixed_supported_download_modes = list(set(BUILTIN_ALL_DOWNLOADED_MODES).intersection(build_supported_download_modes))

build_ldscript = board.get("build.ldscript", "").strip()

if build_soc == "hbird":
    if build_download_mode not in mixed_supported_download_modes:
        # If build.download not defined for hbird SoC, use default "ILM"
        chosen_download_mode = "ilm" if len(mixed_supported_download_modes) == 0 else mixed_supported_download_modes[0]
        print("Download mode %s is not supported for SOC %s, use default download mode %s" \
             %(build_download_mode, build_soc, chosen_download_mode))
        build_download_mode = chosen_download_mode
else:
    if build_download_mode not in mixed_supported_download_modes:
        chosen_download_mode = "flashxip" if len(mixed_supported_download_modes) == 0 else mixed_supported_download_modes[0]
        print("Download mode %s is not supported for SOC %s, use default download mode %s" \
             %(build_download_mode, build_soc, chosen_download_mode))
        build_download_mode = chosen_download_mode

print("Supported downloaded modes for board %s are %s, chosen downloaded mode is %s" \
    % (build_board, mixed_supported_download_modes, build_download_mode))

if build_ldscript == "":
    ld_script = ""
    if build_download_mode == "":
        ld_script = "gcc_%s.ld" % build_soc
    else:
        ld_script = "gcc_%s_%s.ld" % (build_soc, build_download_mode)

    build_ldscript = join(FRAMEWORK_DIR, "SoC", build_soc, "Board", "${BOARD}", "Source", "GCC", ld_script)
else:
    print("Use user defined ldscript %s" % build_ldscript)

# Use correct downloaded modes
DOWNLOAD_MODE = "DOWNLOAD_MODE_%s" % build_download_mode.upper()

default_arch_abi = ("rv32imac", "ilp32")

if build_mabi == "" and build_march == "" and build_core in core_arch_abis:
    build_march, build_mabi = core_arch_abis[build_core]
else:
    if build_mabi == "" or build_march == "":
        build_march, build_mabi = default_arch_abi
        print("No mabi and march specified in board json file, use default -march=%s -mabi=%s!" % (build_march, build_mabi))

assert FRAMEWORK_DIR and isdir(FRAMEWORK_DIR)

env.SConscript("_bare.py", exports="env")

env.Append(
    CCFLAGS=[
        "-march=%s" % build_march,
        "-mabi=%s" % build_mabi,
        "-mcmodel=%s" % build_mcmodel
    ],

    ASFLAGS=[
        "-march=%s" % build_march,
        "-mabi=%s" % build_mabi,
        "-mcmodel=%s" % build_mcmodel
    ],

    LINKFLAGS=[
        "-march=%s" % build_march,
        "-mabi=%s" % build_mabi,
        "-mcmodel=%s" % build_mcmodel
    ],

    CPPDEFINES=[
        ("DOWNLOAD_MODE", DOWNLOAD_MODE)
    ],

    CPPPATH=[
        "$PROJECT_SRC_DIR",
        "$PROJECT_INCLUDE_DIR",
        join(FRAMEWORK_DIR, "NMSIS", "Include"),
        join(FRAMEWORK_DIR, "SoC", build_soc, "Common", "Include"),
        join(FRAMEWORK_DIR, "SoC", build_soc, "Board", build_board, "Include"),
    ],

    LIBPATH=[
        "$BUILD_DIR"
    ],

    LIBS=["gcc", "m"]
)

extra_incdirs = get_extra_soc_board_incdirs(build_soc, build_board)
if extra_incdirs:
    env.Append(
        CPPPATH=extra_incdirs
    )

env.Replace(
    LDSCRIPT_PATH = build_ldscript
)

if not is_valid_soc(build_soc):
    print ("Could not find BSP package for SoC %s" % build_soc)
    env.Exit(1)

#
# Target: Build Nuclei SDK Libraries
#

libs = [
    env.BuildLibrary(
        join("$BUILD_DIR", "SoC", build_soc, "Common"),
        join(FRAMEWORK_DIR, "SoC", build_soc, "Common")
    ),

    env.BuildLibrary(
        join("$BUILD_DIR", "SoC", build_soc, "Board", build_board),
        join(FRAMEWORK_DIR, "SoC", build_soc, "Board", build_board)
    )
]

rtoslibs = []
if selected_rtos == "FreeRTOS":
    rtoslibs = [
        env.BuildLibrary(
            join("$BUILD_DIR", "RTOS", "FreeRTOS"),
            join(FRAMEWORK_DIR, "OS", "FreeRTOS", "Source"),
            src_filter="+<*> -<portable/MemMang/> +<portable/MemMang/heap_4.c>"
        )
    ]
    env.Append(
        CPPPATH=[
            join(FRAMEWORK_DIR, "OS", "FreeRTOS", "Source", "include"),
            join(FRAMEWORK_DIR, "OS", "FreeRTOS", "Source", "portable", "GCC")
        ]
    )
elif selected_rtos == "UCOSII":
    rtoslibs = [
        env.BuildLibrary(
            join("$BUILD_DIR", "RTOS", "UCOSII"),
            join(FRAMEWORK_DIR, "OS", "UCOSII")
        )
    ]
    env.Append(
        CPPPATH=[
            join(FRAMEWORK_DIR, "OS", "UCOSII", "arch"),
            join(FRAMEWORK_DIR, "OS", "UCOSII", "cfg"),
            join(FRAMEWORK_DIR, "OS", "UCOSII", "source")
        ]
    )

libs.append(rtoslibs)

env.Prepend(LIBS=libs)