import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
export function TopNav() {
  const { role, username, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  return (
    <nav className="bg-[#1e40af] text-white px-6 py-3 flex items-center justify-between shadow-md">
      <Link to="/" className="text-xl font-bold">🏛 Land Stack</Link>
      <div className="flex gap-5 text-sm items-center">
        <Link to="/map" className="hover:underline">Map</Link>
        <Link to="/parcel/CH-UT-000001/verify" className="hover:underline">Verify</Link>
        {role
          ? <><span className="opacity-70">{username} · {role}</span>
              <button onClick={() => { clearAuth(); navigate('/') }} className="hover:underline">Logout</button></>
          : <Link to="/citizen/dashboard" className="hover:underline">Login</Link>}
      </div>
    </nav>
  )
}
