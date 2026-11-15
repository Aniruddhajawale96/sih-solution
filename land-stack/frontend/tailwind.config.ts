import type { Config } from 'tailwindcss'
const config: Config = {
  content: ['./index.html','./src/**/*.{ts,tsx}'],
  theme: { extend: { colors: { primary: '#1e40af', secondary: '#059669', danger: '#dc2626' } } },
  plugins: []
}
export default config
