import { useEffect, useRef } from "react";

export function Input({ value, onChange, onSubmit, disabled }: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: (q: string) => void;
  disabled: boolean;
}) {
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (value) ref.current?.focus();
  }, [value]);

  return (
    <form onSubmit={(e) => { e.preventDefault(); if (value.trim()) onSubmit(value); }}>
      <input ref={ref} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled} />
      <button type="submit" disabled={disabled}>ask</button>
    </form>
  );
}
