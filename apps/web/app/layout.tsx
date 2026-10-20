import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Nav } from "@/components/nav";
import { Toaster } from "@/components/ui/sonner";
import "highlight.js/styles/github-dark.css";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin", "latin-ext"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Content Engine",
  description: "Tematy z RSS, research i redakcja artykułów z pomocą AI",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pl" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-zinc-50">
        <a href="#main-content" className="sr-only fixed left-4 top-2 z-50 rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background focus:not-sr-only focus:outline-2 focus:outline-offset-2 focus:outline-ring">Przejdź do treści</a>
        <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-2 px-4 sm:px-6">
            <span className="flex shrink-0 items-center gap-2 text-sm font-semibold tracking-tight sm:text-base">
              <span className="inline-block size-2.5 rounded-sm bg-emerald-600" />
              {/* Na telefonie tylko znak: nawigacja z czterema linkami i wylogowaniem musi się zmieścić. */}
              <span className="hidden sm:inline">Content Engine</span>
            </span>
            <Nav />
          </div>
        </header>
        <main id="main-content" tabIndex={-1} className="mx-auto w-full min-w-0 max-w-7xl flex-1 scroll-mt-28 px-4 py-6 focus-visible:outline-2 focus-visible:outline-ring sm:px-6 sm:py-8">{children}</main>
        <Toaster position="bottom-right" richColors />
      </body>
    </html>
  );
}
