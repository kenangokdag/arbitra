import type { Metadata } from "next";
import {
  Inter,
  Lora,
  Geist,
  Geist_Mono,
  Crimson_Pro,
  Space_Grotesk,
  Source_Sans_3,
  Newsreader,
  Source_Serif_4,
} from "next/font/google";
import { QueryProvider } from "@/lib/query-client";
import { ThemeProvider } from "@/components/ThemeProvider";
import "@/styles/globals.css";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
  display: "swap",
});

const lora = Lora({
  subsets: ["latin", "latin-ext"],
  variable: "--font-lora",
  display: "swap",
  style: ["normal", "italic"],
});

// FAZ 4B — tema font allowlist'i (api/models/theme.py:24-27) GERÇEKTEN yüklenir.
// Her biri kendi CSS değişkenine bağlanır; tema seçimi lib/theme.ts FONT_*_MAP ile
// bu değişkenlere MAP edilir. Yüklenmemiş font seçilemez (UYDURMA YOK).
const sourceSans = Source_Sans_3({
  subsets: ["latin", "latin-ext"],
  variable: "--font-source-sans",
  display: "swap",
});

const newsreader = Newsreader({
  subsets: ["latin", "latin-ext"],
  variable: "--font-newsreader",
  display: "swap",
  style: ["normal", "italic"],
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin", "latin-ext"],
  variable: "--font-source-serif",
  display: "swap",
  style: ["normal", "italic"],
});

const crimsonPro = Crimson_Pro({
  subsets: ["latin", "latin-ext"],
  variable: "--font-crimson",
  display: "swap",
  style: ["normal", "italic"],
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: {
    default: "Arbitra — Göndermeden önce, bağımsız hakem.",
    template: "%s · Arbitra",
  },
  description: "Göndermeden önce, bağımsız hakem. Akademik makaleniz için bağımsız ön-değerlendirme.",
  applicationName: "Arbitra",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr" className={cn(inter.variable, lora.variable, crimsonPro.variable, geist.variable, geistMono.variable, spaceGrotesk.variable, sourceSans.variable, newsreader.variable, sourceSerif.variable, "font-sans")}>
      <body>
        <QueryProvider>
          <ThemeProvider>{children}</ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
