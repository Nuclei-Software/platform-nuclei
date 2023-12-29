# Nuclei: development platform for [PlatformIO](https://platformio.org)

[![Build Examples](https://github.com/Nuclei-Software/platform-nuclei/actions/workflows/build.yml/badge.svg?branch=feature%2Fgd32vw55x)](https://github.com/Nuclei-Software/platform-nuclei/actions/workflows/build.yml)

[Nuclei System Technology](https://www.nucleisys.com/) is a professional RISC-V IP product company.
It provides various RISC-V IP products which can meet the requirements of the AIoT era.
It is the first RISC-V Core IP provider company in Mainland China, launchs the world's
first mass production general-purpose MCU based on RISC-V together with GigaDevice,
see https://www.gigadevice.com/products/microcontrollers/gd32/risc-v/, and is also
the RISC-V eco-system leader in Mainland China.

* [Home](https://platformio.org/platforms/nuclei) (home page in PlatformIO Platform Registry)
* [Documentation](http://docs.platformio.org/page/platforms/nuclei.html) (advanced usage, packages, boards, frameworks, etc.)

# Usage

1. [Install PlatformIO](https://platformio.org)
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
