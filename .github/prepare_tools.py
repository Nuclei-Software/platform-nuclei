import os
import sys
import platform
import zipfile
import tarfile
import shutil
import json
import requests
import hashlib

from urllib.parse import urlparse
import argparse
try:
    import wget  # Import the wget library
    NOWGET = False
except:
    NOWGET = True
    pass

PIOJSONLOC = ""
PREBLT_CACHE = "prebuilt_dlcache"
PREBLT_TOOLS = "prebuilt_tools"

def download_file(url, file_name):
    if NOWGET:
        # Download the file using stream to avoid loading the entire file into memory
        with requests.get(url, stream=True) as response:
            with open(file_name, 'wb') as file:
                shutil.copyfileobj(response.raw, file)
    else:
        wget.download(url, file_name)
    pass

def get_file_size(file_path):
    return os.path.getsize(file_path)

def calculate_md5(file_path, buffer_size=8192):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(buffer_size), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def md5sum_file(file_path):
    if os.path.isfile(file_path) == False:
        print("{file_path} not existed!")
        return False
    print(f"{file_path} size %s bytes" % (get_file_size(file_path)))
    print(f"{file_path} md5 %s" % (calculate_md5(file_path)))
    return True

def download_with_progress(url, destination_folder, reuse=False):
    file_name = os.path.join(destination_folder, os.path.basename(urlparse(url).path))
    if os.path.isdir(destination_folder) == False:
        os.makedirs(destination_folder)

    if reuse == False and os.path.isfile(file_name):
        os.remove(file_name)
    # Download the file with progress bar
    if os.path.isfile(file_name) == False:
        download_file(url, file_name)
        print("%s is downloaded!" % (file_name))
    else:
        print("%s already downloaded!" % (file_name))
    md5sum_file(file_name)

    return file_name

def download_and_extract(url, extract_folder, reuse=False):
    print("Downloading %s" % (url))
    file_name = download_with_progress(url, PREBLT_CACHE, reuse)

    if os.path.isdir(extract_folder) == False:
        os.makedirs(extract_folder)

    print("Extracting %s to %s" % (file_name, extract_folder))
    # Extract the contents
    if file_name.endswith(".zip"):
        print(f"Unzip {file_name}")
        with zipfile.ZipFile(file_name, "r") as zip_ref:
            zip_ref.extractall(extract_folder)
    elif file_name.endswith(".tar.gz") or file_name.endswith(".tgz"):
        print(f"Untar {file_name}")
        with tarfile.open(file_name, "r:gz") as tar_ref:
            tar_ref.extractall(extract_folder)
    else:
        print("Unsupported archive file %s" % (file_name))

    print("List in this directory %s: %s" %(extract_folder, os.listdir(extract_folder)))
    # Remove the temporary file
    if reuse == False and os.path.isfile(file_name):
        os.remove(file_name)
    pass

def modify_json_file(old_file, file_path, system_value):
    # Read the existing JSON file
    with open(old_file, "r") as json_file:
        data = json.load(json_file)

    # Modify the 'system' key
    data["system"] = system_value

    # Write back to the JSON file
    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=4)

    print("%s is ready!" % (file_path))
    pass

def setup_nuclei_studio(toolsdir, nuclei_url, system_value, reuse):
    # Download and extract NucleiStudio
    nuclei_folder = toolsdir
    download_and_extract(nuclei_url, nuclei_folder, reuse)

    # Fix nuclei studio path
    for item in os.listdir(nuclei_folder):
        if os.path.isdir(item) and item.startswith("NucleiStudio") and item != "NucleiStudio":
            nsidepath = os.path.join(nuclei_folder, item)
            newpath = os.path.join(nuclei_folder, "NucleiStudio")
            if len(os.listdir(nsidepath)) == 1:
                nsidepath = os.path.join(nsidepath, "NucleiStudio")
            # rename old ide path to new ide path
            # such as NucleiStudio_IDE_202310/NucleiStudio -> NucleiStudio
            os.rename(nsidepath, newpath)
            break

    # Copy and modify nuclei_openocd.json
    openocd_json_path = os.path.join(nuclei_folder, "NucleiStudio", "toolchain", "openocd", "package.json")
    modify_json_file(os.path.join(PIOJSONLOC, "openocd.json"), openocd_json_path, system_value)

    # Copy and modify nuclei_gcc.json
    gcc_json_path = os.path.join(nuclei_folder, "NucleiStudio", "toolchain", "gcc", "package.json")
    modify_json_file(os.path.join(PIOJSONLOC, "gcc.json"), gcc_json_path, system_value)

def setup_gd_openocd(toolsdir, gd_openocd_url, system_value, gd_openocd_folder_name, reuse):
    # Download and extract gd32-openocd to a temporary folder
    tools_folder = toolsdir
    temp_folder = os.path.join(tools_folder, "temp_gd_openocd")
    download_and_extract(gd_openocd_url, temp_folder)

    # Rename the extracted folder to gd_openocd
    renamed_folder = os.path.join(temp_folder, gd_openocd_folder_name)
    os.rename(os.path.join(temp_folder, os.listdir(temp_folder)[0]), renamed_folder)

    # Move the renamed folder to NucleiStudio/toolchain/
    destination_folder = os.path.join(tools_folder, "NucleiStudio", "toolchain", gd_openocd_folder_name)
    shutil.move(renamed_folder, destination_folder)

    # Copy and modify gd_openocd.json
    gd_openocd_json_path = os.path.join(destination_folder, "package.json")
    modify_json_file(os.path.join(PIOJSONLOC, "gd_openocd.json"), gd_openocd_json_path, system_value)

    # Remove the temporary extraction folder
    shutil.rmtree(temp_folder)


PIOJSONLOC = ".github"

nuclei_win_url = "https://download.nucleisys.com/upload/files/nucleistudio/NucleiStudio_IDE_202310-win64.zip"
gd_openocd_win_url = "https://download.nucleisys.com/upload/files/toochain/openocd/gd32-openocd-0.11.0-3-win32-x64.zip"
nuclei_linux_url = "https://download.nucleisys.com/upload/files/nucleistudio/NucleiStudio_IDE_202310-lin64.tgz"
gd_openocd_linux_url = "https://download.nucleisys.com/upload/files/toochain/openocd/gd32-openocd-0.11.0-3-linux-x64.tar.gz"

REUSE_ARCHIVE = True

def prepare_tools():
    if platform.system() == "Windows":
        # Windows Setup
        setup_nuclei_studio(PREBLT_TOOLS, nuclei_win_url, ["windows_amd64"], REUSE_ARCHIVE)
        setup_gd_openocd(PREBLT_TOOLS, gd_openocd_win_url, ["windows_amd64"], "gd_openocd", REUSE_ARCHIVE)
    elif platform.system() == "Linux":
        # Linux Setup
        setup_nuclei_studio(PREBLT_TOOLS, nuclei_linux_url, ["linux_x86_64"], REUSE_ARCHIVE)
        setup_gd_openocd(PREBLT_TOOLS, gd_openocd_linux_url, ["linux_x86_64"], "gd_openocd", REUSE_ARCHIVE)

    pass

def install_pio_packages(nsdk_url="https://github.com/Nuclei-Software/nuclei-sdk#feature/gd32vw55x"):
    if os.path.isfile("platform.py") == False:
        print("Not in platform nuclei folder, exit")
        return False
    try:
        import platformio as pio
    except:
        print("PlatformIO maybe not installed or not set in PATH, please check!")
        return False
    if pio.VERSION[0] < 6:
        print("PlatformIO %s need to >= 6.x, see https://docs.platformio.org/en/latest/core/history.html#platformio-core-6" % (".".join(pio.VERSION)))
        return False
    nucleistudio_loc = os.path.join(os.getcwd(), PREBLT_TOOLS, "NucleiStudio", "toolchain")
    os.system("pio pkg install -g -t symlink://%s" % (os.path.join(nucleistudio_loc, "gcc")))
    os.system("pio pkg install -g -t symlink://%s" % (os.path.join(nucleistudio_loc, "openocd")))
    os.system("pio pkg install -g -t symlink://%s" % (os.path.join(nucleistudio_loc, "gd_openocd")))
    print("Install Nuclei SDK from %s" % (nsdk_url))
    os.system("pio pkg install -g -t %s" % (nsdk_url))
    print("Install platform nuclei from current folder!")
    os.system("pio pkg install -g -p symlink://%s" % (os.getcwd()))
    print("List installed pio packages")
    os.system("pio pkg list -g")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare Nuclei Tools and Install PIO Packages.')
    parser.add_argument('--sdk', "-s", default="https://github.com/Nuclei-Software/nuclei-sdk#feature/gd32vw55x", help='URL or PATH of Nuclei SDK')
    parser.add_argument('--pio', action='store_true', help="Setup PIO Package")

    args = parser.parse_args()

    if os.path.isdir(PREBLT_TOOLS):
        print("%s existed, maybe tools already installed!" % (PREBLT_TOOLS))
    else:
        prepare_tools()

    if args.pio:
        print("Install pio required packages")
        install_pio_packages(args.sdk)

    print("Setup completed successfully!")
    sys.exit(0)
