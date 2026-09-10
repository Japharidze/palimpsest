import { useState } from "react";

export function Input({ onSubmit, disabled }: { onSubmit: (q: string) => void; disabled: boolean }) {
  const [text, setText] = useState("");

  return (
    <form onSubmit={(e) => { e.preventDefault(); if (text.trim()) { onSubmit(text); setText(""); } }}>
      <input value={text} onChange={(e) => setText(e.target.value)} disabled={disabled} />
      <button type="submit" disabled={disabled}>ask</button>
    </form>
  );
}
