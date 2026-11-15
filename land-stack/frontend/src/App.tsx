import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { RoleRouteGuard } from '@/components/RoleRouteGuard'
import LandingPage from '@/screens/LandingPage'
import GisMapExplorer from '@/screens/GisMapExplorer'
import Parcel360View from '@/screens/Parcel360View'
import OwnershipVerification from '@/screens/OwnershipVerification'
import ServiceRequestPortal from '@/screens/ServiceRequestPortal'
import RequestTracking from '@/screens/RequestTracking'
import CitizenDashboard from '@/screens/CitizenDashboard'
import OfficerLogin from '@/screens/OfficerLogin'
import OfficerDashboard from '@/screens/OfficerDashboard'
import WorkflowApproval from '@/screens/WorkflowApproval'
import ZoningDashboard from '@/screens/ZoningDashboard'
import SyncMonitor from '@/screens/SyncMonitor'
import StateAdminPanel from '@/screens/StateAdminPanel'
import NationalAnalytics from '@/screens/NationalAnalytics'
import AuditTrailViewer from '@/screens/AuditTrailViewer'
import ApiExplorer from '@/screens/ApiExplorer'

export default function App() {
  return (
    <BrowserRouter><Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/map" element={<GisMapExplorer />} />
      <Route path="/parcel/:ulpin" element={<Parcel360View />} />
      <Route path="/parcel/:ulpin/verify" element={<OwnershipVerification />} />
      <Route path="/citizen/services" element={<RoleRouteGuard allowed={['CITIZEN']}><ServiceRequestPortal /></RoleRouteGuard>} />
      <Route path="/citizen/requests" element={<RoleRouteGuard allowed={['CITIZEN']}><RequestTracking /></RoleRouteGuard>} />
      <Route path="/citizen/dashboard" element={<CitizenDashboard />} />
      <Route path="/officer/login" element={<OfficerLogin />} />
      <Route path="/officer/dashboard" element={<RoleRouteGuard allowed={['REV_OFF','REG_OFF','PLAN_OFF','TAX_OFF','STATE_ADMIN','NATL_ADMIN']}><OfficerDashboard /></RoleRouteGuard>} />
      <Route path="/officer/workflow" element={<RoleRouteGuard allowed={['REV_OFF','PLAN_OFF','TAX_OFF','STATE_ADMIN','NATL_ADMIN']}><WorkflowApproval /></RoleRouteGuard>} />
      <Route path="/officer/zoning" element={<RoleRouteGuard allowed={['PLAN_OFF','STATE_ADMIN','NATL_ADMIN']}><ZoningDashboard /></RoleRouteGuard>} />
      <Route path="/officer/sync" element={<RoleRouteGuard allowed={['REV_OFF','REG_OFF','PLAN_OFF','TAX_OFF','STATE_ADMIN','NATL_ADMIN']}><SyncMonitor /></RoleRouteGuard>} />
      <Route path="/admin/state" element={<RoleRouteGuard allowed={['STATE_ADMIN']}><StateAdminPanel /></RoleRouteGuard>} />
      <Route path="/admin/national" element={<RoleRouteGuard allowed={['NATL_ADMIN']}><NationalAnalytics /></RoleRouteGuard>} />
      <Route path="/audit/:ulpin" element={<AuditTrailViewer />} />
      <Route path="/api-explorer" element={<ApiExplorer />} />
    </Routes></BrowserRouter>
  )
}
