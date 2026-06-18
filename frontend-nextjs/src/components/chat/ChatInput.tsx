"use client";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
  suggestions?: string[];
  onSuggestion?: (text: string) => void;
  footerNote?: string;
  onNewChat?: () => void;
  newChatLabel?: string;
};

export default function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
  placeholder = "Ask about your claim…",
  suggestions = [],
  onSuggestion,
  footerNote,
  onNewChat,
  newChatLabel = "New chat",
}: Props) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  };

  return (
    <div className="w-full border-t border-black/5 bg-white">
      <div className="mx-auto w-full max-w-3xl px-4 py-4 sm:px-6">
        {onNewChat && (
          <div className="mb-3 flex justify-center">
            <button
              type="button"
              onClick={onNewChat}
              disabled={disabled}
              className="rounded-full border border-border bg-white px-4 py-1.5 text-xs font-semibold text-text transition hover:border-plum-brand/30 hover:bg-plum-brand/5 disabled:opacity-50"
            >
              {newChatLabel}
            </button>
          </div>
        )}

        {suggestions.length > 0 && (
          <div className="mb-3 flex flex-wrap justify-center gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                disabled={disabled}
                onClick={() => onSuggestion?.(s)}
                className="rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-medium text-text transition hover:border-plum-brand/30 hover:bg-plum-brand/5 disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="relative flex items-end rounded-2xl border border-border bg-white shadow-sm ring-1 ring-black/[0.03] focus-within:border-plum-brand/40 focus-within:ring-plum-brand/10">
          <textarea
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            className="max-h-36 min-h-[52px] flex-1 resize-none bg-transparent px-4 py-3.5 text-[15px] text-text outline-none placeholder:text-text-muted/70 disabled:opacity-50"
          />
          <button
            type="button"
            onClick={onSend}
            disabled={disabled || !value.trim()}
            aria-label="Send message"
            className="m-2 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-plum-brand text-white transition hover:bg-plum-brand-dark disabled:bg-border disabled:text-text-muted"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 19V5M12 5L6 11M12 5l6 6"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        <p className="mt-2.5 text-center text-[11px] text-text-muted">
          {footerNote ??
            "Plum Claims Assistant explains your decision. For account issues, contact Plum support."}
        </p>
      </div>
    </div>
  );
}
