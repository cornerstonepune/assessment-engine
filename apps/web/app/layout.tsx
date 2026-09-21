import type { Metadata } from "next";
import { Source_Serif_4 } from "next/font/google";
import "./globals.css";

// One simple serif family for every voice — body, headings, labels and figures. PRINCIPLES.md.
const serif = Source_Serif_4({ subsets: ["latin"], variable: "--font-source-serif" });

export const metadata: Metadata = {
  title: "Cornerstone · Assessment",
  description: "Every child's worksheet, read and answered with the next one.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${serif.variable} h-full`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
