/**
 * API client.
 *
 * One place that knows the base URL, the error envelope, and how to talk to S3.
 * Errors arrive from the backend as `{error: {code, message}}`; `ApiError`
 * carries the code through so screens can branch on it (`outside_coverage`
 * deserves a different message from `photo_too_large`) instead of string
 * matching on prose.
 */

import type {
  Complaint,
  ComplaintsList,
  CreateComplaintRequest,
  CreateComplaintResponse,
  Health,
  IssueType,
  Leaderboard,
  PresignResponse,
  StatusAction,
  WardLookup,
} from './types'

const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }

  /** True when retrying might plausibly help. */
  get isTransient(): boolean {
    return this.status >= 500 || this.status === 429
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { 'content-type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch {
    // fetch only rejects on a network-level failure, so this is genuinely "no
    // connection", not a 500.
    throw new ApiError('network_error', "Can't reach MERAWARD. Check your connection.", 0)
  }

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    const envelope = (payload as { error?: { code?: string; message?: string } } | null)?.error
    throw new ApiError(
      envelope?.code ?? 'unexpected_error',
      envelope?.message ?? 'Something went wrong.',
      response.status,
    )
  }

  return payload as T
}

export const api = {
  health: () => request<Health>('/health'),

  wardByPoint: (lat: number, lng: number) =>
    request<WardLookup>(`/wards/lookup?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`),

  ward: (wardId: string) => request<WardLookup>(`/wards/${encodeURIComponent(wardId)}`),

  complaint: (id: string) => request<Complaint>(`/complaints/${encodeURIComponent(id)}`),

  complaints: (params: {
    bbox?: [number, number, number, number]
    status?: string
    issue_type?: IssueType
    ward_id?: string
  } = {}) => {
    const query = new URLSearchParams()
    if (params.bbox) query.set('bbox', params.bbox.join(','))
    if (params.status) query.set('status', params.status)
    if (params.issue_type) query.set('issue_type', params.issue_type)
    if (params.ward_id) query.set('ward_id', params.ward_id)
    const suffix = query.toString()
    return request<ComplaintsList>(`/complaints${suffix ? `?${suffix}` : ''}`)
  },

  leaderboard: () => request<Leaderboard>('/leaderboard'),

  presign: (contentType: string, contentLength: number) =>
    request<PresignResponse>('/complaints/presign', {
      method: 'POST',
      body: JSON.stringify({ content_type: contentType, content_length: contentLength }),
    }),

  createComplaint: (body: CreateComplaintRequest) =>
    request<CreateComplaintResponse>('/complaints', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateStatus: (id: string, token: string, action: StatusAction) =>
    request<Complaint>(`/complaints/${encodeURIComponent(id)}/status`, {
      method: 'POST',
      body: JSON.stringify({ token, action }),
    }),
}

/**
 * Upload a photo straight to S3.
 *
 * The signature binds both Content-Type and Content-Length, so the headers the
 * presign response hands back must be sent verbatim — changing either makes the
 * signature fail with an opaque 403.
 */
export async function uploadPhoto(file: File, presigned: PresignResponse): Promise<void> {
  let response: Response
  try {
    response = await fetch(presigned.upload_url, {
      method: 'PUT',
      headers: presigned.required_headers,
      body: file,
    })
  } catch {
    throw new ApiError('upload_failed', "Couldn't upload the photo. Try again.", 0)
  }
  if (!response.ok) {
    throw new ApiError('upload_failed', "Couldn't upload the photo. Try again.", response.status)
  }
}

/** Ask the browser for a position. Rejects with a message worth showing. */
export function currentPosition(): Promise<{ lat: number; lng: number }> {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new ApiError('no_geolocation', 'This device has no location support.', 0))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({ lat: position.coords.latitude, lng: position.coords.longitude }),
      (error) =>
        reject(
          new ApiError(
            error.code === error.PERMISSION_DENIED ? 'permission_denied' : 'position_unavailable',
            error.code === error.PERMISSION_DENIED
              ? 'Location is off, so drop a pin on the map instead.'
              : "Couldn't get your location. Drop a pin on the map instead.",
            0,
          ),
        ),
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 },
    )
  })
}
