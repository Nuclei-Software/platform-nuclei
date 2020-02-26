# Nuclei: development platform for [PlatformIO](http://platformio.org)
[![Build Status](https://travis-ci.com/Nuclei-Software/platform-nuclei.svg?branch=master)](https://travis-ci.com/Nuclei-Software/platform-nuclei)
[![Build status](https://ci.appveyor.com/api/projects/status/cy7mc2qbd5yalr41?svg=true)](https://ci.appveyor.com/project/fanghuaqi/platform-nuclei)

[Nuclei System Technology](https://www.nucleisys.com/) is a professional RISC-V IP product company.
It provides various RISC-V IP products which can meet the requirements of the AIoT era.
It is the first RISC-V Core IP provider company in Mainland China, launchs the world's
first mass production general-purpose MCU based on RISC-V together with GigaDevice,
see https://www.gigadevice.com/products/microcontrollers/gd32/risc-v/, and is also
the RISC-V eco-system leader in Mainland China.

* [Home](http://platformio.org/platforms/nuclei) (home page in PlatformIO Platform Registry)
* [Documentation](http://docs.platformio.org/page/platforms/nuclei.html) (advanced usage, packages, boards, frameworks, etc.)

# Usage

1. [Install PlatformIO](http://platformio.org)
2. Create PlatformIO project and configure a platform option in [platformio.ini](http://docs.platformio.org/page/projectconf.html) file:

## Stable version

```ini
[env:stable]
platform = nuclei
board = ...
...
```

## Development version

```ini
[env:development]
platform = https://github.com/Nuclei-Software/platform-nuclei.git
board = ...
...
```

# Configuration

Please navigate to [documentation](http://docs.platformio.org/page/platforms/nuclei.html).
