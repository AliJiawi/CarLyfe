import type { Metadata } from "next";
import { Archivo, Barlow_Semi_Condensed, Space_Mono } from "next/font/google";
import "./globals.css";

// Fonts matched to the slide deck: wide heavy wordmark, condensed body, mono tagline.
const wordmark = Archivo({ subsets: ["latin"], axes: ["wdth"], variable: "--font-wordmark", display: "swap" });
const body = Barlow_Semi_Condensed({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-body", display: "swap" });
const tagline = Space_Mono({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-tagline", display: "swap" });

export const metadata: Metadata = {
  title: "CarLyfe | Fleet triage",
  description: "Upload fleet telematics and see which vehicles need service first, and why.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${wordmark.variable} ${body.variable} ${tagline.variable}`}>
      <head>
        {/* Apply a saved dark choice before first paint so there is no flash. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{if(localStorage.getItem("carlyfe-theme")==="dark")document.documentElement.dataset.theme="dark"}catch(e){}`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
