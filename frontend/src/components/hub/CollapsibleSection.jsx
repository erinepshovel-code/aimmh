import React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export function CollapsibleSection({
  title,
  subtitle,
  icon: Icon,
  defaultOpen = false,
  testId,
  children,
  headerRight,
}) {
  const [open, setOpen] = React.useState(defaultOpen);

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid={testId}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-start justify-between gap-3 text-left"
        data-testid={`${testId}-toggle`}
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-zinc-100">
            {Icon ? <Icon size={16} /> : null}
            <h2 className="text-base font-semibold">{title}</h2>
          </div>
          {subtitle ? <p className="mt-1 text-xs text-zinc-500">{subtitle}</p> : null}
        </div>
        <div className="flex items-center gap-2">
          {headerRight}
          {open ? <ChevronDown size={16} className="text-zinc-400" /> : <ChevronRight size={16} className="text-zinc-400" />}
        </div>
      </button>

      {open ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}
