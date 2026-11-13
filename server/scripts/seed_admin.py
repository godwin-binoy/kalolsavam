"""Backward-compatibility wrapper for python -m server.scripts.seed_admin."""
import sys
from server.cli import seed_admin

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@kalolsavam.example.com"
    seed_admin(email=email)
