import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Lecturer System',
  description: 'Autonomous AI lecturer for slide-based instructional material',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
