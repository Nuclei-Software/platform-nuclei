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

#
# Default flags for bare-metal programming (without any framework layers)
#

from SCons.Script import Import

Import("env")

env.Append(
    CCFLAGS=[
        "-Os",
        "-Wall",  # show warnings
        "-ffunction-sections",
        "-fdata-sections"
    ],

    LINKFLAGS=[
        "-Os",
        "-nostartfiles",
        "--specs=nano.specs",
        "--specs=nosys.specs",
        "-Wl,--gc-sections"
    ],

    LIBS=["c"],
)

# copy CCFLAGS to ASFLAGS (-x assembler-with-cpp mode)
env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])
