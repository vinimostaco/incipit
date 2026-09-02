// Utilitários de leitura do App.css. Os critérios de aceite desta tarefa são
// afirmações sobre a folha de estilo (reduced-motion, breakpoints, foco,
// contraste), então a folha é lida como dado e não como texto opaco.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// O ambiente jsdom não expõe `import.meta.url` como file://; a raiz do vitest
// é `app/`, então o caminho sai de process.cwd().
export const CSS = readFileSync(resolve(process.cwd(), "src/App.css"), "utf8");

/** Extrai o corpo de uma at-rule (@media/@supports) casando chaves. */
export function atRuleBodies(css: string, headerRe: RegExp): string[] {
  const out: string[] = [];
  const re = new RegExp(headerRe.source, headerRe.flags.includes("g") ? headerRe.flags : headerRe.flags + "g");
  let m: RegExpExecArray | null;
  while ((m = re.exec(css))) {
    const open = css.indexOf("{", m.index + m[0].length - 1);
    if (open < 0) continue;
    let depth = 0;
    let i = open;
    for (; i < css.length; i++) {
      if (css[i] === "{") depth++;
      else if (css[i] === "}") {
        depth--;
        if (depth === 0) break;
      }
    }
    out.push(css.slice(open + 1, i));
  }
  return out;
}

/** Remove todos os corpos de at-rules que casem com o header. */
export function withoutAtRule(css: string, headerRe: RegExp): string {
  let result = css;
  for (const body of atRuleBodies(css, headerRe)) result = result.replace(body, "");
  return result;
}

export const reducedMotionBlocks = () =>
  atRuleBodies(CSS, /@media[^{]*prefers-reduced-motion\s*:\s*reduce[^{]*/);

export const widthMediaQueries = () =>
  [...CSS.matchAll(/@media[^{]*\((?:max|min)-width\s*:\s*([^)]+)\)[^{]*/g)].map((m) => m[0]);

export const keyframeNames = () =>
  [...CSS.matchAll(/@keyframes\s+([\w-]+)/g)].map((m) => m[1]);

/** Declarações `animation`/`transition` fora do bloco de reduced-motion. */
export function motionDeclarations(): { animation: string[]; transition: string[] } {
  let outside = CSS;
  for (const body of reducedMotionBlocks()) outside = outside.replace(body, "");
  return {
    animation: [...outside.matchAll(/\banimation(?:-name)?\s*:\s*([^;}]+)/g)].map((m) => m[1].trim()),
    transition: [...outside.matchAll(/\btransition(?:-property)?\s*:\s*([^;}]+)/g)].map((m) => m[1].trim()),
  };
}

/** Tokens declarados no `:root`. */
export function rootTokens(): Record<string, string> {
  const root = CSS.match(/:root\s*\{([\s\S]*?)\n\}/);
  const tokens: Record<string, string> = {};
  if (!root) return tokens;
  for (const m of root[1].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) tokens[m[1]] = m[2].trim();
  return tokens;
}

// ------------------------------ contraste WCAG ------------------------------
export function parseHex(hex: string): [number, number, number] {
  const h = hex.trim().replace("#", "");
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16)) as [number, number, number];
}

function luminance(rgb: [number, number, number]): number {
  const [r, g, b] = rgb.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Razão de contraste WCAG 2.1 entre duas cores hex. */
export function contrast(a: string, b: string): number {
  const la = luminance(parseHex(a));
  const lb = luminance(parseHex(b));
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100;
}
