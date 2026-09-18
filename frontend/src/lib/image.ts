/**
 * Client-side photo compression.
 *
 * A modern phone camera produces 4–12 MB files. Uploading one raw over mobile
 * data in a Delhi street is slow enough that people abandon the report, and our
 * own cap rejects anything over 8 MB outright.
 *
 * Resizing to 1600px on the long edge and re-encoding as JPEG typically takes a
 * 6 MB photo to roughly 300–600 KB — far more than enough detail to show a
 * pothole, at a tenth of the upload time. It happens on the device, so it costs
 * us no compute and no bandwidth.
 */

const MAX_EDGE = 1600
const QUALITY = 0.82

export interface CompressionResult {
  file: File
  originalBytes: number
  compressedBytes: number
}

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => {
      URL.revokeObjectURL(url)
      resolve(image)
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('could not decode image'))
    }
    image.src = url
  })
}

/**
 * Compress a photo for upload.
 *
 * Returns the original untouched if anything goes wrong, or if compressing
 * would not actually help — a HEIC the browser cannot decode, a canvas that is
 * unavailable, or an image already smaller than the result would be. Failing to
 * compress must never mean failing to report.
 */
export async function compressPhoto(file: File): Promise<CompressionResult> {
  const original = { file, originalBytes: file.size, compressedBytes: file.size }

  if (!file.type.startsWith('image/')) return original

  try {
    const image = await loadImage(file)
    const scale = Math.min(1, MAX_EDGE / Math.max(image.width, image.height))
    const width = Math.round(image.width * scale)
    const height = Math.round(image.height * scale)

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d')
    if (!context) return original
    context.drawImage(image, 0, 0, width, height)

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', QUALITY),
    )
    if (!blob || blob.size >= file.size) return original

    const name = file.name.replace(/\.[^.]+$/, '') || 'photo'
    return {
      file: new File([blob], `${name}.jpg`, { type: 'image/jpeg' }),
      originalBytes: file.size,
      compressedBytes: blob.size,
    }
  } catch {
    // HEIC that the browser cannot decode, a blocked canvas, an OOM on a very
    // large image: upload what we were given and let the server cap decide.
    return original
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
