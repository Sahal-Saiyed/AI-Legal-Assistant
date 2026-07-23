import { Menu, UserRound } from "lucide-react";

import { Button } from "@/components/ui/button";

interface AppHeaderProps {
  onOpenSidebar: () => void;
  userName: string;
}

export function AppHeader({ onOpenSidebar, userName }: AppHeaderProps) {
  return (
    <header className="flex min-h-[76px] items-center justify-between border-b border-slate-100 bg-white px-4 sm:px-7">
      <div className="flex min-w-0 items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onOpenSidebar}
          className="shrink-0 lg:hidden"
          aria-label="Open sidebar"
        >
          <Menu className="size-4" />
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold tracking-[-0.025em] text-slate-950 sm:text-lg">
            AI Legal Assistant
          </h1>
          <p className="hidden truncate text-[11px] text-slate-400 sm:block">
            Clear answers grounded in trusted legal documents
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          className="flex h-10 max-w-52 items-center gap-2.5 rounded-full border border-slate-200 bg-white px-3 text-slate-700 shadow-sm transition hover:border-teal-200 hover:bg-teal-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
          aria-label="Open profile"
          title={userName}
        >
          <span className="grid size-7 shrink-0 place-items-center rounded-full bg-teal-50 text-teal-700">
            <UserRound className="size-4" strokeWidth={1.8} />
          </span>
          <span className="min-w-0 truncate text-xs font-semibold">{userName}</span>
        </button>
      </div>
    </header>
  );
}
