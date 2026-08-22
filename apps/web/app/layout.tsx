import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RecoverAI — AI Revenue Recovery Platform",
  description: "Detect revenue leakage. Decide the safest intervention. Recover the money. Prove the outcome.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#090d16] text-slate-100 antialiased selection:bg-emerald-500/30 selection:text-emerald-200">
        {children}
      </body>
    </html>
  );
}
