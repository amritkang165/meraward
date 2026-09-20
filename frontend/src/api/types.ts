/**
 * Response shapes, typed against the deployed API.
 *
 * These mirror `backend/src/**` exactly. The committed backend tests in
 * `backend/tests/` are the specification — if a shape here disagrees with a
 * test there, the test is right.
 */

export type IssueType = 'POTHOLE' | 'STREETLIGHT' | 'GARBAGE' | 'WATER' | 'OTHER'
export type ComplaintStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED'
export type DraftStatus = 'PENDING' | 'DRAFTED' | 'SENT' | 'FAILED'
export type IndexBand = 'LOW' | 'MODERATE' | 'HIGH'

/** The four raw numbers shown beside the gauge. Explainability is the feature. */
export interface IndexBasis {
  open: number
  resolved: number
  median_open_age_days: number
  median_resolution_days: number
  components?: {
    backlog: number
    staleness: number
    /** null when the ward has never resolved anything, so there is no speed to measure. */
    sloth: number | null
  }
}

/**
 * Identity only — name, party, provenance. Never combined with the index, and
 * null in its entirety when we have not sourced it.
 */
export interface Councillor {
  name: string
  party: string | null
  source: string
}

export interface WardLookup {
  ward_id: string
  ward_name: string
  zone: string | null
  /** null when the ward has fewer than 5 reports. Not zero — never zero. */
  neglect_index: number | null
  index_band: IndexBand | null
  index_note: string | null
  index_basis: IndexBasis
  index_explanation: string
  councillor: Councillor | null
  data_notice: string
  query?: { lat: number; lng: number }
}

export interface PresignResponse {
  upload_url: string
  photo_key: string
  expires_in: number
  max_bytes: number
  required_headers: Record<string, string>
}

export interface CreateComplaintRequest {
  photo_key?: string
  issue_type: IssueType
  lat: number
  lng: number
  reporter_email?: string
  landmark?: string
  description?: string
  input_mode?: 'voice' | 'photo' | 'write'
  preferred_language?: 'en' | 'hi'
}

export interface CreateComplaintResponse {
  complaint_id: string
  /** The magic link. Persist it for the reporter; never render it publicly. */
  status_token: string
  status: ComplaintStatus
  draft_status: DraftStatus
  queued: boolean
  ward: { ward_id: string; ward_name: string; zone: string | null }
  tracking_url: string
}

export interface TimelineStep {
  status: ComplaintStatus
  label: string
  at: string
}

export interface Complaint {
  complaint_id: string
  ward_id: string
  ward_name: string | null
  created_at: string
  status: ComplaintStatus
  draft_status: DraftStatus
  draft_source: string | null
  issue_type: IssueType
  lat: number
  lng: number
  landmark: string | null
  description?: string | null
  input_mode?: 'voice' | 'photo' | 'write' | null
  preferred_language?: 'en' | 'hi' | null
  subject: string | null
  body_en: string | null
  body_hi: string | null
  is_demo: boolean
  delivery_mode: string | null
  acknowledged_at: string | null
  resolved_at: string | null
  reopened_at: string | null
  photo_url: string | null
  timeline: TimelineStep[]
  ward?: { ward_id: string; ward_name: string; zone: string | null }
  /** Only present on a status update response. */
  changed?: boolean
}

export interface MapMarker {
  complaint_id: string
  ward_id: string
  lat: number
  lng: number
  issue_type: IssueType
  status: ComplaintStatus
  created_at: string
  is_demo: boolean
}

export interface ComplaintsList {
  complaints: MapMarker[]
  count: number
  truncated: boolean
  filters: {
    status: ComplaintStatus | null
    issue_type: IssueType | null
    ward_id: string | null
    bbox: number[] | null
  }
}

export interface LeaderboardRow {
  ward_id: string
  ward_name: string
  zone: string | null
  neglect_index: number | null
  index_band: IndexBand | null
  index_basis: IndexBasis
  note: string | null
  rank?: number
}

export interface Leaderboard {
  wards: LeaderboardRow[]
  /** Wards below the minimum sample. Listed, but never ranked. */
  unranked: LeaderboardRow[]
  ranked_count: number
  unranked_count: number
  index_explanation: string
  data_notice: string
}

export interface Health {
  status: 'ok' | 'degraded'
  service: string
  time: string
  region: string
  version: string
  ward_index: { loaded: boolean; wards?: number; reason?: string }
  drafting: { mode: 'bedrock' | 'template' }
  delivery_mode: string
}

export type StatusAction = 'acknowledge' | 'resolve' | 'reopen'
