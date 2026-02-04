"""
Batch job for computing user similarities.

This script should be run periodically (e.g., nightly) to recompute
similarities as new users import their libraries.

Run with: python -m app.scripts.compute_similarities
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import SessionLocal
from app.services.similarity import compute_all_similarities


def progress_callback(current: int, total: int):
    """Print progress updates."""
    percent = int(current / total * 100)
    bar_length = 40
    filled = int(bar_length * current / total)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r  [{bar}] {percent}% ({current}/{total})", end="", flush=True)


def main():
    """Run batch similarity computation."""
    print("Starting batch similarity computation...\n")
    start_time = time.time()

    db = SessionLocal()

    try:
        print("Computing similarities for all users...")
        stats = compute_all_similarities(db, progress_callback=progress_callback)

        # Print final newline after progress bar
        print()

        elapsed = time.time() - start_time

        print("\n=== Computation Complete ===")
        print(f"Time elapsed: {elapsed:.1f} seconds")
        print(f"Users processed: {stats['users_processed']}")
        print(f"Users skipped (not enough data): {stats['users_skipped']}")
        print(f"Total similarities computed: {stats['similarities_computed']}")

        if stats["users_processed"] > 0:
            avg_neighbors = stats["similarities_computed"] / stats["users_processed"]
            print(f"Average neighbors per user: {avg_neighbors:.1f}")

        print("\n✓ Batch job complete!")

    except Exception as e:
        print(f"\n✗ Error during computation: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
