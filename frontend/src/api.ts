const API_BASE = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiFetch(path: string, options?: RequestInit) {
  const resp = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
  });
  if (!resp.ok) {
    throw new ApiError(resp.status, `API error: ${resp.status}`);
  }
  // Handle empty responses (e.g., 204 No Content)
  const contentType = resp.headers.get('content-type');
  if (!contentType || resp.status === 204) {
    return null;
  }
  return resp.json();
}

export async function requestMagicLink(email: string) {
  return apiFetch("/auth/magic-link", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function verifyToken(token: string) {
  return apiFetch(`/auth/verify?token=${encodeURIComponent(token)}`);
}

export async function devLogin() {
  return apiFetch("/auth/dev-login", { method: "POST" });
}

export async function getMe() {
  return apiFetch("/auth/me");
}

export async function getCollections() {
  return apiFetch("/collections");
}

export async function getNextPair(collectionId: number) {
  return apiFetch(`/collections/${collectionId}/ranking/next`);
}

export async function submitComparison(
  collectionId: number,
  data: {
    item_a_id: number;
    item_b_id: number;
    winner_id: number;
    info_level_shown: string;
  }
) {
  return apiFetch(`/collections/${collectionId}/ranking/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getRankedItems(collectionId: number) {
  return apiFetch(`/collections/${collectionId}/ranking`);
}

export async function getItemPhotos(collectionId: number, itemId: number) {
  return apiFetch(`/collections/${collectionId}/items/${itemId}/photos`);
}

export async function updateItemStatus(
  collectionId: number,
  itemId: number,
  status: string
) {
  return apiFetch(`/collections/${collectionId}/items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export async function updateItemBrand(
  collectionId: number,
  itemId: number,
  brand: string
) {
  return apiFetch(`/collections/${collectionId}/items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brand }),
  });
}

export async function getItems(collectionId: number) {
  return apiFetch(`/collections/${collectionId}/items`);
}

export async function createCollection(data: { name: string; description?: string }) {
  return apiFetch("/collections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function patchItemMetadata(
  collectionId: number,
  itemId: number,
  fields: Record<string, unknown>
) {
  return apiFetch(`/collections/${collectionId}/items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
}

export async function addItemPhoto(
  collectionId: number,
  itemId: number,
  file: File
) {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch(`/collections/${collectionId}/items/${itemId}/photos`, {
    method: "POST",
    body: formData,
  });
}

/** Upload multiple photos to an item (one at a time) */
export async function addItemPhotos(
  collectionId: number,
  itemId: number,
  files: File[]
): Promise<unknown[]> {
  const results = [];
  for (const file of files) {
    const result = await addItemPhoto(collectionId, itemId, file);
    results.push(result);
  }
  return results;
}

// Upload/staging types
export type StagingPhoto = {
  id: number;
  thumbnail_url: string;
  original_filename: string | null;
  captured_at: string | null;
};

export type UploadResponse = {
  succeeded: StagingPhoto[];
  failed: { original_filename: string; reason: string }[];
};

export type StagingListResponse = {
  photos: StagingPhoto[];
  has_more: boolean;
};

export async function uploadPhotos(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  return apiFetch("/upload/photos", {
    method: "POST",
    body: formData,
  });
}

export async function getStaging(params: {
  limit?: number;
  before?: number;
}): Promise<StagingListResponse> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.before !== undefined) query.set("before", String(params.before));
  const qs = query.toString();
  return apiFetch(`/upload/staging${qs ? `?${qs}` : ""}`);
}

export async function groupPhotos(body: {
  collection_id: number;
  photo_ids: number[];
}): Promise<{ item_id: number }> {
  return apiFetch("/upload/group", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function discardStaging(id: number): Promise<void> {
  return apiFetch(`/upload/staging/${id}`, { method: "DELETE" });
}
