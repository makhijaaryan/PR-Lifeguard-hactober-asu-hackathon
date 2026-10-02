/** Lifeguard ring: red ring with four white bands and a hairline outline so it reads on white. */
export function LogoMark({ className = "size-6" }: { className?: string }) {
  const r = 8.5; // ring centre-line radius
  const c = 2 * Math.PI * r;
  const band = c / 8; // four white bands, each 1/8 of the circumference
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <circle cx="12" cy="12" r={r} fill="none" stroke="#E5484D" strokeWidth="5" />
      <circle
        cx="12"
        cy="12"
        r={r}
        fill="none"
        stroke="#fff"
        strokeWidth="5"
        strokeDasharray={`${band} ${band}`}
        strokeDashoffset={band / 2}
        transform="rotate(45 12 12)"
      />
      <circle cx="12" cy="12" r="11" fill="none" stroke="#E5484D" strokeWidth="0.75" opacity="0.55" />
      <circle cx="12" cy="12" r="6" fill="none" stroke="#E5484D" strokeWidth="0.75" opacity="0.55" />
    </svg>
  );
}
