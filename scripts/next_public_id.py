"""Utility to print the next public order ID."""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, compute_next_public_id


def main():
    app = create_app()
    with app.app_context():
        print(compute_next_public_id())


if __name__ == "__main__":
    main()
