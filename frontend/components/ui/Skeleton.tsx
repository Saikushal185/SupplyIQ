import clsx from "clsx";

interface SkeletonBlockProps {
  className?: string;
}

export function SkeletonBlock({ className }: SkeletonBlockProps) {
  return <div className={clsx("skeleton-shimmer", className)} aria-hidden="true" />;
}
