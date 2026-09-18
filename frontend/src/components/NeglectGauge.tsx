/**
 * The Ward Neglect Index, shown as a banded gauge.
 *
 * Three rules this component exists to enforce:
 *
 * 1. **Never a bare number.** The band word always appears beside the score, so
 *    "74" is read as "high" rather than as a temperature or a percentage.
 * 2. **`null` is not zero.** A ward below the minimum sample shows "Not enough
 *    reports yet". Rendering it as 0 would put the wards nobody reports at the
 *    top of a best-run reading of the leaderboard.
 * 3. **The index belongs to the ward.** Nothing here takes a councillor as a
 *    prop, so the score cannot accidentally be rendered against a person.
 */
import type { IndexBand, IndexBasis } from '../api/types'

const BAND_STYLE: Record<IndexBand, { text: string; bg: string; stroke: string; word: string }> = {
  LOW: {
    text: 'text-band-low',
    bg: 'bg-band-low-soft',
    stroke: 'var(--color-band-low)',
    word: 'Low neglect',
  },
  MODERATE: {
    text: 'text-band-moderate',
    bg: 'bg-band-moderate-soft',
    stroke: 'var(--color-band-moderate)',
    word: 'Moderate neglect',
  },
  HIGH: {
    text: 'text-band-high',
    bg: 'bg-band-high-soft',
    stroke: 'var(--color-band-high)',
    word: 'High neglect',
  },
}

const RADIUS = 52
const CIRCUMFERENCE = Math.PI * RADIUS // semicircle

export function NeglectGauge({
  score,
  band,
  note,
  basis,
  explanation,
}: {
  score: number | null
  band: IndexBand | null
  note: string | null
  basis: IndexBasis
  explanation: string
}) {
  const hasScore = score !== null && band !== null
  const style = hasScore ? BAND_STYLE[band] : null
  const filled = hasScore ? (score / 100) * CIRCUMFERENCE : 0

  return (
    <section aria-label="Ward Neglect Index">
      <div className="flex items-center gap-4">
        <svg viewBox="0 0 128 72" className="h-[72px] w-32 shrink-0" role="img"
             aria-label={hasScore ? `Neglect index ${score} out of 100, ${style!.word}` : 'No index yet'}>
          <path
            d="M 12 64 A 52 52 0 0 1 116 64"
            fill="none"
            stroke="var(--color-line)"
            strokeWidth="11"
            strokeLinecap="round"
          />
          {hasScore ? (
            <path
              d="M 12 64 A 52 52 0 0 1 116 64"
              fill="none"
              stroke={style!.stroke}
              strokeWidth="11"
              strokeLinecap="round"
              strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
            />
          ) : null}
          <text
            x="64"
            y="58"
            textAnchor="middle"
            className="fill-ink"
            style={{ fontSize: 26, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}
          >
            {hasScore ? score : '—'}
          </text>
        </svg>

        <div className="min-w-0">
          {hasScore ? (
            <span
              className={`inline-block rounded-full px-2.5 py-1 text-xs font-semibold ${style!.bg} ${style!.text}`}
            >
              {style!.word}
            </span>
          ) : (
            <span className="inline-block rounded-full bg-surface-2 px-2.5 py-1 text-xs font-semibold text-ink-3">
              {note ?? 'Not enough reports yet'}
            </span>
          )}
          <p className="mt-1.5 text-xs leading-relaxed text-ink-2">{explanation}</p>
        </div>
      </div>

      {/* The four raw numbers. Explainability is the feature: a reader who asks
          "what is 74 made of?" gets an answer without leaving the card. */}
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 border-t border-line pt-3 text-xs sm:grid-cols-4">
        <Stat label="Still open" value={basis.open} />
        <Stat label="Resolved" value={basis.resolved} />
        <Stat label="Oldest open" value={`${Math.round(basis.median_open_age_days)}d`} title="Median age of open reports" />
        <Stat label="Fix time" value={`${Math.round(basis.median_resolution_days)}d`} title="Median days to resolve" />
      </dl>
    </section>
  )
}

function Stat({ label, value, title }: { label: string; value: string | number; title?: string }) {
  return (
    <div title={title}>
      <dt className="text-[11px] uppercase tracking-wide text-ink-3">{label}</dt>
      <dd className="font-semibold tabular-nums text-ink">{value}</dd>
    </div>
  )
}
