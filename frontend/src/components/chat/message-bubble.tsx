import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  variant: "user" | "assistant";
  children: ReactNode;
  className?: string;
}

export function MessageBubble({ variant, children, className }: MessageBubbleProps) {
  return (
    <div
      className={cn(
        "min-w-0 break-words text-sm leading-6 [overflow-wrap:anywhere]",
        variant === "user"
          ? "max-w-[82%] rounded-[24px] rounded-br-lg bg-[#236f5f] px-5 py-3.5 text-white shadow-float sm:max-w-[70%]"
          : "w-full max-w-[88%] rounded-[28px] rounded-bl-lg border border-white/90 bg-white/90 p-5 text-slate-700 shadow-soft sm:p-6",
        className,
      )}
    >
      {children}
    </div>
  );
}
