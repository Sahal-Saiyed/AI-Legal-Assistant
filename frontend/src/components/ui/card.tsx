import type * as React from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-white/80 bg-card text-card-foreground shadow-soft",
        className,
      )}
      {...props}
    />
  );
}
