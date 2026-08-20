import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FloorMind — Factory AI",
  description: "The AI Brain for Your Factory",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
