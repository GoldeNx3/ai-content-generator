import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { SparklesIcon } from "lucide-react";

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
  description: "Tematy z RSS, ocena AI, research, QA i publikacja artykułów w WordPress",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pl" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-zinc-50">
        <a href="#main-content" className="sr-only fixed left-4 top-2 z-50 rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background focus:not-sr-only focus:outline-2 focus:outline-offset-2 focus:outline-ring">Przejdź do treści</a>
        <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur-md">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-2 px-4 sm:px-6">
            <span className="flex shrink-0 items-center gap-2.5">
              <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 text-white shadow-sm shadow-emerald-700/30">
                <SparklesIcon className="size-4" />
              </span>
              {/* Na telefonie tylko znak: nawigacja z czterema linkami i wylogowaniem musi się zmieścić. */}
              <span className="hidden leading-tight sm:block">
                <span className="block text-sm font-semibold tracking-tight">Content Engine</span>
                <span className="block text-[11px] text-muted-foreground">Redakcja AI</span>
              </span>
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
