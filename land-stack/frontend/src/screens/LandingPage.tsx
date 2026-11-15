import { Link } from 'react-router-dom'
import { TopNav } from '@/components/TopNav'
import { Footer } from '@/components/Footer'
export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <TopNav />
      <main className="flex-1">
        <section className="bg-gradient-to-br from-[#1e40af] to-blue-900 text-white py-24 px-8 text-center">
          <h1 className="text-4xl font-bold mb-4">Unified Land Governance, anchored by ULPIN</h1>
          <p className="text-lg mb-8 opacity-80">SIH PS #26014 - Ministry of Rural Development - DoLR</p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link to="/parcel/CH-UT-000001/verify" className="bg-white text-[#1e40af] px-6 py-3 rounded-lg font-semibold hover:bg-blue-50">Verify a Parcel</Link>
            <Link to="/map" className="border-2 border-white px-6 py-3 rounded-lg font-semibold hover:bg-white/10">Explore Map</Link>
          </div>
        </section>
        <section className="py-12 px-8 max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4">
          {['3-Layer GIS Model','State Adapter','AI/ML Insights','Tamper-Evident Audit'].map(f =>
            <div key={f} className="bg-white rounded-xl shadow p-6 text-center"><p className="font-semibold text-slate-700">{f}</p></div>
          )}
        </section>
        <section className="py-8 bg-slate-50 flex gap-6 justify-center">
          {[['Chandigarh Urban Pilot'],['Tamil Nadu Rural Pilot']].map(([n]) =>
            <div key={n} className="bg-white border border-slate-200 rounded-xl shadow p-8 text-center w-64">
              <p className="font-bold text-[#1e40af]">{n}</p>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </div>
  )
}
