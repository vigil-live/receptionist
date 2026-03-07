import './globals.css'

export const metadata = {
  title: 'Vigil — Emergency Dispatch',
  description: 'AI-powered 911 dispatch platform',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}