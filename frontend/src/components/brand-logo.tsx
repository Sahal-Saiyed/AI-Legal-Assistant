import { Scale } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

const bundledLogos = import.meta.glob("/src/assets/logo.png", {
  eager: true,
  import: "default",
  query: "?url",
}) as Record<string, string>;
const logoPath = import.meta.env.VITE_LOGO_PATH ?? bundledLogos["/src/assets/logo.png"];

interface BrandLogoProps {
  className?: string;
}

export function BrandLogo({ className }: BrandLogoProps) {
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <span
      className={cn(
        "grid size-11 shrink-0 place-items-center overflow-hidden rounded-2xl bg-primary text-primary-foreground shadow-float",
        className,
      )}
      aria-hidden="true"
    >
      {logoPath && !imageFailed ? (
        <img
          src={logoPath}
          alt=""
          className="size-full object-cover"
          onError={() => setImageFailed(true)}
        />
      ) : (
        <Scale className="size-5" strokeWidth={1.8} />
      )}
    </span>
  );
}
