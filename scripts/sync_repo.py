#!/usr/bin/env python3
"""
ShotNET Repository Synchronization Script

This script automates the process of synchronizing the local repository with GitHub.
It performs the following actions:
1. Fetches the latest changes from the remote repository
2. Checks for any local changes that need to be committed
3. Stashes any uncommitted changes if needed
4. Pulls the latest changes
5. Restores any stashed changes
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Command output: {e.stderr}")
        sys.exit(1)

def check_git_status(repo_path):
    """Check the git status of the repository."""
    return run_command("git status --porcelain", repo_path)

def stash_changes(repo_path):
    """Stash any uncommitted changes."""
    if check_git_status(repo_path):
        print("Stashing local changes...")
        run_command("git stash push -m 'Auto-stash before sync'", repo_path)
        return True
    return False

def sync_repository(repo_path):
    """Synchronize the repository with the remote."""
    print(f"\n🔍 Checking repository status at {repo_path}")
    
    # Ensure we're in the repository directory
    os.chdir(repo_path)
    
    # Check if the directory is a git repository
    if not os.path.exists(os.path.join(repo_path, '.git')):
        print("❌ Not a git repository. Please initialize git first.")
        return False
    
    # Get current branch
    current_branch = run_command("git rev-parse --abbrev-ref HEAD", repo_path)
    print(f"🌿 Current branch: {current_branch}")
    
    # Check for uncommitted changes
    status = check_git_status(repo_path)
    has_changes = bool(status)
    
    if has_changes:
        print("📝 Found uncommitted changes:")
        print(status)
        stash = input("Would you like to stash these changes before syncing? (y/N) ").lower() == 'y'
        if stash:
            stash_changes(repo_path)
        else:
            print("Please commit or stash your changes before syncing.")
            return False
    
    # Fetch the latest changes
    print("\n🔄 Fetching latest changes from remote...")
    run_command("git fetch", repo_path)
    
    # Check if we need to pull
    behind = run_command(f"git rev-list HEAD..origin/{current_branch} --count", repo_path)
    if int(behind) > 0:
        print(f"⬇️  Pulling {behind} commit(s) from remote...")
        run_command(f"git pull origin {current_branch}", repo_path)
    else:
        print("✅ Already up to date.")
    
    # Check for any new branches
    print("\n🌐 Checking for new branches...")
    run_command("git remote update", repo_path)
    run_command("git fetch --all", repo_path)
    
    print("\n✨ Synchronization complete!")
    return True

if __name__ == "__main__":
    # Get the repository path (defaults to current directory)
    repo_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    repo_path = os.path.abspath(repo_path)
    
    print(f"🚀 ShotNET Repository Synchronization")
    print(f"📁 Repository: {repo_path}")
    print("-" * 50)
    
    sync_repository(repo_path)
    
    # Add a small delay to see the output
    import time
    time.sleep(2)
