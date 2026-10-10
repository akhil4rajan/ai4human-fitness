import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Nav from "@/components/Nav";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI4Human",
  description: "A multi-agent wellness companion for nutrition, fitness, sleep and mental wellbeing.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="border-b border-border bg-surface">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-3">
            <span className="font-semibold">AI4Human</span>
            <Nav />
          </div>
        </header>
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">{children}</main>
        <footer className="border-t border-border px-4 py-3 text-center text-xs text-muted">
          Wellness guidance only, not medical advice. In an emergency call your local emergency number
          (US: 911; crisis line: 988).
        </footer>
      </body>
    </html>
  );
}
