#!/usr/bin/env python3
"""
Database backup utility for Poolula Platform

Automated daily backups of SQLite database with retention policy:
- 7 daily backups (last 7 days)
- 4 weekly backups (last 4 weeks, keep Sunday)
- 12 monthly backups (last 12 months, keep 1st of month)

Usage:
    python scripts/backup.py                    # Create backup
    python scripts/backup.py --restore latest   # Restore from latest
    python scripts/backup.py --list            # List all backups
    python scripts/backup.py --clean           # Apply retention policy

Author: Poolula Platform
Date: 2025-11-13
"""

import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import argparse
import sys


class DatabaseBackup:
    """
    Handles database backup and restore operations

    Attributes:
        db_path: Path to the SQLite database file
        backup_dir: Directory where backups are stored
    """

    def __init__(self, db_path: Path, backup_dir: Path):
        """
        Initialize backup manager

        Args:
            db_path: Path to database file (e.g., poolula.db)
            backup_dir: Directory for storing backups
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Path:
        """
        Create a new backup of the database

        Uses timestamp-based naming: poolula_YYYYMMDD_HHMMSS.db

        Returns:
            Path to the created backup file

        Raises:
            FileNotFoundError: If database file doesn't exist
            IOError: If backup creation fails
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"poolula_{timestamp}.db"
        backup_path = self.backup_dir / backup_name

        # Use SQLite backup API (safer than file copy during writes)
        try:
            source = sqlite3.connect(str(self.db_path))
            dest = sqlite3.connect(str(backup_path))
            source.backup(dest)
            source.close()
            dest.close()

            print(f"✅ Backup created: {backup_path}")
            print(f"   Size: {backup_path.stat().st_size / 1024:.1f} KB")
            return backup_path

        except Exception as e:
            if backup_path.exists():
                backup_path.unlink()  # Clean up failed backup
            raise IOError(f"Backup failed: {e}")

    def list_backups(self) -> List[tuple[datetime, Path]]:
        """
        List all available backups sorted by date (newest first)

        Returns:
            List of (timestamp, path) tuples
        """
        backups = []
        for backup_file in self.backup_dir.glob("poolula_*.db"):
            # Parse timestamp from filename: poolula_YYYYMMDD_HHMMSS.db
            try:
                ts_str = backup_file.stem.split("_", 1)[1]  # Get YYYYMMDD_HHMMSS
                timestamp = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                backups.append((timestamp, backup_file))
            except (ValueError, IndexError):
                print(f"⚠️  Skipping invalid backup filename: {backup_file.name}")
                continue

        backups.sort(reverse=True, key=lambda x: x[0])
        return backups

    def restore_backup(self, backup_path: Path) -> None:
        """
        Restore database from a backup file

        Creates a backup of current database before restoring

        Args:
            backup_path: Path to backup file to restore from

        Raises:
            FileNotFoundError: If backup file doesn't exist
            IOError: If restore operation fails
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        # Create backup of current state first
        if self.db_path.exists():
            current_backup = self.backup_dir / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(self.db_path, current_backup)
            print(f"📦 Current database backed up to: {current_backup.name}")

        # Restore from backup
        try:
            shutil.copy2(backup_path, self.db_path)
            print(f"✅ Database restored from: {backup_path.name}")
            print(f"   Restored to: {self.db_path}")
        except Exception as e:
            raise IOError(f"Restore failed: {e}")

    def apply_retention_policy(self) -> dict:
        """
        Apply retention policy: 7 daily, 4 weekly (Sunday), 12 monthly (1st)

        Returns:
            Dictionary with deletion statistics
        """
        backups = self.list_backups()
        if not backups:
            print("No backups found")
            return {"kept": 0, "deleted": 0}

        now = datetime.now()
        to_keep = set()

        # Keep last 7 daily backups
        daily_backups = [b for b in backups if (now - b[0]).days < 7]
        to_keep.update(b[1] for b in daily_backups)

        # Keep last 4 weekly backups (Sundays)
        weekly_backups = [
            b for b in backups
            if 7 <= (now - b[0]).days < 28 and b[0].weekday() == 6  # Sunday = 6
        ]
        to_keep.update(b[1] for b in weekly_backups[:4])

        # Keep last 12 monthly backups (1st of month)
        monthly_backups = [
            b for b in backups
            if (now - b[0]).days >= 28 and b[0].day == 1
        ]
        to_keep.update(b[1] for b in monthly_backups[:12])

        # Delete backups not in keep set
        deleted_count = 0
        for timestamp, backup_path in backups:
            if backup_path not in to_keep:
                backup_path.unlink()
                deleted_count += 1
                print(f"🗑️  Deleted old backup: {backup_path.name}")

        kept_count = len(to_keep)
        print(f"\n📊 Retention policy applied:")
        print(f"   Kept: {kept_count} backups")
        print(f"   Deleted: {deleted_count} backups")

        return {"kept": kept_count, "deleted": deleted_count}


def main():
    """Command-line interface for backup utility"""
    parser = argparse.ArgumentParser(
        description="Poolula Platform Database Backup Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/backup.py                    # Create new backup
  python scripts/backup.py --list             # List all backups
  python scripts/backup.py --restore latest   # Restore from latest
  python scripts/backup.py --clean            # Clean old backups
        """
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=Path("poolula.db"),
        help="Path to database file (default: poolula.db)"
    )

    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("backups"),
        help="Backup directory (default: backups/)"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available backups"
    )

    parser.add_argument(
        "--restore",
        type=str,
        metavar="BACKUP",
        help="Restore from backup (use 'latest' or filename)"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Apply retention policy and clean old backups"
    )

    args = parser.parse_args()

    backup_manager = DatabaseBackup(args.db, args.backup_dir)

    try:
        if args.list:
            # List backups
            backups = backup_manager.list_backups()
            if not backups:
                print("No backups found")
                return

            print(f"📦 Available backups ({len(backups)} total):\n")
            for i, (timestamp, path) in enumerate(backups, 1):
                age = datetime.now() - timestamp
                size = path.stat().st_size / 1024  # KB
                print(f"{i:2}. {timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
                      f"({age.days}d {age.seconds // 3600}h ago) - "
                      f"{size:.1f} KB - {path.name}")

        elif args.restore:
            # Restore from backup
            if args.restore.lower() == "latest":
                backups = backup_manager.list_backups()
                if not backups:
                    print("❌ No backups available to restore")
                    sys.exit(1)
                backup_path = backups[0][1]  # Most recent
            else:
                backup_path = args.backup_dir / args.restore

            backup_manager.restore_backup(backup_path)

        elif args.clean:
            # Clean old backups
            backup_manager.apply_retention_policy()

        else:
            # Create new backup (default action)
            backup_manager.create_backup()

            # Auto-clean if more than 20 backups
            backups = backup_manager.list_backups()
            if len(backups) > 20:
                print("\n📊 More than 20 backups found, applying retention policy...")
                backup_manager.apply_retention_policy()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
