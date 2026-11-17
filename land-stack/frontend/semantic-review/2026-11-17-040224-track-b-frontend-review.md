# Land Stack Track B — Frontend Code Review

All 16 screen files, plus `App.tsx`, `authStore.ts`, `apiClient.ts`, `RoleRouteGuard.tsx`, and `TopNav.tsx` were reviewed. The screens were written by automated subagents, so many share the same structural patterns; bugs and improvements are noted once and cross-referenced where the same pattern recurs.

**Watch for:** (1) `ZoningDashboard` accumulates duplicate `map.once('load', ...)` listeners every time `violations` re-renders before the map is loaded — markers will be added multiple times. (2) `CitizenDashboard` is a full copy-paste of `OfficerLogin` and renders a login form under a "dashboard" route, which citizens land on after authentication — a routing dead-end. (3) `SyncMonitor` passes the JWT as a URL query parameter, leaking the token into server logs and browser history. (4) `authStore` persists the access token to `localStorage` without expiry handling, and there is no token refresh interceptor despite `refresh_token` being stored.

**Verdict**: NEEDS_CHANGES

---

## High-level view

`CitizenDashboard` is not a dashboard — it is an exact duplicate of `OfficerLogin` with a different icon and color. Any citizen who logs in and is routed to `/citizen/dashboard` sees another login form instead of a post-login landing page. This is a functional dead-end and needs a real citizen home screen.

The `ZoningDashboard` marker system has a race-condition accumulation bug. The markers `useEffect` correctly clears existing markers at the start, but when the map hasn't finished loading it registers a `map.once('load', addMarkers)` listener. If `violations` changes again before the map loads (React Query refetches, StrictMode double-invoke), a second listener queues up and markers will be added twice. The fix is to cancel the pending listener before registering a new one.

`SyncMonitor` constructs its SSE URL with the JWT appended as `?token=...`. This leaks the bearer token into HTTP access logs on any intermediary and into the browser's navigation history. The standard approach for SSE auth in a same-origin SPA is to send the token as a cookie, or to have the server issue a short-lived SSE-specific token exchanged via a POST.

The auth layer has two compounding weaknesses: tokens are persisted to `localStorage` via Zustand `persist` with no expiry check, and there is no Axios response interceptor to handle 401s or trigger a refresh. The `refresh_token` field is stored but never used. Any expired session silently fails every API call.

`maskCitizenData` in `Parcel360View` is a client-side-only privacy control — it masks `owner_name` and `transaction_value` in the React render tree, but the unmasked values are present in the network response visible in browser DevTools. This is a UI affordance, not a security control, but it needs a comment making that explicit so future maintainers don't rely on it for security.

The `AuditTrailViewer` chain verification runs entirely client-side against data fetched from the same server. A compromised server can serve consistent-but-fabricated `chain_hash` values that pass the client-side SHA-256 check. The UI banner saying "has not been tampered with" is accurate only if the server is trusted — the UI should clarify this scope.

The `toggleMutation.variables` type assertion in `StateAdminPanel` is correct for TanStack Query v5 — `variables` is typed as the mutation's input type when the mutation is pending, so the cast is safe.

`/parcel/:ulpin/verify` and `/audit/:ulpin` are not wrapped in `RoleRouteGuard`, so unauthenticated users can access them. Whether that is intentional (public ownership lookup) needs to be confirmed; the current behavior should be explicitly documented in the route definition.

---

<details>
<summary>Issues (13)</summary>

1. **CitizenDashboard is a login form, not a dashboard** — Replace with a real post-login citizen landing page, or redirect `/citizen/dashboard` to `/citizen/services` after login. As-is, authenticated citizens hit another login form.

2. **ZoningDashboard: duplicate marker accumulation on map load** — The markers `useEffect` registers `map.once('load', addMarkers)` without cancelling any previously registered listener. On re-render before map loads, markers are added N times. Cancel the queued listener at the top of the effect before conditionally re-registering.

3. **SyncMonitor: JWT in URL query string** — `?token=${accessToken}` leaks the bearer token into access logs and browser history. Use a cookie-based auth or a server-issued ephemeral SSE token instead.

4. **No 401 / token-refresh interceptor in apiClient** — Expired sessions fail silently. Add a response interceptor that calls the refresh endpoint and retries, or clears auth and redirects to login on 401.

5. **authStore: access token persisted to localStorage with no expiry** — Tokens survive indefinitely across sessions. Add expiry metadata and validate on load, or use `sessionStorage`.

6. **maskCitizenData is a UI mask, not a security control** — The raw data is visible in DevTools network tab. Add a comment to prevent future maintainers from treating this as access control. The backend should enforce field-level access.

7. **AuditTrailViewer: client-side chain verification trust boundary** — The "Chain Intact" banner implies tamper-evidence but only holds if the server is not compromised. The UI should qualify the claim ("verified against server-provided hashes").

8. **`/parcel/:ulpin/verify` and `/audit/:ulpin` are unguarded** — No `RoleRouteGuard` wraps these routes. Confirm and document whether public access is intentional.

9. **TypeScript: `error as Error` and `error as { message?: string }` casts throughout** — TanStack Query v5 types `error` as `Error | null`. Using `(error as Error)?.message` is safe but the outer `?` is redundant since `isError` guarantees non-null. The inconsistent `{ message?: string }` cast in `OfficerDashboard` and `WorkflowApproval` can silently hide the actual error type. Use `error instanceof Error ? error.message : String(error)` for robust handling.

10. **ZoningDashboard: popup HTML interpolates `v.ulpin` and `v.violation_type` without escaping** — If the server returns a ULPIN or violation type containing `<script>` or HTML characters, the `setHTML()` call renders it. Sanitize these values before interpolation, or use `setDOMContent()` with text nodes.

11. **GisMapExplorer: state filter `console.log` left in production code** — `LayerPanel.handleStateChange` calls `console.log('[LayerPanel] state filter changed:', value)` and the state filter itself does nothing (no map filter applied). Remove the log and either wire up the filter or remove the UI element.

12. **NationalAnalytics / StateAdminPanel: placeholder data silently substituted on API failure** — When `state_breakdown` / `district_breakdown` is empty OR when the API returns no data at all, hardcoded placeholder data is shown with no visual indication it is not real. A user could make decisions on fabricated numbers. Show an empty state or a "no data" message instead.

13. **React keys using array index** — `OwnershipVerification > DataTable` and `Parcel360View > DataTable` use `idx` as keys in `.map()` over API-returned arrays. If the server reorders items, React will not reconcile correctly. Use a stable field (`entry_id`, `ulpin`, or similar) where available.

</details>

---

<details>
<summary>Details</summary>

### CitizenDashboard is a copy-paste of OfficerLogin

`CitizenDashboard.tsx` contains an identical login form to `OfficerLogin.tsx` — same `LoginResponse` interface, same `roleToRoute` function, same `handleSubmit` logic — with only the icon changed from 🛡️ to 👤 and the button color from indigo to blue. The route `/citizen/dashboard` is where citizens land after `roleToRoute` returns `'/citizen/services'` for `CITIZEN` role... except it doesn't: `roleToRoute` returns `'/citizen/services'`, so the citizen never reaches `/citizen/dashboard` via normal login flow. The route is dead from the citizen's perspective, but it still renders a second login form if navigated to directly, which is confusing and incorrect.

**Fix (🔴):** Replace `CitizenDashboard` with a real landing page for authenticated citizens — links to service request portal and request tracking — or delete the route and redirect to `/citizen/services`.

### ZoningDashboard: `map.once` listener accumulation (confirmed)

```
// markers useEffect runs when violations changes
if (map.loaded()) {
  addMarkers()
} else {
  map.once('load', addMarkers)   // ← no way to cancel this
}
```

If `violations` updates before the map fires `load`, each render queues another `addMarkers` call onto the same `once` listener (which is not actually `once` in the cancellation sense — MapLibre's `once` fires once per registration, so N registrations = N calls). On first real data arrival, all queued callbacks fire and markers multiply.

**Fix (🔴):** Track the pending callback in a ref and remove it before registering a new one:

```ts
const pendingAddMarkersRef = useRef<(() => void) | null>(null)

// In the markers useEffect, before the if/else:
if (pendingAddMarkersRef.current) {
  map.off('load', pendingAddMarkersRef.current)
  pendingAddMarkersRef.current = null
}

if (map.loaded()) {
  addMarkers()
} else {
  pendingAddMarkersRef.current = addMarkers
  map.once('load', addMarkers)
}
```

Also add cleanup in the map-init `useEffect` return to remove the pending listener before the map is destroyed.

### SyncMonitor: token in URL

The EventSource is constructed as:
```ts
const url = accessToken
  ? `/api/v1/workflow/events/stream?token=${encodeURIComponent(accessToken)}`
  : '/api/v1/workflow/events/stream'
```

`EventSource` does not support custom request headers, so there is no clean alternative without a server-side change. The least-bad client-side options are: (a) use a short-lived query token exchanged via a pre-flight POST, or (b) rely on `HttpOnly` session cookies set at login. This is a known limitation of the `EventSource` API and needs a backend-coordinated fix. The issue should be documented and the unauthenticated fallback URL should not be used (it currently serves the stream without auth if no token is present).

**Fix (🔴 partial):** Remove the unauthenticated fallback — if there is no token, do not open the EventSource at all and show an "authentication required" message instead.

### StateAdminPanel: `toggleMutation.variables` cast

In TanStack Query v5, `useMutation` infers `variables` from the `mutationFn` signature. The check:
```ts
(toggleMutation.variables as { user_id: string } | undefined)?.user_id === user.user_id
```
is correct behavior but the cast is unnecessary — if the `mutationFn` is typed `({ user_id, is_active }: { user_id: string; is_active: boolean }) => ...`, then `toggleMutation.variables` is already typed as `{ user_id: string; is_active: boolean } | undefined`. The cast should be removed in favor of the inferred type. This is a 🟡 warning, not a bug.

### AuditTrailViewer: chain verification logic

The `verifyChain` function reverses the display-order array to get chronological order, then for each entry computes `SHA-256(prev_hash + payload_hash)` and compares to `entry.chain_hash`. This is correct for entries 2..N. The genesis entry (first chronologically) will have some sentinel `prev_hash` (typically `"0".repeat(64)` or `""`) defined by the backend — the client just trusts whatever value the server sent as `prev_hash` for that first entry, which means a corrupted genesis entry cannot be detected. This is an inherent limitation of a client-side verifier without a trusted anchor, not a code bug.

The logic is otherwise correct. 🟡 — document the genesis entry limitation.

### ZoningDashboard popup XSS (confirmed)

```ts
const popup = new maplibregl.Popup({ offset: 12, closeButton: false })
  .setHTML(`
    ...${v.ulpin}...${v.violation_type}...
  `)
```

`v.ulpin` and `v.violation_type` are rendered via `innerHTML` with no escaping. If the backend returns `violation_type: "<img src=x onerror=alert(1)>"`, it executes in the popup. This is a stored XSS vector in an authenticated officer context — severity depends on what the backend accepts, but the client should not trust it.

**Fix (🔴):** Replace `setHTML` with `setDOMContent` using manually constructed DOM elements, or escape the values before interpolation.

### GisMapExplorer: markers effect and stale closure

The `ViolationMap` in `ZoningDashboard` has the stale-closure issue described above. The `GisMapExplorer` does not use a separate markers effect — it registers a `map.on('click', 'parcels-fill', ...)` handler at map load time, which only fires once and reads from the vector tile feature properties directly, so there is no stale closure issue there. ✓

### apiClient: no response interceptor for 401

The interceptor only sets the Authorization header on requests. There is no response interceptor. When a token expires, every API call returns 401 and the UI shows an error banner, but the user is not redirected to login and the stale token stays in `localStorage`. This affects all 16 screens simultaneously.

**Fix (🟡 warning):** Add a response interceptor:
```ts
apiClient.interceptors.response.use(
  r => r,
  err => {
    if (err?.response?.status === 401) {
      useAuthStore.getState().clearAuth()
      window.location.href = '/citizen/dashboard'
    }
    return Promise.reject(err)
  }
)
```

### NationalAnalytics / StateAdminPanel: silent placeholder data

Both screens fall back to hardcoded placeholder arrays when the API returns an empty `state_breakdown` / `district_breakdown`. There is no visual indicator that the data is placeholder. A national admin looking at the charts during initial rollout would see fabricated state-level data.

**Fix (🟡 warning):** Show a "No data available" empty state instead of placeholder arrays, or add a visible "Sample data" label.

### TopNav: hardcoded ULPIN in Verify link

```tsx
<Link to="/parcel/CH-UT-000001/verify" className="hover:underline">Verify</Link>
```

The nav always links to parcel `CH-UT-000001` regardless of context. This is almost certainly a placeholder left in from development.

**Fix (🔵 improvement):** Remove the hardcoded link. The Verify screen has its own ULPIN input — link to `/parcel/verify` or a search entry point instead.

### React keys using index

`DataTable` in both `Parcel360View` and `OwnershipVerification` renders:
```tsx
{data.map((item, idx) => (
  <div key={idx} ...>
```
Index keys cause incorrect reconciliation if the server reorders array items between fetches.

**Fix (🔵 improvement):** Use a stable field from the item if available; otherwise generate a key from a hash of the entry's identifying fields.

</details>

---

<details>
<summary>File map</summary>

| File | What changed / reviewed |
|---|---|
| `CitizenDashboard.tsx` | 🔴 Duplicate of OfficerLogin — not a citizen dashboard |
| `OfficerLogin.tsx` | ✓ Structurally identical to CitizenDashboard; correct for officer use |
| `Parcel360View.tsx` | 🟡 `maskCitizenData` is UI-only; exports correctly for OwnershipVerification |
| `OwnershipVerification.tsx` | ✓ `maskCitizenData` import verified present in Parcel360View |
| `GisMapExplorer.tsx` | 🟡 State filter is a no-op with a console.log; map click handling is correct |
| `ServiceRequestPortal.tsx` | ✓ No bugs found |
| `RequestTracking.tsx` | ✓ No bugs found |
| `OfficerDashboard.tsx` | 🟡 `error as { message?: string }` unsafe cast pattern |
| `WorkflowApproval.tsx` | ✓ `task_id` query param name matches OfficerDashboard navigation |
| `ZoningDashboard.tsx` | 🔴 `map.once` listener accumulation; 🔴 popup XSS via `setHTML` |
| `SyncMonitor.tsx` | 🔴 JWT in URL query string; 🔴 unauthenticated SSE fallback |
| `StateAdminPanel.tsx` | 🟡 Unnecessary type cast on `toggleMutation.variables`; placeholder data risk |
| `NationalAnalytics.tsx` | 🟡 Placeholder data shown silently on empty API response |
| `AuditTrailViewer.tsx` | 🟡 Genesis entry cannot be verified; client-side trust boundary undocumented |
| `ApiExplorer.tsx` | ✓ No bugs found |
| `App.tsx` | 🟡 `/audit/:ulpin` and `/parcel/:ulpin/verify` unguarded |
| `authStore.ts` | 🟡 Token persisted to localStorage with no expiry |
| `apiClient.ts` | 🟡 No 401 / refresh interceptor |
| `RoleRouteGuard.tsx` | ✓ Logic correct |
| `TopNav.tsx` | 🔵 Hardcoded ULPIN in Verify nav link |

</details>
