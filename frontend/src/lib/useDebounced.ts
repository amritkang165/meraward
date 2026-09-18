import { useEffect, useRef, useState } from 'react'

/**
 * Hold a value still until it stops changing.
 *
 * The ward lookup is keyed on the pin. Without this, dragging the pin across
 * the map fires one API request per animation frame — hundreds of Lambda
 * invocations for a gesture the user has not finished making. Debouncing turns
 * a drag into a single request when the finger lifts.
 */
export function useDebounced<T>(value: T, delayMs = 350): T {
  const [settled, setSettled] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return settled
}

/**
 * Debounce a callback, cancelling any pending call on unmount.
 *
 * Used for map-move handlers, where the event fires continuously while the user
 * pans and only the final position is worth acting on.
 */
export function useDebouncedCallback<A extends unknown[]>(
  fn: (...args: A) => void,
  delayMs = 350,
): (...args: A) => void {
  const latest = useRef(fn)
  latest.current = fn
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
    },
    [],
  )

  return (...args: A) => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => latest.current(...args), delayMs)
  }
}
