import { Settings } from "lucide-react";
import { NavLink } from "react-router-dom";

import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navigation = [
  { label: "Workspace", to: "/" },
  { label: "Documents", to: "/documents" },
  { label: "About", to: "/about" },
];

export function TopNavigation() {
  return (
    <header className="sticky top-0 z-30 px-3 pt-3 sm:px-6 sm:pt-4 lg:px-8">
      <nav className="relative mx-auto flex h-16 max-w-[1480px] items-center justify-between rounded-[24px] border border-white/80 bg-white/85 px-3 shadow-float backdrop-blur-xl sm:h-[72px] sm:px-5" aria-label="Primary navigation">
        <NavLink to="/" className="flex items-center gap-3" aria-label="JuriGPT home">
          <BrandLogo />
          <div>
            <p className="text-[17px] font-semibold tracking-[-0.025em] text-slate-900">JuriGPT</p>
            <p className="hidden text-[10px] font-medium uppercase tracking-[0.16em] text-slate-400 sm:block">
              Legal clarity
            </p>
          </div>
        </NavLink>

        <div className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 rounded-full bg-stone-100/80 p-1 md:flex">
          {navigation.map((item) => (
            <NavLink
              key={item.label}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "rounded-full px-4 py-2 text-xs font-medium transition-colors",
                  isActive
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-900",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label="Settings" title="Settings">
            <Settings className="size-4" strokeWidth={1.8} />
          </Button>
          <button
            type="button"
            className="grid size-10 place-items-center rounded-full bg-[#d7eee7] text-xs font-semibold text-[#176b5a] ring-4 ring-white transition-transform hover:scale-105"
            aria-label="Open user profile"
          >
            JU
          </button>
        </div>
      </nav>
    </header>
  );
}
