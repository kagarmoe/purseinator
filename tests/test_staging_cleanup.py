"""Tests for staging TTL cleanup task (B7)."""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import StagingPhotoTable, UserTable

pytestmark = pytest.mark.anyio


async def _create_user(db_session, email: str) -> UserTable:
    user = UserTable(email=email, name="Cleanup Test", role="curator")
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_staging_file(root: Path, user_id: int, name: str) -> tuple[Path, Path]:
    """Create actual files and return (full_path, thumb_path)."""
    staging_dir = root / "staging" / str(user_id)
    staging_dir.mkdir(parents=True, exist_ok=True)
    full_path = staging_dir / name
    thumb_path = staging_dir / (name.replace(".jpg", ".thumb.jpg"))
    full_path.write_bytes(b"fake image data")
    thumb_path.write_bytes(b"fake thumb data")
    return full_path, thumb_path


async def test_cleanup_deletes_rows_older_than_7_days(db_session, db_session_factory, photo_storage_root):
    """Rows older than 7 days are deleted; fresh rows are kept."""
    from app.tasks.staging_cleanup import run_staging_cleanup

    root = Path(photo_storage_root)
    user = await _create_user(db_session, "cleanup_ttl@example.com")

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=8)
    fresh_time = now - timedelta(days=1)

    # Create old row
    old_full, old_thumb = await _make_staging_file(root, user.id, "old.jpg")
    old_row = StagingPhotoTable(
        user_id=user.id,
        storage_key=f"staging/{user.id}/old.jpg",
        thumbnail_key=f"staging/{user.id}/old.thumb.jpg",
        created_at=old_time.replace(tzinfo=None),
    )
    db_session.add(old_row)

    # Create fresh row
    fresh_full, fresh_thumb = await _make_staging_file(root, user.id, "fresh.jpg")
    fresh_row = StagingPhotoTable(
        user_id=user.id,
        storage_key=f"staging/{user.id}/fresh.jpg",
        thumbnail_key=f"staging/{user.id}/fresh.thumb.jpg",
        created_at=fresh_time.replace(tzinfo=None),
    )
    db_session.add(fresh_row)
    await db_session.commit()

    # Run cleanup
    async with db_session_factory() as session:
        await run_staging_cleanup(session, photo_storage_root)

    # Old row should be gone
    result = await db_session.execute(
        select(StagingPhotoTable).where(StagingPhotoTable.id == old_row.id)
    )
    assert result.scalar_one_or_none() is None, "Old row should be deleted"

    # Old files should be gone
    assert not old_full.exists(), "Old full file should be deleted"
    assert not old_thumb.exists(), "Old thumb file should be deleted"

    # Fresh row should remain
    result = await db_session.execute(
        select(StagingPhotoTable).where(StagingPhotoTable.id == fresh_row.id)
    )
    assert result.scalar_one_or_none() is not None, "Fresh row should remain"

    # Fresh files should remain
    assert fresh_full.exists(), "Fresh full file should remain"
    assert fresh_thumb.exists(), "Fresh thumb file should remain"


async def test_cleanup_reaps_orphan_staging_files(db_session, db_session_factory, photo_storage_root):
    """Files in staging/{uid}/ with no corresponding DB row are removed (if old enough)."""
    from app.tasks.staging_cleanup import run_staging_cleanup

    root = Path(photo_storage_root)
    user = await _create_user(db_session, "orphan_reap@example.com")

    # Create an orphan file (no DB row)
    orphan_dir = root / "staging" / str(user.id)
    orphan_dir.mkdir(parents=True, exist_ok=True)
    orphan_file = orphan_dir / "orphan.jpg"
    orphan_file.write_bytes(b"orphan file")

    # Make it old (> 60 seconds for race-protection)
    old_mtime = (datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()
    os.utime(str(orphan_file), (old_mtime, old_mtime))

    async with db_session_factory() as session:
        await run_staging_cleanup(session, photo_storage_root)

    assert not orphan_file.exists(), "Orphan file should have been reaped"


async def test_cleanup_does_not_remove_files_referenced_by_current_rows(db_session, db_session_factory, photo_storage_root):
    """Files referenced by current (non-expired) rows are NOT deleted."""
    from app.tasks.staging_cleanup import run_staging_cleanup

    root = Path(photo_storage_root)
    user = await _create_user(db_session, "keep_current@example.com")

    # Create file
    full_path, thumb_path = await _make_staging_file(root, user.id, "keep.jpg")

    row = StagingPhotoTable(
        user_id=user.id,
        storage_key=f"staging/{user.id}/keep.jpg",
        thumbnail_key=f"staging/{user.id}/keep.thumb.jpg",
    )
    db_session.add(row)
    await db_session.commit()

    # Make file old enough for orphan check
    old_mtime = (datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()
    os.utime(str(full_path), (old_mtime, old_mtime))
    os.utime(str(thumb_path), (old_mtime, old_mtime))

    async with db_session_factory() as session:
        await run_staging_cleanup(session, photo_storage_root)

    assert full_path.exists(), "Referenced file should not be deleted"
    assert thumb_path.exists(), "Referenced thumb should not be deleted"


async def test_cleanup_does_not_touch_collections_dir(db_session, db_session_factory, photo_storage_root):
    """Files under collections/ are never touched by cleanup."""
    from app.tasks.staging_cleanup import run_staging_cleanup

    root = Path(photo_storage_root)

    # Create a file in collections/
    coll_dir = root / "collections" / "1" / "items" / "1"
    coll_dir.mkdir(parents=True, exist_ok=True)
    coll_file = coll_dir / "photo.jpg"
    coll_file.write_bytes(b"collection photo")

    async with db_session_factory() as session:
        await run_staging_cleanup(session, photo_storage_root)

    assert coll_file.exists(), "Collections file should not be touched by cleanup"
