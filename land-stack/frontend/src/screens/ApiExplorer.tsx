import { useState } from 'react'
import { Copy, CheckCheck, ExternalLink } from 'lucide-react'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
import { useAuthStore } from '@/store/authStore'

export default function ApiExplorer() {
  const accessToken = useAuthStore(s => s.accessToken)
  const [loaded, setLoaded] = useState(false)
  const [copied, setCopied] = useState(false)

  async function copyToken() {
    if (!accessToken) return
    await navigator.clipboard.writeText(accessToken)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <TopNav />

      {/* Header bar */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-800">API Explorer</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Explore and test the Land Stack REST API. Endpoints require a valid Bearer token.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {accessToken ? (
            <button
              onClick={copyToken}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              {copied ? (
                <>
                  <CheckCheck size={15} />
                  Copied!
                </>
              ) : (
                <>
                  <Copy size={15} />
                  Copy Token
                </>
              )}
            </button>
          ) : (
            <span className="text-sm text-slate-400 italic">Not logged in — no token available</span>
          )}
          <a
            href="/api/v1/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 text-slate-600 text-sm hover:bg-slate-50 transition-colors"
          >
            <ExternalLink size={14} />
            Open in tab
          </a>
        </div>
      </div>

      {/* iframe fills remaining space */}
      <main className="flex-1 relative bg-slate-100">
        {!loaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-50 z-10">
            <div className="text-center">
              <div className="inline-block w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm text-slate-500">Loading API Explorer…</p>
            </div>
          </div>
        )}
        <iframe
          src="/api/v1/docs"
          title="API Explorer — Land Stack Swagger UI"
          onLoad={() => setLoaded(true)}
          className="w-full border-0"
          style={{ minHeight: 'calc(100vh - 120px)', display: 'block' }}
        />
      </main>

      <Footer />
    </div>
  )
}
