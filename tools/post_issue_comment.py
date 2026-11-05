#!/usr/bin/env python3
"""Post a comment to a GitHub issue on the repository using the local git credentials.

Usage:
    python tools/post_issue_comment.py --issue 4 --message "Thanks for reporting..."
"""
import argparse
import json
import subprocess
import sys
import urllib.request

REPO = "STS78721/totk-pc-recomp-SteelTempleBuild"

def get_token():
    try:
        p = subprocess.Popen(
            ["git", "credential", "fill"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, _ = p.communicate("protocol=https\nhost=github.com\n")
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception as e:
        sys.exit(f"Failed to retrieve git credentials: {e}")
    sys.exit("No token found in git credential helper.")

def post_comment(issue: int, message: str):
    token = get_token()
    url = f"https://api.github.com/repos/{REPO}/issues/{issue}/comments"
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "SteelTemple-Issue-Helper",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    data = json.dumps({"body": message}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            rj = json.loads(resp.read().decode("utf-8"))
            print(f"Comment posted successfully to Issue #{issue}: {rj.get('html_url')}")
    except Exception as e:
        sys.exit(f"Failed to post comment to Issue #{issue}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post a comment to a GitHub issue.")
    parser.add_argument("--issue", type=int, required=True, help="Issue number")
    parser.add_argument("--message", type=str, required=True, help="Comment body")
    args = parser.parse_args()
    post_comment(args.issue, args.message)
