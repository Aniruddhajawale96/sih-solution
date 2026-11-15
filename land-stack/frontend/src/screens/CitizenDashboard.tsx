import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
export default function CitizenDashboard() {
  return (
    <div className="min-h-screen flex flex-col">
      <TopNav />
      <main className="flex-1 flex items-center justify-center bg-slate-50">
        <div className="bg-white rounded-xl shadow-lg p-12 text-center max-w-md">
          <p className="text-5xl mb-4">👤</p>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Citizen Dashboard</h2>
          <p className="text-slate-500 text-sm">Login and manage your parcels — Screen 7</p>
        </div>
      </main>
      <Footer />
    </div>
  )
}
