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

def select_rtos_package(build_rtos):
    SUPPORTED_RTOSES = ("FreeRTOS", "UCOSII", "RTThread", "ThreadX")
    selected_rtos = None
    build_rtos = build_rtos.strip().lower()
    for rtos in SUPPORTED_RTOSES:
        if rtos.lower() == build_rtos:
            selected_rtos = rtos
    return selected_rtos

def parse_nuclei_predefined_cores(core_mk):
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

def find_suitable_download(download, download_modes):
    if download_modes and type(download_modes) == list and len(download_modes) > 1:
        if download not in download_modes:
            print("DOWNLOAD MODE is %s, not supported in %s" % (download, download_modes))
            download = download_modes[0]
            print("Change to use DOWNLOAD MODE %s now!!!!!" % (download))
    return download

def find_suitable_ldscript(socdir, soc, board, download, variant=""):
    soc_variant = soc
    if board == "gd32vf103c_longan_nano":
        soc_variant = "gd32vf103x8" if variant == "lite" else "gd32vf103xb"

    if download:
        ld_script = "gcc_%s_%s.ld" % (soc_variant, download)
    else:
        ld_script = "gcc_%s.ld" % build_soc

    build_ldscript = join(socdir, "Board", build_board, "Source", "GCC", ld_script)
    return build_ldscript

def find_arch_abi_tune_cmodel(core, arch, abi, tune, cmodel, splist):
    if not (arch and abi) and core in splist:
        if len(splist[core]) == 2:
            arch, abi = splist[core]
        elif len(splist[core]) == 3:
            arch, abi, tune = splist[core]
    if not cmodel:
        cmodel = "medlow" if "rv32" in arch else "medany"

    return [arch, abi, tune, cmodel]

def get_arch_flags(arch, abi, tune, cmodel, archext, toolchain):
    optlist = ["-g"]
    optlist.append("-march=%s%s" % (arch, archext)) if arch else optlist
    optlist.append("-mabi=%s" % (abi)) if abi else optlist
    optlist.append("-mcmodel=%s" % (cmodel)) if cmodel else optlist
    if toolchain == "nuclei_gnu":
        optlist.append("-mtune=%s" % (tune)) if tune else optlist
    return optlist

# Get core arch/abi/mtune list
core_arch_abis = parse_nuclei_predefined_cores(FRAMEWORK_NUCLEI_SOC_CORES_MK)

# get build soc
build_soc = board.get("build.soc", "").strip()

if not build_soc:
    print("Error! build.soc is not defined in board description json file %s.json, please check!" % (build_board))
    env.Exit(1)

# Check whether soc is supported by this nuclei sdk
if build_soc in ("hbird", "demosoc"):
    if not is_valid_soc(build_soc):
        print("Warning! %s SoC is deprecated, please use evalsoc instead!" %(build_soc))
        build_soc = "evalsoc"

FRAMEWORK_SOC_DIR = ""
if not is_valid_soc(build_soc):
    print("Warning! Could not find %s SoC support package in framework-nuclei-sdk" % build_soc)
    soc_framework_pkg = "framework-nuclei-sdk-%s" % build_soc
    try:
        # you can add an extra platform_packages see https://docs.platformio.org/en/latest/projectconf/sections/env/options/platform/platform_packages.html
        print("Try to find SoC support package from pio package %s, assume it is provided!" % (soc_framework_pkg))
        FRAMEWORK_SOC_DIR = env.PioPlatform().get_package_dir(soc_framework_pkg)
        print("Using SoC support package source code from %s" % (soc_framework_pkg))
    except KeyError:
        print("Error! If you confirm this pio package %s existed, please install it!" % (soc_framework_pkg))
        env.Exit(1)

# Set Nuclei SDK Root directory
build_nsdk_dir = FRAMEWORK_DIR
build_nsdk_socdir = os.path.join(FRAMEWORK_DIR, "SoC", build_soc)
if FRAMEWORK_SOC_DIR != "":
    build_nsdk_socdir = FRAMEWORK_SOC_DIR

build_core = board.get("build.core", "").lower().strip()
build_arch_ext = board.get("build.arch_ext", "").lower().strip()

build_march = board.get("build.march", "").lower().strip()
build_mabi = board.get("build.mabi", "").lower().strip()
build_mtune = board.get("build.mtune", "").lower().strip()
build_mcmodel = board.get("build.mcmodel", "").lower().strip()

build_rtos = board.get("build.rtos", "").lower().strip()
build_rtthread_msh = board.get("build.rtthread_msh", "").lower().strip()
build_variant = board.get("build.variant", "").lower().strip()
build_toolchain = board.get("build.toolchain", "").lower().strip()
build_download = board.get("build.download", "").lower().strip()
build_download_modes = board.get("build.download_modes", [])
build_stdclib = board.get("build.stdclib", "newlib_small").lower().strip()
build_simu = board.get("build.simu", "").lower().strip()
build_ncrtio = board.get("build.ncrtio", "uart").lower().strip()
build_stacksz = board.get("build.stacksz", "").lower().strip()
build_heapsz = board.get("build.heapsz", "").lower().strip()
build_ldscript = board.get("build.ldscript", "").lower().strip()
build_nmsis_lib = board.get("build.nmsis_lib", "").lower().strip()
build_nmsis_lib_arch = board.get("build.nmsis_lib_arch", "").lower().strip()
build_usb_driver = board.get("build.usb_driver", "").lower().strip()
build_smp = board.get("build.smp", "").lower().strip()
build_boot_hartid = board.get("build.boot_hartid", "").lower().strip()
build_hartid_ofs = board.get("build.hartid_ofs", "").lower().strip()
build_sysclk = board.get("build.sysclk", "").lower().strip()
build_clksrc = board.get("build.clksrc", "").lower().strip()
build_hxtal_value = board.get("build.hxtal_value", "").lower().strip()

selected_rtos = select_rtos_package(build_rtos)

build_download = find_suitable_download(build_download, build_download_modes)

if not build_ldscript:
    build_ldscript = find_suitable_ldscript(build_nsdk_socdir, build_soc, build_board, build_download, build_variant)

build_march, build_mabi, build_mtune, build_mcmodel = find_arch_abi_tune_cmodel(build_core, build_march, build_mabi, build_mtune, build_mcmodel, core_arch_abis)

env.SConscript("_bare.py", exports="env")
print("Use ldscript %s" % build_ldscript)
env.Replace(LDSCRIPT_PATH=build_ldscript)

target_map = join("$BUILD_DIR", "${PROGNAME}.map")

build_arch_flags = get_arch_flags(build_march, build_mabi, build_mtune, build_mcmodel, build_arch_ext, build_toolchain)

if not build_nmsis_lib_arch:
    build_nmsis_lib_arch = "%s%s" % (build_march, build_arch_ext)

build_common_flags = build_arch_flags
build_asmflags = []
build_cflags = []
build_cxxflags = []
build_ldflags = [
        "-Wl,-Map,%s" % target_map,
        "-nostartfiles",
        "-nodefaultlibs",
        "-u", "_isatty",
        "-u", "_write",
        "-u", "_sbrk",
        "-u", "_read",
        "-u", "_close",
        "-u", "_fstat",
        "-u", "_lseek",
        "-u", "errno"]

build_cppdefines = []
build_cpppaths = [
    "$PROJECT_SRC_DIR", "$PROJECT_INCLUDE_DIR", join(build_nsdk_dir, "NMSIS", "Core", "Include"),
    join(build_nsdk_socdir, "Common", "Include"),
    join(build_nsdk_socdir, "Board", build_board, "Include")]
build_libpaths = []
build_libs = []

stubname = "newlib"
# process stdclib
if build_stdclib.startswith("libncrt"):
    stubname = "libncrt"
    ncrtlib = build_stdclib.replace("lib", "")
    build_libs = [ncrtlib, "fileops_%s" % (build_ncrtio), "heapops_basic"]
    build_common_flags.extend(["-isystem", "/include/libncrt"])
else:
    build_common_flags.extend(["-isystem", "/include/newlib-nano"])
    if build_stdclib == "newlib_full":
        build_libs.extend(["c", "gcc", "m", "stdc++"])
    else:
        build_libs.extend(["c_nano", "gcc", "m", "stdc++"])
        if build_stdclib == "newlib_fast":
            build_ldflags.extend(["-u", "_printf_float", "-u", "_scanf_float"])
        elif build_stdclib == "newlib_small":
            build_ldflags.extend(["-u", "_printf_float"])
        if build_toolchain == "nuclei_llvm":
            build_ldflags.extend(["-u", "_printf_float", "-u", "__on_exit_args"])

if build_toolchain == "nuclei_gnu":
    build_ldflags.append("-Wl,--no-warn-rwx-segments")
    if "zc" in build_arch_ext:
        build_common_flags.extend(["-fomit-frame-pointer", "-fno-shrink-wrap-separate"])

if build_download:
    build_cppdefines.extend([("DOWNLOAD_MODE", "DOWNLOAD_MODE_%s" % (build_download.upper())),
        ("DOWNLOAD_MODE_STRING", "\\\"%s\\\"" % build_download),
        "VECTOR_TABLE_REMAPPED" if build_download == "flash" else "VECTOR_TABLE_NOT_REMAPPED"])

if selected_rtos:
    build_cppdefines.extend(["RTOS_%s" % selected_rtos.upper()])

if build_nmsis_lib:
    sel_nmsis_libs = build_nmsis_lib.split()
    print(sel_nmsis_libs)
    for lib in ["dsp", "nn"]:
        libname = "nmsis_%s" % (lib)
        if libname in sel_nmsis_libs:
            build_libs.extend(["%s_%s" % (libname, build_nmsis_lib_arch)])
            build_libpaths.extend([join(build_nsdk_dir, "NMSIS", "Library", lib.upper(), "GCC")])
            build_cpppaths.extend([join(build_nsdk_dir, "NMSIS", lib.upper(), "Include")])
            if lib == "dsp":
                build_cpppaths.extend([join(build_nsdk_dir, "NMSIS", lib.upper(), "PrivateInclude")])

if build_soc == "gd32vf103" and build_usb_driver != "":
    build_cpppaths.extend([join(build_nsdk_socdir, "Common", "Include", "Usb")])

if build_simu:
    build_cppdefines.extend([("SIMULATION_MODE", "SIMULATION_MODE_%s" % (build_simu.upper()))])

if build_heapsz:
    build_ldflags.extend(["-Wl,--defsym=__HEAP_SIZE=%s" % (build_heapsz)])

if build_stacksz:
    build_ldflags.extend(["-Wl,--defsym=__STACK_SIZE=%s" % (build_stacksz)])

if build_smp:
    build_cppdefines.extend([("SMP_CPU_CNT", build_smp)])
    build_ldflags.extend(["-Wl,--defsym=__SMP_CPU_CNT=%s" % (build_smp)])

if build_boot_hartid:
    build_cppdefines.extend([("BOOT_HARTID", build_boot_hartid)])

if build_hartid_ofs:
    build_cppdefines.extend([("__HARTID_OFFSET", build_hartid_ofs)])

if build_sysclk:
    build_cppdefines.extend([("SYSTEM_CLOCK", build_sysclk)])

if build_clksrc:
    build_cppdefines.extend(["SYSCLK_USING_%s" % (build_clksrc.upper())])

if build_hxtal_value:
    build_cppdefines.extend([("HXTAL_VALUE", build_hxtal_value)])

# WORKAROUND: If RT-Thread used, force it to include symbols from finsh
# otherwise it will not be included
if build_rtthread_msh == "1": # RT-Thread MSH compoment selected
    build_ldflags.extend(["-u", "finsh_system_init"])
    rtt_srcfilter = "+<*> -<**/iar/>"
else:
    rtt_srcfilter = "+<*> -<**/iar/> -<components/>"

if build_toolchain == "nuclei_llvm":
    build_ldflags.extend(["-fuse-ld=lld"])
    env.Replace(
        AR="llvm-ar",
        AS="riscv64-unknown-elf-clang",
        CC="riscv64-unknown-elf-clang",
        CXX="riscv64-unknown-elf-clang++",
        RANLIB="llvm-ranlib"
    )

# Append generic options
env.Append(
    ASFLAGS = build_common_flags + build_asmflags,
    CFLAGS = build_common_flags + build_cflags,
    CXXFLAGS = build_common_flags + build_cxxflags,
    LINKFLAGS = build_common_flags + build_ldflags,
    CPPDEFINES = build_cppdefines,
    CPPPATH = build_cpppaths,
    LIBPATH = build_libpaths,
    LIBS = build_libs
    )

#
# Target: Build Nuclei SDK Libraries
#
soclibname = "soc_" + build_soc
boardlibname = "board_" + build_board

libs = [
    env.BuildLibrary(
        join("$BUILD_DIR", "SoC", build_soc, soclibname),
        join(build_nsdk_socdir, "Common"),
        src_filter="+<*> -<**/IAR/> -<**/Stubs/> -<**/Usb/> +<**/%s/>" % (stubname)
    ),
    env.BuildLibrary(
        join("$BUILD_DIR", "SoC", build_soc, "Board", boardlibname),
        join(build_nsdk_socdir, "Board", build_board),
        src_filter="+<*> -<**/IAR/>"
    )
]

if selected_rtos == "FreeRTOS":
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "RTOS", "FreeRTOS"),
        join(build_nsdk_dir, "OS", "FreeRTOS", "Source"),
        src_filter="+<*> -<portable/MemMang/> -<portable/IAR/> +<portable/MemMang/heap_4.c>"
    ))
    env.Append(
        CPPPATH = [
            join(build_nsdk_dir, "OS", "FreeRTOS", "Source", "include"),
            join(build_nsdk_dir, "OS", "FreeRTOS", "Source", "portable")
        ]
    )
elif selected_rtos == "UCOSII":
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "RTOS", "UCOSII"),
        join(build_nsdk_dir, "OS", "UCOSII"),
        src_filter="+<*> -<arch/iar/>"
    ))
    env.Append(
        CPPPATH = [
            join(build_nsdk_dir, "OS", "UCOSII", "arch"),
            join(build_nsdk_dir, "OS", "UCOSII", "cfg"),
            join(build_nsdk_dir, "OS", "UCOSII", "source")
        ]
    )
elif selected_rtos == "RTThread":
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "RTOS", "RTThread"),
        join(build_nsdk_dir, "OS", "RTThread"),
        src_filter=rtt_srcfilter
    ))
    env.Append(
        CPPPATH = [
            join(build_nsdk_dir, "OS", "RTThread", "libcpu", "risc-v", "nuclei"),
            join(build_nsdk_dir, "OS", "RTThread", "include"),
            join(build_nsdk_dir, "OS", "RTThread", "include", "libc")
            ]
    )
    if build_rtthread_msh == "1":
        env.Append(
            CPPPATH = [
                join(build_nsdk_dir, "OS", "RTThread", "components", "finsh")
                ]
        )
elif selected_rtos == "ThreadX":
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "RTOS", "ThreadX"),
        join(build_nsdk_dir, "OS", "ThreadX"),
        src_filter="+<*> -<iar/>"
    ))
    env.Append(
        CPPPATH = [
            join(build_nsdk_dir, "OS", "ThreadX", "common", "inc"),
            join(build_nsdk_dir, "OS", "ThreadX", "ports", "nuclei")
        ]
    )

# process usb library
if build_soc == "gd32vf103" and build_usb_driver != "":
    usb_srcfilter = "+<*>"
    if build_usb_driver == "device":
        usb_srcfilter = "+<*> -<*usbh_*.c> -<drv_usb_host.c>"
    elif build_usb_driver == "host":
        usb_srcfilter = "+<*> -<*usbd_*.c> -<drv_usb_dev.c>"
    else:
        usb_srcfilter = "+<*>"

    libs.append(env.BuildLibrary(
            join("$BUILD_DIR", "SoC", build_soc, "%s_usb" %(soclibname)),
            join(build_nsdk_socdir, "Common", "Source", "Drivers", "Usb"),
            src_filter=usb_srcfilter
        ))

env.Prepend(LIBS=libs)
