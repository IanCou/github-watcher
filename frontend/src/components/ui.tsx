import { ReactNode } from "react";

export function Card({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      {children}
    </div>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost" | "danger";
  type?: "button" | "submit";
}) {
  const styles = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-500",
    ghost: "border border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800",
    danger: "text-red-600 hover:bg-red-50 dark:hover:bg-red-950",
  }[variant];
  return (
    <button
      type={type}
      onClick={onClick}
      className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${styles}`}
    >
      {children}
    </button>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none dark:border-slate-700"
    />
  );
}

const BADGE_TONES: Record<string, string> = {
  slate: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  green: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200",
  red: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200",
  indigo: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200",
};

export function Badge({
  children,
  tone = "slate",
}: {
  children: ReactNode;
  tone?: keyof typeof BADGE_TONES;
}) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${BADGE_TONES[tone] ?? BADGE_TONES.slate}`}
    >
      {children}
    </span>
  );
}
