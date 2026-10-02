import type { Metadata } from "next";
// Local font files from the `geist` package: no Google Fonts download, so the demo works offline.
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "PR Lifeguard",
  description: "Triage open pull requests by effort, not AI usage, and draft a kind reply for each.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <TooltipProvider delay={150}>{children}</TooltipProvider>
        <Toaster position="bottom-right" theme="light" />
      </body>
    </html>
  );
}
