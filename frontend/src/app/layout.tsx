import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Consilium - AI-Powered Decision Analysis",
  description:
    "Strategic scenario analysis through multi-expert deliberation and red team validation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <div className="min-h-screen bg-war-bg">
          {/* Header */}
          <header className="border-b border-war-border bg-war-surface/50 backdrop-blur-sm sticky top-0 z-50">
            <div className="container mx-auto px-4 h-14 flex items-center justify-between">
              <a href="/" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded bg-war-accent flex items-center justify-center">
                  <span className="text-black font-bold text-sm">C</span>
                </div>
                <span className="font-semibold text-war-text">Consilium</span>
              </a>
              <nav className="flex items-center gap-4 text-sm text-war-muted">
                <span>Strategic Analysis Platform</span>
              </nav>
            </div>
          </header>

          {/* Main content */}
          <main>{children}</main>

          {/* Footer */}
          <footer className="border-t border-war-border mt-auto py-6">
            <div className="container mx-auto px-4 text-center text-sm text-war-muted">
              Consilium - Multi-Expert Deliberation System
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
