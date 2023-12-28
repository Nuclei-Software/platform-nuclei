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
import sys

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
board = env.BoardConfig()
build_board = board.id

FRAMEWORK_DIR = env.PioPlatform().get_package_dir("framework-nuclei-sdk")
FRAMEWORK_NUCLEI_SOC_CORES_MK = join(FRAMEWORK_DIR, "Build", "Makefile.core")

assert isdir(FRAMEWORK_DIR)


def is_valid_soc(soc):
    return isdir(join(FRAMEWORK_DIR, "SoC", soc))


def get_extra_soc_board_incdirs(soc, board):
    def _get_inc_dirs(path):
        incdirs = []
        if isdir(path):
            for dir in listdir(path):
                dir_path = join(path, dir)
                if isdir(dir_path):
                    incdirs.append(dir_path)
        return incdirs

    soc_inc_dir_root = join(FRAMEWORK_DIR, "SoC", soc, "Common", "Include")
    board_inc_dir_root = join(FRAMEWORK_DIR, "SoC", soc, "Board", board, "Include")

    return _get_inc_dirs(soc_inc_dir_root) + _get_inc_dirs(board_inc_dir_root)


def select_rtos_package(build_rtos):
    SUPPORTED_RTOSES = ("FreeRTOS", "UCOSII", "RTThread")
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
    core_arch_abi_re = re.compile(r'^([A-Z]+\d+[A-Z]*)_CORE_ARCH_ABI\s*=\s*(rv\d+\w*)\s+(i*lp\d+\w*)\s+(nuclei-\d*-series)')
    with open(core_mk, "r") as core_mk_file:
        for line in core_mk_file.readlines():
            line = line.strip()
            matches = core_arch_abi_re.match(line)
            if matches:
                core_lower = matches.groups()[0].lower()
                core_arch_abis[core_lower] = (matches.groups()[1:])
    return core_arch_abis


core_arch_abis = parse_nuclei_soc_predefined_cores(FRAMEWORK_NUCLEI_SOC_CORES_MK)

build_soc = board.get("build.soc", "").strip()

if not build_soc:
    sys.stderr.write(
        "build.soc is not defined in board description json file, please check!")
    env.Exit(1)

if build_soc == "hbird":
    print("%s SoC is deprecated, please use demosoc instead!" %(build_soc))
    build_soc = "demosoc"

BUILTIN_ALL_DOWNLOADED_MODES = ("ilm", "flash", "flashxip", "ddr", "sram", "sramxip")

build_core = board.get("build.core", "").lower().strip()
build_arch_ext = board.get("build.arch_ext", "").lower().strip()
build_march = board.get("build.march", "").lower().strip()
build_mabi = board.get("build.mabi", "").lower().strip()
build_mtune = board.get("build.mtune", "").lower().strip()
build_mcmodel = board.get("build.mcmodel", "").lower().strip()

build_rtos = board.get("build.rtos", "").lower().strip()
build_rtthread_msh = board.get("build.rtthread_msh", "").lower().strip()
build_variant = board.get("build.variant", "").lower().strip()

selected_rtos = select_rtos_package(build_rtos)

build_download_mode = board.get("build.download", "").lower().strip()

build_supported_download_modes = board.get("build.download_modes", [])

# Get supported download modes
build_supported_download_modes = [mode.lower().strip() for mode in build_supported_download_modes]
# intersection of BUILTIN_ALL_DOWNLOADED_MODES, build.download_modes, build.download
mixed_supported_download_modes = list(set(BUILTIN_ALL_DOWNLOADED_MODES).intersection(
    build_supported_download_modes))

if build_soc == "evalsoc":
    if build_download_mode not in mixed_supported_download_modes:
        # If build.download not defined for Nuclei demosoc SoC, use default "ILM"
        chosen_download_mode = "ilm" if len(mixed_supported_download_modes) == 0 else mixed_supported_download_modes[0]
        print("Download mode %s is not supported for SOC %s, use default download mode %s" \
             % (build_download_mode, build_soc, chosen_download_mode))
        build_download_mode = chosen_download_mode
else:
    if build_download_mode not in mixed_supported_download_modes:
        chosen_download_mode = "flashxip" if len(mixed_supported_download_modes) == 0 else mixed_supported_download_modes[0]
        print("Download mode %s is not supported for SOC %s, use default download mode %s" \
             % (build_download_mode, build_soc, chosen_download_mode))
        build_download_mode = chosen_download_mode

print("Supported downloaded modes for board %s are %s, chosen downloaded mode is %s" \
    % (build_board, mixed_supported_download_modes, build_download_mode))

if not board.get("build.ldscript", ""):
    build_soc_variant = build_soc
    if build_board == "gd32vf103c_longan_nano":
        if build_variant == "lite":
            build_soc_variant = "gd32vf103x8"
        else:
            build_soc_variant = "gd32vf103xb"

    ld_script = "gcc_%s_%s.ld" % (
        build_soc_variant, build_download_mode) if build_download_mode else "gcc_%s.ld" % build_soc
    build_ldscript = join(
        FRAMEWORK_DIR, "SoC", build_soc, "Board", build_board, "Source", "GCC", ld_script)
    env.Replace(LDSCRIPT_PATH=build_ldscript)
else:
    print("Use user defined ldscript %s" % board.get("build.ldscript"))

# Use correct downloaded modes
DOWNLOAD_MODE = "DOWNLOAD_MODE_%s" % build_download_mode.upper()

if selected_rtos:
    RTOS_MACRO = ("RTOS_%s" % selected_rtos.upper())
else:
    RTOS_MACRO = ("NO_RTOS_SERVICE")

default_arch_abi = ("rv32imac", "ilp32")

if not build_mabi and not build_march and build_core in core_arch_abis:
    if len(core_arch_abis[build_core]) == 2:
        build_march, build_mabi = core_arch_abis[build_core]
    elif len(core_arch_abis[build_core]) == 3:
        build_march, build_mabi, build_mtune = core_arch_abis[build_core]
else:
    if not build_mabi or not build_march:
        build_march, build_mabi = default_arch_abi
        print("No mabi and march specified in board json file, use default -march=%s -mabi=%s!" % (build_march, build_mabi))

if build_rtthread_msh == "1": # RT-Thread MSH compoment selected
    rtt_srcfilter = "+<*> -<**/iar/>"
else:
    rtt_srcfilter = "+<*> -<**/iar/> -<components/>"

env.SConscript("_bare.py", exports="env")

target_map = join("$BUILD_DIR", "${PROGNAME}.map")

build_mtune_opt = ""
if build_mtune != "":
    build_mtune_opt = "-mtune=%s" % build_mtune
if build_mcmodel == "":
    if "rv32" in build_march:
        build_mcmodel = "medlow"
    else:
        build_mcmodel = "medany"

build_march = "%s%s" % (build_march, build_arch_ext)

env.Append(
    CCFLAGS=[
        "-march=%s" % build_march,
        "-mabi=%s" % build_mabi,
        "-mcmodel=%s" % build_mcmodel,
        "%s" % build_mtune_opt
    ],

    ASFLAGS=[
        "-march=%s" % build_march,
        "-mabi=%s" % build_mabi,
        "-mcmodel=%s" % build_mcmodel,
        "%s" % build_mtune_opt
    ],

    LINKFLAGS=[
        "-march=%s" % build_march,
        "-mabi=%s" % build_mabi,
        "-mcmodel=%s" % build_mcmodel,
        "%s" % build_mtune_opt,
        "-Wl,-Map,%s" % target_map,
        "-nostartfiles",
        "--specs=nano.specs",
        "-u", "_isatty",
        "-u", "_write",
        "-u", "_sbrk",
        "-u", "_read",
        "-u", "_close",
        "-u", "_fstat",
        "-u", "_lseek",
        "-u", "errno"
    ],

    CPPDEFINES=[
        ("DOWNLOAD_MODE", DOWNLOAD_MODE),
        ("DOWNLOAD_MODE_STRING", "\\\"%s\\\"" % build_download_mode),
        ("VECTOR_TABLE_REMAPPED") if build_download_mode == "flash" else ("VECTOR_TABLE_NOT_REMAPPED"),
        RTOS_MACRO
    ],

    CPPPATH=[
        "$PROJECT_SRC_DIR",
        "$PROJECT_INCLUDE_DIR",
        join(FRAMEWORK_DIR, "NMSIS", "Include"),
        join(FRAMEWORK_DIR, "NMSIS", "Core", "Include"),
        join(FRAMEWORK_DIR, "NMSIS", "DSP", "Include"),
        join(FRAMEWORK_DIR, "NMSIS", "DSP", "PrivateInclude"),
        join(FRAMEWORK_DIR, "NMSIS", "NN", "Include"),
        join(FRAMEWORK_DIR, "SoC", build_soc, "Common", "Include"),
        join(FRAMEWORK_DIR, "SoC", build_soc, "Board", build_board, "Include"),
    ],

    LIBPATH=[
        join(FRAMEWORK_DIR, "NMSIS", "Library", "DSP", "GCC"),
        join(FRAMEWORK_DIR, "NMSIS", "Library", "NN", "GCC")
    ],

    LIBS=["gcc", "m", "stdc++"]
)

# WORKAROUND: If RT-Thread used, force it to include symbols from finsh
# otherwise it will not be included
if build_rtthread_msh == "1":
    env.Append(LINKFLAGS=["-u", "finsh_system_init"])

extra_incdirs = get_extra_soc_board_incdirs(build_soc, build_board)
if extra_incdirs:
    env.Append(
        CPPPATH=extra_incdirs
    )

if not is_valid_soc(build_soc):
    sys.stderr.write("Could not find BSP package for SoC %s" % build_soc)
    env.Exit(1)

#
# Target: Build Nuclei SDK Libraries
#
soclibname = "soc_" + build_soc
boardlibname = "board_" + build_board
libs = [
    env.BuildLibrary(
        join("$BUILD_DIR", "SoC", build_soc, soclibname),
        join(FRAMEWORK_DIR, "SoC", build_soc, "Common"),
        src_filter="+<*> -<**/IAR/> -<**/iardlib/> -<**/libncrt/>"
    ),

    env.BuildLibrary(
        join("$BUILD_DIR", "SoC", build_soc, "Board", boardlibname),
        join(FRAMEWORK_DIR, "SoC", build_soc, "Board", build_board),
        src_filter="+<*> -<**/IAR/>"
    )
]

if selected_rtos == "FreeRTOS":
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "RTOS", "FreeRTOS"),
        join(FRAMEWORK_DIR, "OS", "FreeRTOS", "Source"),
        src_filter="+<*> -<portable/MemMang/> -<portable/IAR/> +<portable/MemMang/heap_4.c>"
    ))
    env.Append(
        CPPPATH=[
            join(FRAMEWORK_DIR, "OS", "FreeRTOS", "Source", "include"),
            join(FRAMEWORK_DIR, "OS", "FreeRTOS", "Source", "portable")
        ]
    )
elif selected_rtos == "UCOSII":
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "RTOS", "UCOSII"),
        join(FRAMEWORK_DIR, "OS", "UCOSII"),
        src_filter="+<*> -<arch/iar/>"
    ))
    env.Append(
        CPPPATH=[
            join(FRAMEWORK_DIR, "OS", "UCOSII", "arch"),
            join(FRAMEWORK_DIR, "OS", "UCOSII", "cfg"),
            join(FRAMEWORK_DIR, "OS", "UCOSII", "source")
        ]
    )
elif selected_rtos == "RTThread":
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "RTOS", "RTThread"),
        join(FRAMEWORK_DIR, "OS", "RTThread"),
        src_filter=rtt_srcfilter
    ))
    env.Append(
        CPPPATH=[
            join(FRAMEWORK_DIR, "OS", "RTThread", "libcpu", "risc-v", "nuclei"),
            join(FRAMEWORK_DIR, "OS", "RTThread", "include"),
            join(FRAMEWORK_DIR, "OS", "RTThread", "include", "libc"),
            join(FRAMEWORK_DIR, "OS", "RTThread", "components", "finsh")
        ]
    )

env.Prepend(LIBS=libs)
