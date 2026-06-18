"use client";

import Link from "next/link";
import type { Audience, AudienceConfig } from "./chatConfig";
import { PORTAL_SECTIONS } from "./chatConfig";
import PlumLogo from "./PlumLogo";

type Props = {
  audience: Audience;
  config: AudienceConfig;
  onNewChat: () => void;
  onToggleSidebar?: () => void;
  showSidebarToggle?: boolean;
};

export default function ChatHeader({
  audience,
  config,
  onNewChat,
  onToggleSidebar,
  showSidebarToggle,
}: Props) {
  return (
    <header className="z-30 w-full shrink-0 border-b border-black/5 bg-white shadow-[0_1px_0_rgba(0,0,0,0.03)]">
      <div className="flex h-14 w-full items-center justify-between gap-2 px-4 sm:gap-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          {showSidebarToggle && onToggleSidebar && (
            <button
              type="button"
              onClick={onToggleSidebar}
              aria-label="Open sidebar"
              className="rounded-lg p-2 text-text-muted transition hover:bg-surface-muted hover:text-text lg:hidden"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />
              </svg>
            </button>
          )}
          <PlumLogo className="h-6 w-auto shrink-0" />
          <div className="hidden h-5 w-px bg-border md:block" />
          <div className="hidden min-w-0 md:block">
            <p className="truncate text-sm font-semibold text-text">{config.title}</p>
            <p className="truncate text-xs text-text-muted">{config.subtitle}</p>
          </div>
        </div>

        <nav
          aria-label="Portal sections"
          className="flex shrink-0 items-center gap-0.5 rounded-lg bg-surface-muted p-0.5 sm:gap-1 sm:p-1"
        >
          {PORTAL_SECTIONS.map((section) => {
            const active = audience === section.audience;
            return (
              <Link
                key={section.href}
                href={section.href}
                className={`rounded-md px-2 py-1.5 text-xs font-medium transition sm:px-3 sm:text-sm ${
                  active
                    ? "bg-white text-text shadow-sm"
                    : "text-text-muted hover:text-text"
                }`}
              >
                {section.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex shrink-0 items-center">
          <button
            type="button"
            onClick={onNewChat}
            className="rounded-lg bg-plum-brand px-2.5 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-plum-brand-dark sm:px-4 sm:text-sm"
          >
            {config.newClaimLabel}
          </button>
        </div>
      </div>
    </header>
  );
}
