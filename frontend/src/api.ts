const API_BASE = import.meta.env.VITE_API_URL || "";

async function apiFetch(path: string, options?: RequestInit) {
  const resp = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
  });
  if (!resp.ok) {
    throw new Error(`API error: ${resp.status}`);
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
  return apiFetch(`/auth/verify?token=${token}`);
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
