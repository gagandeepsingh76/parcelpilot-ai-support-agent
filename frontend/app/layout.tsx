import type { Metadata } from "next";
import { Caveat, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const caveat = Caveat({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-cursive",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-sans",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "ParcelPilot AI Support Agent",
  description:
    "B2B logistics support agent with cited answers, confirmation-gated actions, and internal insights.",
};

// Theme script: only light or dark, defaults to dark. No system mode.
const themeScript = `(function(){try{var p=localStorage.getItem("pp-theme");var d=p==="dark"||(p!=="light");document.documentElement.dataset.theme=d?"dark":"light";}catch(e){document.documentElement.dataset.theme="dark";}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${caveat.variable} ${inter.variable} ${mono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
