import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "AIGC Production Pipeline",
  description: "Local-first AIGC production workflow entry.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
