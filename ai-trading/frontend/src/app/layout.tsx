import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import "./globals.css";
import { WalletProvider } from "@/context/WalletContext";
import Link from "next/link";
import ConnectWalletButton from "@/components/ConnectWalletButton";
import CreateAgentWalletButton from "@/components/CreateAgentWalletButton";
import { Bot, MessageSquareText, TrendingUp } from "lucide-react";

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "AI Trading Agent",
  description: "Hyperliquid Strategy Generator with AI Analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${poppins.variable} font-['Poppins'] antialiased`}>
        <WalletProvider>
          <div className="flex h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900">
            {/* Sidebar (applies to all pages) */}
            <aside className="w-64 border-r border-[#91F4B5]/20 bg-black/40 backdrop-blur flex flex-col">
              <div className="p-4 border-b border-[#91F4B5]/20">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-[#AEFEC3] to-[#91F4B5] rounded-lg flex items-center justify-center">
                    <Bot className="w-6 h-6 text-black" />
                  </div>
                  <div>
                    <div className="text-white font-semibold leading-tight">AI Trading Agent</div>
                    <div className="text-gray-400 text-xs">Hyperliquid Tools</div>
                  </div>
                </div>
              </div>

              <nav className="p-4 space-y-1 text-sm">
                <Link href="/" className="flex items-center gap-2 px-3 py-2 rounded-md text-gray-300 hover:text-black hover:bg-[#91F4B5] transition-colors">
                  <MessageSquareText className="w-4 h-4" />
                  Chat
                </Link>
                <Link href="/strategies" className="flex items-center gap-2 px-3 py-2 rounded-md text-gray-300 hover:text-black hover:bg-[#91F4B5] transition-colors">
                  <TrendingUp className="w-4 h-4" />
                  Strategies
                </Link>
              </nav>

              <div className="mt-auto p-4 border-t border-[#91F4B5]/20 flex flex-col gap-3">
                <Link
                  href="/strategies"
                  className="flex items-center justify-center w-full bg-[#91F4B5]/20 hover:bg-[#91F4B5]/30 text-[#91F4B5] px-4 py-2.5 rounded-lg text-sm border border-[#91F4B5]/30 transition-colors font-medium"
                >
                  My Strategies
                </Link>
                <div className="flex flex-col gap-2">
                  <div className="w-full">
                    <ConnectWalletButton />
                  </div>
                  <div className="w-full">
                    <CreateAgentWalletButton />
                  </div>
                </div>
              </div>
            </aside>

            {/* Main content */}
            <main className="flex-1 min-w-0 min-h-0 overflow-hidden">
              {children}
            </main>
          </div>
        </WalletProvider>
      </body>
    </html>
  );
}
