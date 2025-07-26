import os
import requests
from datetime import datetime, timedelta


# 🔒 Global configuration for github access
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "SMenon-14/Flake_Tracker"
BRANCH = "main"
IMAGES_PATH = "Images"

# How long should images exist in the image folder on github
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
    resp = requests.get(url, headers=headers) # <--- Get a JSON array of objects representing the files in our folder
    resp.raise_for_status() # <--- Check if we got an error
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
    return jpg_files # <--- return our modified list

def get_last_commit_timestamp(path):
    """A method that get's the upload/commit timestamp associated with a given file at the github path

    Args:
        path (str): A string that represents the file that we want to find the last commit timestamp for

    Returns:
        str: A string representing the commit timestamp (datetime) of a given image at the specified path
    """
    url = f"https://api.github.com/repos/{REPO}/commits" # <--- URL to get the commit history for our repository
    params = {"path": path, "sha": BRANCH, "per_page": 1} # <--- Parameters for our request to get the commits (we only want commits that affected the image at "path" in our branch)
    resp = requests.get(url, headers=headers, params=params) # <--- Submit our request for commit data
    resp.raise_for_status() # <--- Check for errors that occured
    commit_data = resp.json() # <--- Get the commit data as a JSON array
    if not commit_data: # <--- If we didn't get any data, return None
        return None
    return commit_data[0]["commit"]["committer"]["date"] # <--- Return the commit date for our file

def delete_file(path, sha):
    """Deletes a file at the given path

    Args:
        path (str): The path to the image we want to delete
        sha (str): The unique identifier of the image we want to delete
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{path}" # <--- the URL path to the image we want to delete
    data = {"message": f"Delete old image {path}", "branch": BRANCH, "sha": sha} # <--- The data we will pass in our delete request
    resp = requests.delete(url, headers=headers, json=data) # <--- submit our delete file request
    if resp.status_code == 200: # <--- check if our request was successful
        print(f"✅ Deleted {path}")
    else:
        print(f"❌ Failed to delete {path}: {resp.text}")

def main():
    files = filter_jpg_files(list_files()) # <--- gets a list of all the JPG files at our given GitHub location
    now = datetime.utcnow() # <--- gets the current time
    cutoff = now - timedelta(hours=MAX_AGE_HOURS) # <--- finds the cutoff timestamp by subtracting the max-age from the current time

    for f in files: # <--- iterates over all the JPG files we found
        path = f["path"] # <--- gets the path of our image
        sha = f["sha"] # <--- gets the unique identifier of our image

        commit_time_str = get_last_commit_timestamp(path) # <--- finds the commit time of the image we are looking at
        if not commit_time_str: # <--- handle error in which we can't get a commit time from our image
            print(f"⚠️ Could not get commit time for {path}, skipping.")
            continue

        commit_time = datetime.strptime(commit_time_str, "%Y-%m-%dT%H:%M:%SZ") # <--- converts the string returned by get_last_commit_timestamp() into a DateTime object to make it comparable

        if commit_time < cutoff: # <--- if our commit time is older than the cutoff 
            delete_file(path, sha) # <--- delete our file 
        else:
            print(f"🕒 Keeping {path} (last modified {commit_time_str})") # <--- the case where our file is not old enough to be deleted

if __name__ == "__main__":
    main()
