type FlagSize = "sm" | "md" | "lg" | "xl";

const SIZE_CLASSES: Record<FlagSize, string> = {
  sm: "h-3.5 w-5",
  md: "h-4 w-6",
  lg: "h-5 w-7",
  xl: "h-8 w-12",
};

export default function CountryFlag({
  code,
  country,
  size = "md",
  className = "",
}: {
  code: string | null | undefined;
  country: string;
  size?: FlagSize;
  className?: string;
}) {
  if (!code) return null;

  return (
    <span
      className={`fi fi-${code.toLowerCase()} shrink-0 overflow-hidden rounded-[2px] border border-white/15 bg-cover shadow-sm ${SIZE_CLASSES[size]} ${className}`}
      role="img"
      aria-label={`${country} flag`}
      title={country}
    />
  );
}
