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

def run_cmd(cmd):
    print(cmd)
    return os.system(cmd)

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

def modify_json_file(old_file, file_path, system_value, force=False):
    if os.path.isfile(file_path):
        print("%s already existed!" % (file_path))
        if force == False:
            return
        print("Force reinstall this %s file!")

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

def check_isdir(uri):
    try:
        return os.path.isdir(uri)
    except:
        return False

def setup_nuclei_studio(toolsdir, nuclei_uri, system_value, reuse, force=False):
    if check_isdir(nuclei_uri) == False:
        # Download and extract NucleiStudio
        nuclei_folder = toolsdir
        download_and_extract(nuclei_uri, nuclei_folder, reuse)
        # Fix nuclei studio path
        for item in os.listdir(nuclei_folder):
            itemdir = os.path.join(nuclei_folder, item)
            if os.path.isdir(itemdir) and item.startswith("NucleiStudio") and item != "NucleiStudio":
                nsidepath = os.path.join(nuclei_folder, item)
                newpath = os.path.join(nuclei_folder, "NucleiStudio")
                if len(os.listdir(nsidepath)) == 1:
                    nsidepath = os.path.join(nsidepath, "NucleiStudio")
                # rename old ide path to new ide path
                # such as NucleiStudio_IDE_202310/NucleiStudio -> NucleiStudio
                print("Move %s -> %s" % (nsidepath, newpath))
                os.rename(nsidepath, newpath)
                break
        nsideloc = os.path.join(nuclei_folder, "NucleiStudio")
    else:
        nsideloc = nuclei_uri

    # Copy and modify nuclei_openocd.json
    openocd_json_path = os.path.join(nsideloc, "toolchain", "openocd", "package.json")
    modify_json_file(os.path.join(PIOJSONLOC, "openocd.json"), openocd_json_path, system_value, force)

    # Copy and modify nuclei_gcc.json
    gcc_json_path = os.path.join(nsideloc, "toolchain", "gcc", "package.json")
    modify_json_file(os.path.join(PIOJSONLOC, "gcc.json"), gcc_json_path, system_value, force)
    pass

def setup_gd_openocd(toolsdir, gd_openocd_uri, system_value, nsideloc, reuse, force=False):
    gd_openocd_folder_name = "gd_openocd"
    destination_folder = os.path.join(nsideloc, "toolchain", gd_openocd_folder_name)
    temp_folder = None
    if check_isdir(gd_openocd_uri) == False:
        # Download and extract gd32-openocd to a temporary folder
        tools_folder = toolsdir
        temp_folder = os.path.join(tools_folder, "temp_gd_openocd")
        if temp_folder and os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder)
        download_and_extract(gd_openocd_uri, temp_folder, reuse)
        org_folder = os.path.join(temp_folder, os.listdir(temp_folder)[0])
    else:
        org_folder = gd_openocd_uri
    if os.path.isdir(os.path.join(org_folder, "scripts")) == False:
        print("This %s may not be a valid openocd package!" % (org_folder))
        sys.exit(1)
    # Rename the old openocd folder to gd_openocd
    if os.path.isdir(destination_folder) == False:
        print("Copy %s -> %s" % (org_folder, destination_folder))
        shutil.copytree(org_folder, destination_folder)
    else:
        print("%s already exist!" % (destination_folder))
    
    # Remove the temporary extraction folder
    if temp_folder and os.path.isdir(temp_folder):
        shutil.rmtree(temp_folder)

    # Copy and modify gd_openocd.json
    gd_openocd_json_path = os.path.join(destination_folder, "package.json")
    modify_json_file(os.path.join(PIOJSONLOC, "gd_openocd.json"), gd_openocd_json_path, system_value, force)
    pass


PIOJSONLOC = ".github"
REUSE_ARCHIVE = True

def is_valid_url(url):
    try:
        if url and urlparse(url).netloc != "":
            return True
    except:
        pass
    return False

def prepare_tools(prebltloc=PREBLT_TOOLS, nside=None, gdocd=None, force=False):
    ostype = platform.system()
    print("Setup Tools for %s" % (ostype))
    if platform.architecture()[0] != '64bit':
        print("ERROR: Currently only support 64bit OS!")
        sys.exit(1)
    # if you provide a real installed nuclei studio path
    nsideloc = os.path.join(prebltloc, "NucleiStudio")
    # you can customize the url to your own url
    nuclei_win_url = "https://download.nucleisys.com/upload/files/nucleistudio/NucleiStudio_IDE_202310-win64.zip"
    gd_openocd_win_url = "https://download.nucleisys.com/upload/files/toochain/openocd/gd32-openocd-0.11.0-3-win32-x64.zip"
    nuclei_linux_url = "https://download.nucleisys.com/upload/files/nucleistudio/NucleiStudio_IDE_202310-lin64.tgz"
    gd_openocd_linux_url = "https://download.nucleisys.com/upload/files/toochain/openocd/gd32-openocd-0.11.0-3-linux-x64.tar.gz"

    nside_uri = None
    gdocd_uri = None
    supported_oses = []
    if ostype == "Windows":
        # Windows Setup
        nside_uri = nuclei_win_url
        gdocd_uri = gd_openocd_win_url
        supported_oses = ["windows_amd64"]
    elif ostype == "Linux":
        # Linux Setup
        nside_uri = nuclei_linux_url
        gdocd_uri = gd_openocd_linux_url
        supported_oses = ["linux_x86_64"]
    else:
        print("ERROR: Unsupported OS")
        sys.exit(1)

    # if nside or gdocd are specified
    if nside and (os.path.isdir(nside) and os.path.isfile(os.path.join(nside, "NucleiStudio.ini"))):
        print("INFO: Using already installed Nuclei Studio in %s!" % (nside))
        nside_uri = nside
        nsideloc = nside
    elif is_valid_url(nside):
        print("INFO: Using a different url %s to download Nuclei Studio!" % (nside))
        nside_uri = nside
    if gdocd and os.path.isdir(gdocd) and os.path.isdir(os.path.join(gdocd, "scripts")):
        print("INFO: Using already installed GD OpenOCD in %s!" % (gdocd))
        gdocd_uri = gdocd
    elif is_valid_url(gdocd):
        print("INFO: Using a different url %s to download gd32 openocd!" % (gdocd))
        gdocd_uri = nside

    setup_nuclei_studio(prebltloc, nside_uri, supported_oses, REUSE_ARCHIVE, force)
    setup_gd_openocd(prebltloc, gdocd_uri, supported_oses, nsideloc, REUSE_ARCHIVE, force)
    pass

def get_nside_loc(prebltloc=PREBLT_TOOLS, nside=None):
    if nside and os.path.isdir(nside) and os.path.isfile(os.path.join(nside, "NucleiStudio.ini")):
        return nside
    return os.path.join(prebltloc, "NucleiStudio")


def install_pio_packages(nsideloc=os.path.join(os.getcwd(), PREBLT_TOOLS, "NucleiStudio"), nsdk_url="https://github.com/Nuclei-Software/nuclei-sdk#feature/gd32vw55x"):
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
    nside_tools_loc = os.path.join(nsideloc, "toolchain")
    if os.path.isdir(nside_tools_loc) == False:
        print("%s not exist! Please Check!" % (nside_tools_loc))
        sys.exit(1)
    print("Install required tool packages located in %s" % (nside_tools_loc))
    sys.stdout.flush()
    run_cmd("pio pkg install -g -t symlink://%s" % (os.path.join(nside_tools_loc, "gcc")))
    run_cmd("pio pkg install -g -t symlink://%s" % (os.path.join(nside_tools_loc, "openocd")))
    run_cmd("pio pkg install -g -t symlink://%s" % (os.path.join(nside_tools_loc, "gd_openocd")))
    print("Install framework-nuclei-sdk from %s" % (nsdk_url))
    sys.stdout.flush()
    if os.path.isdir(nsdk_url):
        run_cmd("pio pkg install -g -t symlink://%s" % (os.path.realpath(nsdk_url)))
    else:
        run_cmd("pio pkg install -g -t %s" % (nsdk_url))
    print("Install platform-nuclei from current folder!")
    run_cmd("pio pkg install -g -p symlink://%s" % (os.getcwd()))
    print("List installed pio packages")
    sys.stdout.flush()
    run_cmd("pio pkg list -g")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prepare Nuclei Tools and Install PIO Packages.')
    parser.add_argument('--install', action='store_true', help="Always install required tools")
    parser.add_argument('--into', default=PREBLT_TOOLS, help="Install required tools to desired location")
    parser.add_argument('--pio', action='store_true', help="Setup PIO Package")
    parser.add_argument('--sdk', "-s", default="https://github.com/Nuclei-Software/nuclei-sdk#feature/gd32vw55x", help='URL or PATH of Nuclei SDK')
    parser.add_argument('--ide', help='Nuclei Studio IDE PATH, such as C:\\Software\\NucleiStudio')
    parser.add_argument('--gdocd', help='GD OpenOCD PATH, such as C:\\Work\\openocd_v1.2.2\\xpack-openocd-0.11.0-3')
    parser.add_argument('--force', action='store_true', help='Force reinstall the package.json file if existed!')

    args = parser.parse_args()

    needinstall = True
    if os.path.isdir(PREBLT_CACHE):
        print("Prebuilt tool download cache directory existed!")
        print("Content in this directory: %s" % (os.listdir(PREBLT_CACHE)))
    else:
        print("No prebuilt tool download cache found!")

    prebuiltloc = args.into
    if os.path.isdir(prebuiltloc) and len(os.listdir(prebuiltloc)) >= 1:
        needinstall = False
        print("%s existed, maybe tools already installed!" % (prebuiltloc))
        if args.install:
            if prebuiltloc == PREBLT_TOOLS:
                shutil.rmtree(prebuiltloc)
            needinstall = True

    if needinstall:
        prepare_tools(prebuiltloc, args.ide, args.gdocd, args.force)

    nsideloc = get_nside_loc(prebuiltloc, args.ide)
    if args.pio:
        print("Install pio required packages")
        install_pio_packages(nsideloc, args.sdk)

    print("Setup completed successfully!")
    sys.exit(0)
