import { describe, expect, it } from "vitest";
import { CSS, contrast, rootTokens } from "./css";

describe("sistema de tokens", () => {
  const tokens = rootTokens();
  const names = Object.keys(tokens);
  const family = (prefix: string) => names.filter((n) => n.startsWith(prefix));

  it("preserva a identidade escura e âmbar", () => {
    expect(tokens["--bg"]).toBeDefined();
    expect(tokens["--accent"]).toBeDefined();
    // âmbar: matiz quente, com vermelho > verde > azul
    const [r, g, b] = tokens["--accent"].replace("#", "").match(/../g)!.map((h) => parseInt(h, 16));
    expect(r).toBeGreaterThan(g);
    expect(g).toBeGreaterThan(b);
  });

  it("tem escala de espaçamento em vez de valores mágicos", () => {
    expect(family("--space-").length).toBeGreaterThanOrEqual(6);
  });

  it("tem escala de raio", () => {
    expect(family("--radius-").length).toBeGreaterThanOrEqual(3);
  });

  it("tem escala de sombra/elevação", () => {
    expect(family("--shadow-").length).toBeGreaterThanOrEqual(2);
  });

  it("tem escala de duração de animação", () => {
    expect(family("--dur-").length).toBeGreaterThanOrEqual(3);
  });

  it("tem escala tipográfica", () => {
    expect(family("--text-size-").length).toBeGreaterThanOrEqual(5);
  });
});

describe("contraste WCAG (critério 8)", () => {
  const t = rootTokens();

  it("--text sobre --bg ≥ 4.5:1", () => {
    expect(contrast(t["--text"], t["--bg"])).toBeGreaterThanOrEqual(4.5);
  });

  it("--text-dim sobre --bg ≥ 4.5:1", () => {
    expect(contrast(t["--text-dim"], t["--bg"])).toBeGreaterThanOrEqual(4.5);
  });

  it("--text-dim sobre --bg-soft ≥ 4.5:1 (sidebar)", () => {
    expect(contrast(t["--text-dim"], t["--bg-soft"])).toBeGreaterThanOrEqual(4.5);
  });

  it("texto sobre --accent ≥ 4.5:1", () => {
    expect(t["--on-accent"]).toBeDefined();
    expect(contrast(t["--on-accent"], t["--accent"])).toBeGreaterThanOrEqual(4.5);
  });

  it("--danger sobre --bg ≥ 4.5:1", () => {
    expect(contrast(t["--danger"], t["--bg"])).toBeGreaterThanOrEqual(4.5);
  });

  it("--ok sobre --bg-soft ≥ 4.5:1 (backend online)", () => {
    expect(t["--ok"]).toBeDefined();
    expect(contrast(t["--ok"], t["--bg-soft"])).toBeGreaterThanOrEqual(4.5);
  });

  it("--accent sobre --bg ≥ 4.5:1 (usado como texto de título/rótulo)", () => {
    expect(contrast(t["--accent"], t["--bg"])).toBeGreaterThanOrEqual(4.5);
  });

  it("nenhuma cor hex crua fora do :root além das definições de token", () => {
    const body = CSS.slice(CSS.indexOf("}", CSS.indexOf(":root")));
    const stray = [...body.matchAll(/#[0-9a-fA-F]{3,8}\b/g)].map((m) => m[0]);
    expect(stray).toEqual([]);
  });
});
