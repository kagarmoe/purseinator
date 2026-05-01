# Backend TDD — Design Spec

**Date:** 2026-05-01  
**Sub-project:** 1 of 3 (Backend TDD → Frontend TDD → README)

## Goal

Build a correct, complete backend using TDD. Tests specify the required behavior; implementation exists to make them pass. The existing 70-test baseline is a starting point — gaps are filled by writing new tests first, then implementing.

## Scope

All non-GPU backend functionality: auth, collections, items, photos, ranking, and the service layer underneath them.

GPU-dependent tests (`test_card_detector`, `test_condition`, `test_grouper`, `test_ingest_and_push_workflow`) are skipped when numpy is absent, not deleted.

## Test Specification

### Auth

- `POST /auth/magic-link` with valid email → 200, returns token
- `POST /auth/magic-link` with missing email → 422
- `GET /auth/verify?token=<valid>` → 200, returns session_id, creates user on first use
- `GET /auth/verify?token=<expired>` → 401
- `GET /auth/verify?token=<invalid>` → 401
- `GET /auth/me` with valid session → 200, returns name and role
- `GET /auth/me` without session → 401
- `POST /auth/logout` → 200, session invalidated

### Collections

- `POST /collections` authenticated → 201, collection created and owned by caller
- `POST /collections` unauthenticated → 401
- `GET /collections` → 200, returns only caller's collections
- `GET /collections/{id}` owner → 200
- `GET /collections/{id}` non-owner → 403
- `GET /collections/{id}` missing → 404

### Items

- `POST /collections/{id}/items` → 201, item created with status `unranked`
- `GET /collections/{id}/items` → 200, list scoped to collection
- `GET /collections/{id}/items/{item_id}` → 200
- `GET /collections/{id}/items/{item_id}` wrong collection → 404
- `PATCH /collections/{id}/items/{item_id}` brand update → 200, persisted
- `PATCH /collections/{id}/items/{item_id}` status update → 200, persisted
- `PATCH /collections/{id}/items/{item_id}` non-owner → 403
- `PATCH /collections/{id}/items/{item_id}` missing → 404

### Photos

- `POST /collections/{id}/items/{item_id}/photos` → 201, first upload becomes hero
- `POST /collections/{id}/items/{item_id}/photos` second upload → 201, hero unchanged
- `GET /collections/{id}/items/{item_id}/photos` → 200, list in upload order
- `GET /photos/{storage_key}` existing → 200, correct content-type
- `GET /photos/{storage_key}` missing → 404
- Upload to missing item → 404

### Ranking

- `GET /collections/{id}/ranking/next` → 200, returns two items with info_level
- `GET /collections/{id}/ranking/next` single item collection → 404 or empty
- `POST /collections/{id}/ranking/compare` valid winner → 200, Elo ratings updated
- `POST /collections/{id}/ranking/compare` winner_id not in pair → 422
- `GET /collections/{id}/ranking` → 200, items sorted by rating descending

### Service Layer (unit tests, no HTTP)

- Elo engine: winner gains rating, loser loses rating, sum conserved
- Elo engine: larger upset → larger rating change
- Pairing algorithm: returns least-compared pair
- Pairing algorithm: with single item returns None
- Ranking sort: items ordered by rating descending, ties broken by comparison_count

## GPU Tests

Add to each GPU-dependent test:

```python
numpy_available = pytest.mark.skipif(
    importlib.util.find_spec("numpy") is None,
    reason="requires gpu extras: pip install -e '.[gpu]'"
)
```

## Done When

- All non-GPU tests pass (`pytest tests/ --ignore` pattern or skip marks)
- Every behavior listed above has at least one test
- No implementation changes made without a failing test driving them
