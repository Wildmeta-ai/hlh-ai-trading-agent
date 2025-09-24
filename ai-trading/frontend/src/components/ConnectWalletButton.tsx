'use client'

import { useEffect, useRef, useState } from 'react'
import { useWallet } from '@/context/WalletContext'

function truncateAddress(addr: string) {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

export default function ConnectWalletButton() {
  const { address, chainId, connecting, hasProvider, connect, disconnect, copyAddress } = useWallet()
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [open])

  const handleCopy = async () => {
    await copyAddress()
    setCopied(true)
    setTimeout(() => setCopied(false), 1200)
  }

  if (!hasProvider && !address) {
    return (
      <a
        href="https://metamask.io/download/"
        target="_blank"
        rel="noreferrer"
        className="block w-full text-center px-4 py-2.5 rounded-lg border border-[#91F4B5]/40 text-[#91F4B5] hover:bg-[#91F4B5]/10 transition-colors text-sm font-medium"
      >
        Install Wallet
      </a>
    )
  }

  if (!address) {
    return (
      <button
        onClick={connect}
        disabled={connecting}
        className="w-full bg-[#91F4B5]/20 hover:bg-[#91F4B5]/30 text-[#91F4B5] px-4 py-2.5 rounded-lg text-sm border border-[#91F4B5]/30 transition-colors disabled:opacity-60 font-medium"
      >
        {connecting ? 'Connecting...' : 'Connect Wallet'}
      </button>
    )
  }

  return (
    <div className="relative w-full" ref={menuRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full px-4 py-2.5 rounded-lg bg-[#AEFEC3]/15 hover:bg-[#AEFEC3]/25 text-[#AEFEC3] border border-[#AEFEC3]/30 text-sm font-medium transition-colors"
      >
        {truncateAddress(address)}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 min-w-[220px] rounded-lg bg-black/80 backdrop-blur-md border border-[#91F4B5]/20 shadow-lg p-2 z-20">
          <div className="px-3 py-2">
            <div className="text-xs text-gray-400">Connected</div>
            <div className="text-sm text-white font-medium">{truncateAddress(address)}</div>
            {chainId && (
              <div className="text-xs text-gray-500 mt-1">Chain ID: {parseInt(chainId, 16)}</div>
            )}
          </div>
          <div className="h-px bg-[#91F4B5]/20 my-1" />
          <button
            onClick={handleCopy}
            className="w-full text-left px-3 py-2 rounded-md hover:bg-white/5 text-sm text-gray-200"
          >
            {copied ? 'Copied!' : 'Copy Address'}
          </button>
          <button
            onClick={() => {
              disconnect()
              setOpen(false)
            }}
            className="w-full text-left px-3 py-2 rounded-md hover:bg-[#DA373B]/10 text-sm text-[#DA373B]"
          >
            Disconnect
          </button>
        </div>
      )}
    </div>
  )
}

