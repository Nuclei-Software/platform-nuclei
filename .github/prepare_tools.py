import os
import zipfile
import tarfile
import shutil
import json
import requests
import wget  # Import the wget library
from urllib.parse import urlparse
import argparse

PIOJSONLOC = ""
PREBLT_CACHE = "prebuilt_dlcache"
PREBLT_TOOLS = "prebuilt_tools"

def download_with_progress(url, destination_folder, reuse=False):
    file_name = os.path.join(destination_folder, os.path.basename(urlparse(url).path))

    if os.path.isdir(destination_folder) == False:
        os.makedirs(destination_folder)
    if reuse == False and os.path.isfile(file_name):
        os.remove(file_name)
    # Download the file with progress bar
    if os.path.isfile(file_name) == False:
        wget.download(url, file_name)

    return file_name

def download_and_extract(url, extract_folder, reuse=False):
    print("Downloading %s" % (url))
    file_name = download_with_progress(url, PREBLT_CACHE, reuse)
    # Download the file using stream to avoid loading the entire file into memory
    #with requests.get(url, stream=True) as response:
    #    with open(file_name, 'wb') as file:
    #        shutil.copyfileobj(response.raw, file)

    if os.path.isdir(extract_folder) == False:
        os.makedirs(extract_folder)

    print("Extracting %s to %s" % (file_name, extract_folder))
    # Extract the contents
    if file_name.endswith(".zip"):
        with zipfile.ZipFile(file_name, "r") as zip_ref:
            zip_ref.extractall(extract_folder)
    elif file_name.endswith(".tar.gz"):
        with tarfile.open(file_name, "r:gz") as tar_ref:
            tar_ref.extractall(extract_folder)

    # Remove the temporary file
    if reuse == False and os.path.isfile(file_name):
        os.remove(file_name)

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

def prepare_tools():
    if platform.system() == "Windows":
        # Windows Setup
        setup_nuclei_studio(PREBLT_TOOLS, nuclei_win_url, ["windows_amd64"], True)
        setup_gd_openocd(PREBLT_TOOLS, gd_openocd_win_url, ["windows_amd64"], "gd_openocd", True)
    elif platform.system() == "Linux":
        # Linux Setup
        setup_nuclei_studio(PREBLT_TOOLS, nuclei_linux_url, ["linux_x86_64"], True)
        setup_gd_openocd(PREBLT_TOOLS, gd_openocd_linux_url, ["linux_x86_64"], "gd_openocd", True)

    pass

def install_pio_packages(nsdk_url="https://github.com/Nuclei-Software/nuclei-sdk#feature/gd32vw55x"):
    print("Install pio required packages")
    if os.path.isfile("platform.py") == False:
        print("Not in platform nuclei folder, exit")
        return
    nucleistudio_loc = os.path.join(os.getcwd(), PREBLT_TOOLS, "NucleiStudio", "toolchain")
    os.system("pio pkg install -g -t symlink://%s" % (os.path.join(nucleistudio_loc, "gcc")))
    os.system("pio pkg install -g -t symlink://%s" % (os.path.join(nucleistudio_loc, "openocd")))
    os.system("pio pkg install -g -t symlink://%s" % (os.path.join(nucleistudio_loc, "gd_openocd")))
    print("Install Nuclei SDK from %s" % (nsdk_url))
    os.system("pio pkg install -g -t %s" % (nsdk_url))
    print("Install platform nuclei from current folder!")
    os.system("pio pkg install -g -p symlink://%s" % (os.getcwd()))
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare Nuclei Tools and Install PIO Packages.')
    parser.add_argument('--sdk', "-s", required=True, default="https://github.com/Nuclei-Software/nuclei-sdk#feature/gd32vw55x", help='URL or PATH of Nuclei SDK')

    args = parser.parse_args()

    if os.path.isdir(PREBLT_TOOLS):
        print("%s existed, maybe tools already installed!" % (PREBLT_TOOLS))
    else:
        prepare_tools()
    
    install_pio_packages(args.nsdk)

    print("Setup completed successfully!")
