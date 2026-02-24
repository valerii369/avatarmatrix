import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AVATAR — Эволюция Сознания",
  description: "Платформа трансформации через 176 архетипов по шкале Хокинса",
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  themeColor: "#060818",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <script src="https://telegram.org/js/telegram-web-app.js" />
      </head>
      <body className="stars-bg">{children}</body>
    </html>
  );
}
