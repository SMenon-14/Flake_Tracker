import os
import requests
from datetime import datetime, timedelta

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "SMenon-14/Flake_Tracker"
BRANCH = "main"
IMAGES_PATH = "Images"
MAX_AGE_HOURS = 12

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def list_files():
    url = f"https://api.github.com/repos/{REPO}/contents/{IMAGES_PATH}?ref={BRANCH}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def get_last_commit_timestamp(path):
    url = f"https://api.github.com/repos/{REPO}/commits"
    params = {"path": path, "sha": BRANCH, "per_page": 1}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    commit_data = resp.json()
    if not commit_data:
        return None
    return commit_data[0]["commit"]["committer"]["date"]

def delete_file(path, sha):
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
    files = list_files()
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
