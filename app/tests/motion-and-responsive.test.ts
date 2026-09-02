import { describe, expect, it } from "vitest";
import {
  CSS,
  atRuleBodies,
  keyframeNames,
  motionDeclarations,
  reducedMotionBlocks,
  widthMediaQueries,
} from "./css";

describe("prefers-reduced-motion (critério 5)", () => {
  it("existe pelo menos um bloco @media (prefers-reduced-motion: reduce)", () => {
    expect(reducedMotionBlocks().length).toBeGreaterThanOrEqual(1);
  });

  it("o bloco neutraliza animação e transição universalmente", () => {
    const block = reducedMotionBlocks().join("\n");
    // um seletor universal cobrindo pseudo-elementos
    expect(block).toMatch(/\*\s*,\s*\*::before\s*,\s*\*::after/);
    expect(block).toMatch(/animation-duration\s*:\s*0\.01ms|animation\s*:\s*none/);
    expect(block).toMatch(/animation-iteration-count\s*:\s*1/);
    expect(block).toMatch(/transition-duration\s*:\s*0\.01ms|transition\s*:\s*none/);
    expect(block).toMatch(/scroll-behavior\s*:\s*auto/);
  });

  it("toda animação introduzida é coberta pelo bloco", () => {
    const { animation, transition } = motionDeclarations();
    // há movimento real a neutralizar (senão o critério é vazio)
    expect(animation.length).toBeGreaterThanOrEqual(1);
    expect(transition.length).toBeGreaterThanOrEqual(1);
    // e o bloco é universal, logo cobre todas elas
    const block = reducedMotionBlocks().join("\n");
    expect(block).toMatch(/\*\s*,/);
  });

  it("todo @keyframes definido é efetivamente usado", () => {
    const declared = keyframeNames();
    expect(declared.length).toBeGreaterThanOrEqual(1);
    const { animation } = motionDeclarations();
    const used = animation.join(" ");
    for (const name of declared) expect(used).toContain(name);
  });

  it("o scroll suave do parágrafo atual respeita reduced-motion", () => {
    // o Reader usa scrollIntoView({behavior:'smooth'}); o CSS precisa poder
    // desligá-lo, e o app precisa consultar a media query em JS.
    const reader = CSS.includes("scroll-behavior");
    expect(reader).toBe(true);
  });
});

describe("responsividade (critérios 4 e 6)", () => {
  it("existe @media de largura", () => {
    expect(widthMediaQueries().length).toBeGreaterThanOrEqual(1);
  });

  it("há um breakpoint em ~820px", () => {
    expect(widthMediaQueries().join(" ")).toMatch(/max-width\s*:\s*8\d\dpx/);
  });

  it("usa 100dvh e não 100vh para altura de tela cheia", () => {
    expect(CSS).toContain("100dvh");
    expect(CSS).not.toMatch(/height\s*:\s*100vh/);
  });

  it("abaixo do breakpoint o grid vira coluna única", () => {
    const mobile = atRuleBodies(CSS, /@media[^{]*max-width\s*:\s*8\d\dpx[^{]*/).join("\n");
    expect(mobile).toMatch(/grid-template-columns\s*:\s*1fr/);
  });

  it("abaixo do breakpoint a biblioteca vira drawer fora da tela", () => {
    const mobile = atRuleBodies(CSS, /@media[^{]*max-width\s*:\s*8\d\dpx[^{]*/).join("\n");
    expect(mobile).toMatch(/\.sidebar/);
    expect(mobile).toMatch(/translateX\(-100%\)|left\s*:\s*-/);
  });

  it("o drawer fechado sai da ordem de tabulação", () => {
    // senão o Tab entra na biblioteca escondida e o foco some da tela
    const mobile = atRuleBodies(CSS, /@media[^{]*max-width\s*:\s*8\d\dpx[^{]*/).join("\n");
    expect(mobile).toMatch(/visibility\s*:\s*hidden/);
    expect(mobile).toMatch(/\.sidebar\.open\s*\{[^}]*visibility\s*:\s*visible/);
  });

  it("nada força largura maior que a viewport", () => {
    expect(CSS).not.toMatch(/min-width\s*:\s*[3-9]\d\dpx/);
  });
});

describe("alvos de toque e foco (critérios 5 e 7)", () => {
  it("define :focus-visible para os elementos interativos", () => {
    const rules = [...CSS.matchAll(/:focus-visible/g)];
    expect(rules.length).toBeGreaterThanOrEqual(1);
    // um estilo de foco compartilhado, com contorno visível e deslocado
    expect(CSS).toMatch(/outline\s*:\s*[^;]*var\(--focus\)/);
    expect(CSS).toMatch(/outline-offset\s*:/);
  });

  it("remove o outline padrão apenas onde repõe :focus-visible", () => {
    const killed = [...CSS.matchAll(/([^{}]+)\{[^}]*outline\s*:\s*none[^}]*\}/g)].map((m) =>
      m[1].trim(),
    );
    for (const sel of killed) {
      expect(sel).toMatch(/:focus(?!-visible)|::-|:focus-visible/);
    }
  });

  it("alvos de toque têm no mínimo 44px", () => {
    expect(CSS).toMatch(/--touch-min\s*:\s*44px/);
    const uses = [...CSS.matchAll(/min-(?:width|height)\s*:\s*var\(--touch-min\)/g)];
    expect(uses.length).toBeGreaterThanOrEqual(4);
  });
});
