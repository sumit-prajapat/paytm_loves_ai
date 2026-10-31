import datetime
import os
import sqlite3
import sys

BACKUP_DIR = "backups"
SOURCE_DB = "saarthi.db"


def backup_database(source_path: str = SOURCE_DB, backup_dir: str = BACKUP_DIR) -> str:
    """Performs a non-blocking, transaction-safe SQLite backup using the native sqlite3 backup API."""
    if not os.path.exists(source_path):
        print(f"Error: Source database '{source_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.join(backup_dir, f"saarthi_backup_{timestamp}.db")

    print(f"Starting online SQLite backup from '{source_path}' to '{dest_path}'...")
    src_conn = sqlite3.connect(source_path)
    dst_conn = sqlite3.connect(dest_path)

    try:
        with dst_conn:
            # Native backup step-by-step to avoid long locking
            src_conn.backup(dst_conn, pages=100)
        size_kb = os.path.getsize(dest_path) / 1024.0
        print(f"Backup completed successfully! Destination: {dest_path} ({size_kb:.1f} KB)")
        return dest_path
    finally:
        dst_conn.close()
        src_conn.close()


if __name__ == "__main__":
    backup_database()
