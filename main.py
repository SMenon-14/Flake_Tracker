import sys
import subprocess
import os

def install_package(package):
    """Install the given package on the system

    Args:
        package (str): The name of the package we want to install.
    """
    # implement pip as a subprocess:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    # process output with an API in the subprocess module:
    subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])

def install_all_requirements():
    """ Reads from requirements.txt file if present and then installs all needed packages.
    """
    if not os.path.exists('requirements.txt'): # <--- check if we can find a file with that name in the same directory as the program is being run from
        return [] # <--- Returning empty list
    # Note that the above if statement guarantees that if the file does not exist we do not try to open it. If we try to open a file in read mode without it existing, it will return an error.
    with open('requirements.txt', "r") as f: # <--- open a file with the given file name in reading mode (we are not planning to modify the file)
        packages = [line.strip() for line in f.readlines() if line.strip()]
        for package in packages:
            install_package(package) # <--- install all necessary packages as stated in requirements


install_all_requirements()
exec(open("flake_tracker.py").read()) # <--- run flake_tracker
