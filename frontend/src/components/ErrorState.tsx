import { motion } from 'framer-motion'
import { AlertCircle, WifiOff } from 'lucide-react'

interface ErrorStateProps {
  message?: string
  unavailable?: boolean
  onRetry: () => void
}

export function ErrorState({ message, unavailable, onRetry }: ErrorStateProps) {
  const isUnavailable =
    unavailable ||
    /unavailable|failed to fetch|network|ECONNREFUSED|load failed/i.test(message || '')

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-xl px-5 py-16 text-center sm:px-8"
    >
      <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-critical/25 bg-critical/10 text-critical">
        {isUnavailable ? (
          <WifiOff className="h-6 w-6" aria-hidden />
        ) : (
          <AlertCircle className="h-6 w-6" aria-hidden />
        )}
      </div>
      <h2 className="font-display text-2xl font-bold text-navy">
        {isUnavailable ? 'Troubleshooting service unavailable' : 'Unexpected error'}
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-ink-soft">
        {message?.trim() ||
          (isUnavailable
            ? 'The SGTE API could not be reached. Confirm the backend is running, then try again.'
            : "SGTE couldn't complete this diagnosis.")}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="sgte-btn-primary mt-8 rounded-full px-5 py-2.5 text-sm font-semibold"
      >
        Try again
      </button>
    </motion.section>
  )
}
