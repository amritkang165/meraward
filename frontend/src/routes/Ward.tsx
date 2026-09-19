/**
 * `/ward` — which ward am I in, and how neglected is it?
 *
 * The first screen a user touches and the first a judge clicks. Drop a pin (or
 * use your location), get the ward and its Neglect Index.
 */
import { useCallback, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError, api, currentPosition } from '../api/client'
import { DELHI_CENTRE, MapView } from '../components/MapView'
import { NeglectGauge } from '../components/NeglectGauge'
import { useDebounced } from '../lib/useDebounced'
import { DemoNotice, ErrorState, LoadingCard } from '../components/states'

type Pin = { lat: number; lng: number }

export default function Ward() {
  const [pin, setPin] = useState<Pin>({ lat: DELHI_CENTRE[1], lng: DELHI_CENTRE[0] })
  const [locating, setLocating] = useState(false)
  const [locationNote, setLocationNote] = useState<string | null>(null)

  // `/ward?ward=DEL-0042` — how the dashboard leaderboard links here. Without
  // this the deep link silently showed whatever the map happened to be on.
  const [searchParams, setSearchParams] = useSearchParams()
  const wardIdParam = searchParams.get('ward')?.trim() ?? ''

  // Dragging the pin emits a position per animation frame; without debouncing
  // that is one Lambda invocation per frame for a gesture nobody has finished.
  const settledPin = useDebounced(pin, 350)

  const ward = useQuery({
    queryKey: wardIdParam
      ? ['ward', 'id', wardIdParam]
      : ['ward', settledPin.lat.toFixed(5), settledPin.lng.toFixed(5)],
    queryFn: () =>
      wardIdParam ? api.ward(wardIdParam) : api.wardByPoint(settledPin.lat, settledPin.lng),
    retry: false,
  })

  /** Moving the pin means "look here instead", so it clears a deep link. */
  const movePin = useCallback(
    (next: Pin) => {
      setPin(next)
      if (wardIdParam) setSearchParams({}, { replace: true })
    },
    [wardIdParam, setSearchParams],
  )

  const useMyLocation = useCallback(async () => {
    setLocating(true)
    setLocationNote(null)
    try {
      movePin(await currentPosition())
    } catch (error) {
      // Geolocation denial is an ordinary outcome on a phone, not a failure:
      // say what to do instead and leave the map usable.
      setLocationNote(
        error instanceof ApiError ? error.message : 'Drop a pin on the map instead.',
      )
    } finally {
      setLocating(false)
    }
  }, [movePin])

  const outsideCoverage = ward.error instanceof ApiError && ward.error.code === 'outside_coverage'

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold tracking-tight text-ink">Which ward am I in?</h1>
        <p className="mt-1 text-sm text-ink-2">
          Tap the map or drag the pin. Delhi has hundreds of municipal wards and almost nobody knows
          which one they live in.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={useMyLocation}
          disabled={locating}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-dark disabled:opacity-60"
        >
          {locating ? 'Finding you…' : 'Use my location'}
        </button>
        <span className="font-mono text-xs tabular-nums text-ink-3">
          {pin.lat.toFixed(5)}, {pin.lng.toFixed(5)}
        </span>
      </div>

      {locationNote ? (
        <p className="rounded-lg bg-band-moderate-soft px-3 py-2 text-sm text-band-moderate" role="status">
          {locationNote}
        </p>
      ) : null}

      <MapView
        pin={pin}
        onPinMove={movePin}
        className="h-[320px] w-full overflow-hidden rounded-xl border border-line sm:h-[420px]"
      />

      <section className="rounded-xl border border-line bg-surface shadow-sm">
        {ward.isPending ? (
          <LoadingCard label="Looking up the ward for this pin" />
        ) : ward.isError ? (
          <div className="p-4">
            <ErrorState
              title={outsideCoverage ? 'Outside Delhi' : "Couldn't look that up"}
              message={
                ward.error instanceof ApiError
                  ? ward.error.message
                  : 'Something went wrong. Try moving the pin.'
              }
              action={
                outsideCoverage ? null : (
                  <button
                    type="button"
                    onClick={() => ward.refetch()}
                    className="rounded-lg border border-line px-4 py-2 text-sm font-semibold text-ink"
                  >
                    Try again
                  </button>
                )
              }
            />
          </div>
        ) : (
          <div className="space-y-4 p-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-wide text-ink-3">
                {ward.data.ward_id}
              </p>
              <h2 className="text-lg font-bold tracking-tight text-ink">{ward.data.ward_name}</h2>
              {ward.data.zone ? <p className="text-sm text-ink-2">{ward.data.zone}</p> : null}
            </div>

            <NeglectGauge
              score={ward.data.neglect_index}
              band={ward.data.index_band}
              note={ward.data.index_note}
              basis={ward.data.index_basis}
              explanation={ward.data.index_explanation}
            />

            {/* Identity only, and visually separated from the index above it.
                Withheld entirely by the API when we have not sourced it.

                The separation matters more now that real councillors are
                loaded: this card can show a named person on a ward whose index
                is HIGH, and that index is computed from demonstration data. The
                disclaimer below is not decoration - it is the difference
                between naming who represents an area and implying they caused
                a number we generated. */}
            <div className="border-t border-line pt-3">
              <h3 className="text-[11px] uppercase tracking-wide text-ink-3">Your councillor</h3>
              {ward.data.councillor ? (
                <>
                  <p className="font-semibold text-ink">{ward.data.councillor.name}</p>
                  {ward.data.councillor.party ? (
                    <p className="text-sm text-ink-2">{ward.data.councillor.party}</p>
                  ) : null}
                  <p className="mt-2 rounded-md bg-surface-2 px-2.5 py-2 text-xs leading-relaxed text-ink-2">
                    The Neglect Index above describes <strong className="text-ink">this ward</strong>,
                    not this councillor&rsquo;s performance. It is computed from demonstration data
                    and is not a measure of any individual.
                  </p>
                  <p className="mt-1.5 text-xs leading-relaxed text-ink-3">
                    Source: {ward.data.councillor.source}
                  </p>
                </>
              ) : (
                <p className="mt-1 inline-block rounded-md bg-surface-2 px-2 py-1 text-xs text-ink-3">
                  Councillor details not available for this ward
                </p>
              )}
            </div>

            <Link
              to="/report"
              state={{ lat: pin.lat, lng: pin.lng }}
              className="block rounded-lg bg-brand px-4 py-3 text-center text-sm font-semibold text-white transition-colors hover:bg-brand-dark"
            >
              Report an issue here
            </Link>

            <DemoNotice>{ward.data.data_notice}</DemoNotice>
          </div>
        )}
      </section>
    </div>
  )
}
