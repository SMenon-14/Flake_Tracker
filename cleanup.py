import os
import requests
from datetime import datetime, timedelta


# 🔒 Global configuration for github access
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "SMenon-14/Flake_Tracker"
BRANCH = "main"
IMAGES_PATH = "Images"

# How long should images exist in the image github
MAX_AGE_HOURS = 12

# Request header setup for pulling github information
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def list_files():
    """ Returns a list of all the files at the given location in the repo.

    Returns:
        List: A list of dicts representing all the files at the given location in the repo with their identifying 
              information
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{IMAGES_PATH}?ref={BRANCH}" # <--- the url of the location that we want to find files in within our repo
    resp = requests.get(url, headers=headers) # <---
    resp.raise_for_status() # <---
    return resp.json() # <--- return our list

def filter_jpg_files(all_files):
    """ Filters a list of files to only contain the .jpg entries.

    Args:
        all_files (List): A list of dicts representing all the files at the given location in the repo with their 
                          identifying information

    Returns:
        List: A list of dicts representing all the jpg files at the given location in the repo with their identifying 
              information
    """
    jpg_files = [f for f in all_files if f['name'].lower().endswith('.jpg')] # <--- a filter that only lets files whose filename ends with ".jpg" pass
    return jpg_files

def get_last_commit_timestamp(path):
    """_summary_

    Args:
        path (_type_): _description_

    Returns:
        _type_: _description_
    """
    url = f"https://api.github.com/repos/{REPO}/commits"
    params = {"path": path, "sha": BRANCH, "per_page": 1}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    commit_data = resp.json()
    if not commit_data:
        return None
    return commit_data[0]["commit"]["committer"]["date"]

def delete_file(path, sha):
    """_summary_

    Args:
        path (_type_): _description_
        sha (_type_): _description_
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    data = {
        "message": f"Delete old image {path}",
        "branch": BRANCH,
        "sha": sha
    }
    resp = requests.delete(url, headers=headers, json=data)
    if resp.status_code == 200:
        print(f"✅ Deleted {path}")
    else:
        print(f"❌ Failed to delete {path}: {resp.text}")

def main():
    """
    """
    files = filter_jpg_files(list_files())
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)

    for f in files:
        path = f["path"]
        sha = f["sha"]

        commit_time_str = get_last_commit_timestamp(path)
        if not commit_time_str:
            print(f"⚠️ Could not get commit time for {path}, skipping.")
            continue

        commit_time = datetime.strptime(commit_time_str, "%Y-%m-%dT%H:%M:%SZ")

        if commit_time < cutoff:
            delete_file(path, sha)
        else:
            print(f"🕒 Keeping {path} (last modified {commit_time_str})")

if __name__ == "__main__":
    main()
