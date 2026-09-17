import type { Metadata } from "next";
import { Atkinson_Hyperlegible, JetBrains_Mono, Young_Serif } from "next/font/google";
import "./globals.css";

// The type triad: the child (body), the teacher (headings), the space (facts). PRINCIPLES.md.
const atkinson = Atkinson_Hyperlegible({ weight: ["400", "700"], subsets: ["latin"], variable: "--font-atkinson" });
const youngSerif = Young_Serif({ weight: "400", subsets: ["latin"], variable: "--font-young-serif" });
const jetbrains = JetBrains_Mono({ weight: ["400", "500", "600"], subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata: Metadata = {
  title: "Cornerstone · Assessment",
  description: "Every child's worksheet, read and answered with the next one.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${atkinson.variable} ${youngSerif.variable} ${jetbrains.variable} h-full`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
