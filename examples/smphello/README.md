How to build PlatformIO based project
=====================================

1. [Install PlatformIO Core](http://docs.platformio.org/page/core.html)
2. Download [development platform with examples](https://github.com/Nuclei-Software/platform-nuclei/archive/develop.zip)
3. Extract ZIP archive
4. Run these commands:

```shell
# Change directory to example
$ cd platform-nuclei/examples/smphello

# Build project
$ pio run

# required ux900fd 4c version
# Upload firmware
$ pio run --target upload

# Build specific environment
$ pio run -e nuclei-nuclei_fpga_eval

# Upload firmware for the specific environment
$ pio run -e nuclei-nuclei_fpga_eval --target upload

# Clean build files
$ pio run --target clean
```
