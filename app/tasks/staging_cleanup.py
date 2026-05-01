"""Staging photo TTL cleanup task (B7)."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StagingPhotoTable

logger = logging.getLogger(__name__)

_TTL_DAYS = 7
_ORPHAN_GRACE_SECONDS = 60  # Don't reap files modified within last 60s (in-flight uploads)
_CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour


async def run_staging_cleanup(session: AsyncSession, storage_root: str) -> None:
    """
    Run the staging photo cleanup:

    1. Delete rows older than 7 days (and their files).
    2. Reap orphan files in staging/{user_id}/ not referenced by any current DB row.

    Safe to call at startup and on a 1-hour schedule.
    """
    root = Path(storage_root)
    cutoff = datetime.now(timezone.utc) - timedelta(days=_TTL_DAYS)
    cutoff_naive = cutoff.replace(tzinfo=None)

    # --- Step 1: TTL cleanup ---
    result = await session.execute(
        select(StagingPhotoTable).where(StagingPhotoTable.created_at < cutoff_naive)
    )
    expired_rows = result.scalars().all()

    for row in expired_rows:
        # Delete files
        for key in (row.storage_key, row.thumbnail_key):
            if key:
                try:
                    (root / key).unlink()
                    logger.debug("TTL: deleted file %s", key)
                except FileNotFoundError:
                    pass
                except OSError as e:
                    logger.warning("TTL: could not delete file %s: %s", key, e)

        await session.execute(
            delete(StagingPhotoTable).where(StagingPhotoTable.id == row.id)
        )

    await session.commit()
    logger.info("TTL cleanup: deleted %d expired staging rows", len(expired_rows))

    # --- Step 2: Orphan file reaper ---
    staging_dir = root / "staging"
    if not staging_dir.exists():
        return

    now_ts = time.time()

    for user_dir in staging_dir.iterdir():
        if not user_dir.is_dir():
            continue

        try:
            user_id = int(user_dir.name)
        except ValueError:
            continue

        # Build set of referenced keys for this user
        result = await session.execute(
            select(StagingPhotoTable.storage_key, StagingPhotoTable.thumbnail_key).where(
                StagingPhotoTable.user_id == user_id
            )
        )
        referenced_keys: set[str] = set()
        for storage_key, thumbnail_key in result.all():
            if storage_key:
                referenced_keys.add(storage_key)
            if thumbnail_key:
                referenced_keys.add(thumbnail_key)

        # Check each file
        for file_path in user_dir.iterdir():
            if not file_path.is_file():
                continue

            # Race-protection: skip recently modified files
            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                continue

            if now_ts - mtime < _ORPHAN_GRACE_SECONDS:
                continue

            # Compute relative path from storage_root
            try:
                relative_key = str(file_path.relative_to(root))
            except ValueError:
                continue

            if relative_key not in referenced_keys:
                try:
                    file_path.unlink()
                    logger.debug("Orphan: deleted %s", relative_key)
                except OSError as e:
                    logger.warning("Orphan: could not delete %s: %s", relative_key, e)


async def _cleanup_loop(session_factory, storage_root: str) -> None:
    """Background task: run cleanup at startup, then every hour."""
    while True:
        try:
            async with session_factory() as session:
                await run_staging_cleanup(session, storage_root)
        except Exception:
            logger.exception("Staging cleanup loop error")
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
