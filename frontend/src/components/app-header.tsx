import { Menu, Search, UserRound } from "lucide-react";

import { Button } from "@/components/ui/button";

interface AppHeaderProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onOpenSidebar: () => void;
}

export function AppHeader({ searchQuery, onSearchChange, onOpenSidebar }: AppHeaderProps) {
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
        <label className="relative hidden md:block">
          <span className="sr-only">Search conversation history</span>
          <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <input
            id="history-search"
            type="search"
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search"
            className="h-10 w-64 rounded-full border border-slate-200 bg-slate-50/70 pl-11 pr-14 text-xs text-slate-700 outline-none transition focus:border-teal-400 focus:bg-white focus:ring-2 focus:ring-teal-100"
          />
          <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[9px] text-slate-400">
            Ctrl K
          </kbd>
        </label>
        <button
          type="button"
          className="grid size-10 place-items-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:border-teal-200 hover:bg-teal-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
          aria-label="Open profile"
          title="Profile"
        >
          <UserRound className="size-4" strokeWidth={1.8} />
        </button>
      </div>
    </header>
  );
}
