// Primitivas de apresentação compartilhadas entre App e Reader.
import type * as React from "react";

/** Consulta única de prefers-reduced-motion (usada onde o CSS não alcança). */
export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;
}

type NoticeKind = "error" | "warn" | "info";

const ICON: Record<NoticeKind, string> = { error: "!", warn: "!", info: "i" };

interface NoticeProps {
  kind: NoticeKind;
  title?: string;
  children: React.ReactNode;
  onDismiss?: () => void;
}

/**
 * Aviso único para os três caminhos de erro do app (extração, player e
 * pré-geração), que antes tinham três aparências diferentes. Erros são
 * `role="alert"`; avisos e informações são `role="status"`, para não
 * interromper quem está no meio de uma escuta.
 */
export function Notice({ kind, title, children, onDismiss }: NoticeProps) {
  return (
    <div className={`notice notice-${kind}`} role={kind === "error" ? "alert" : "status"}>
      <span className="notice-icon" aria-hidden="true">
        {ICON[kind]}
      </span>
      <div className="notice-body">
        {title && <strong className="notice-title">{title}</strong>}
        {children}
      </div>
      {onDismiss && (
        <button type="button" className="notice-dismiss" onClick={onDismiss} aria-label="Dispensar aviso">
          <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
            <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.5" fill="none" />
          </svg>
        </button>
      )}
    </div>
  );
}

/**
 * Placeholder do corpo da página enquanto o texto é extraído. Comunica "está
 * vindo" no lugar onde os parágrafos vão aparecer — não só no rótulo do botão.
 */
export function ExtractSkeleton() {
  return (
    <div className="extracting" data-testid="extract-skeleton" aria-busy="true" aria-live="polite">
      <p className="extracting-head">
        <Spinner />
        Extraindo o texto do arquivo…
      </p>
      {[0, 1, 2].map((block) => (
        <div className="skeleton-block" key={block}>
          <div className="skeleton-line title" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
        </div>
      ))}
    </div>
  );
}

export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg
      className="spinner"
      width={size}
      height={size}
      viewBox="0 0 16 16"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.25" />
      <path d="M8 1.5a6.5 6.5 0 016.5 6.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
