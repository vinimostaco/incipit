import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const dialogOpen = vi.fn(async () => "/livros/metamorfose.epub");
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: (...a: unknown[]) => dialogOpen(...(a as [])) }));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ minimize: vi.fn(), toggleMaximize: vi.fn(), close: vi.fn() }),
}));

const api = {
  checkHealth: vi.fn(async () => true),
  extractBook: vi.fn(async () => BOOK),
  synthesize: vi.fn(async () => new Blob(["x"], { type: "audio/wav" })),
  pregenerate: vi.fn(async () => ({ id: "j1", status: "running", done: 1, total: 9, error: null })),
  pregenStatus: vi.fn(async () => ({ id: "j1", status: "running", done: 1, total: 9, error: null })),
  pregenCancel: vi.fn(async () => {}),
};
vi.mock("../src/api", () => api);

const BOOK = {
  title: "A Metamorfose",
  author: "Franz Kafka",
  source_format: "epub",
  chapters: [
    {
      index: 0,
      title: "I — O despertar",
      paragraphs: [
        { index: 0, text: "Gregor Samsa acordou de sonhos intranquilos." },
        { index: 1, text: "A colcha estava a ponto de escorregar." },
      ],
    },
  ],
};

const ENTRY = {
  id: "/livros/metamorfose.epub",
  path: "/livros/metamorfose.epub",
  title: "A Metamorfose",
  author: "Franz Kafka",
  format: "epub",
  engine: "piper",
  voice: "pt_BR-faber-medium",
  progressIndex: 0,
  totalParas: 2,
  addedAt: 1,
};

const PARAS = [
  { globalIndex: 0, chapterIndex: 0, chapterTitle: "I — O despertar", text: "Gregor Samsa acordou de sonhos intranquilos." },
  { globalIndex: 1, chapterIndex: 0, chapterTitle: "I — O despertar", text: "A colcha estava a ponto de escorregar." },
];

async function loadApp() {
  const { default: App } = await import("../src/App");
  return App;
}
async function loadReader() {
  const { Reader } = await import("../src/Reader");
  return Reader;
}

beforeEach(() => {
  vi.clearAllMocks();
  api.checkHealth.mockResolvedValue(true);
  api.extractBook.mockResolvedValue(BOOK);
  api.synthesize.mockResolvedValue(new Blob(["x"], { type: "audio/wav" }));
});

describe("titlebar customizada (critério 10)", () => {
  it("mantém a drag region e os três botões operantes", async () => {
    const App = await loadApp();
    const { container } = render(<App />);
    expect(container.querySelector("[data-tauri-drag-region]")).not.toBeNull();
    for (const name of ["Minimizar", "Maximizar", "Fechar"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
  });
});

describe("estado do backend legível em texto além da cor (critério 2)", () => {
  it("anuncia 'verificando', 'online' e 'offline' em texto", async () => {
    let resolve!: (v: boolean) => void;
    api.checkHealth.mockReturnValueOnce(new Promise<boolean>((r) => (resolve = r)));
    const App = await loadApp();
    render(<App />);

    const status = screen.getByTestId("backend-status");
    expect(status).toHaveAttribute("role", "status");
    expect(status.textContent).toMatch(/verificando/i);

    resolve(true);
    await waitFor(() => expect(screen.getByTestId("backend-status").textContent).toMatch(/online/i));

    api.checkHealth.mockResolvedValue(false);
    await waitFor(
      () => expect(screen.getByTestId("backend-status").textContent).toMatch(/offline/i),
      { timeout: 7000 },
    );
  }, 10000);
});

describe("extração em curso ganha corpo na página (critério 2)", () => {
  it("mostra um skeleton onde os parágrafos vão aparecer, não só o botão desabilitado", async () => {
    api.extractBook.mockReturnValue(new Promise(() => {}));
    const App = await loadApp();
    render(<App />);

    await userEvent.click(screen.getAllByRole("button", { name: /abrir livro/i })[0]);

    await waitFor(() => expect(screen.getByTestId("extract-skeleton")).toBeInTheDocument());
    const skeleton = screen.getByTestId("extract-skeleton");
    expect(skeleton).toHaveAttribute("aria-busy", "true");
    // o skeleton vive no corpo da página, não dentro do botão
    expect(skeleton.closest("button")).toBeNull();
    expect(skeleton.querySelectorAll(".skeleton-line").length).toBeGreaterThanOrEqual(3);
  });
});

describe("erros com tratamento consistente (critério 2)", () => {
  it("o erro de extração usa o componente de aviso compartilhado", async () => {
    api.extractBook.mockRejectedValue(new Error("PDF protegido por senha"));
    const App = await loadApp();
    render(<App />);

    await userEvent.click(screen.getAllByRole("button", { name: /abrir livro/i })[0]);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveClass("notice");
    expect(alert).toHaveClass("notice-error");
    expect(alert.textContent).toMatch(/PDF protegido por senha/);
  });

  it("o erro do player usa o mesmo componente de aviso", async () => {
    api.synthesize.mockRejectedValue(new Error("Motor XTTS indisponível"));
    const Reader = await loadReader();
    render(<Reader entry={ENTRY} paras={PARAS} onProgress={() => {}} onSettings={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: /reproduzir|pausar/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveClass("notice");
    expect(alert).toHaveClass("notice-error");
  });

  it("o erro de pré-geração usa o mesmo componente de aviso", async () => {
    api.pregenerate.mockRejectedValue(new Error("Falha ao iniciar"));
    const Reader = await loadReader();
    render(<Reader entry={ENTRY} paras={PARAS} onProgress={() => {}} onSettings={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: /^cap[íi]tulo$/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveClass("notice");
    expect(alert).toHaveClass("notice-error");
  });
});

describe("player.loading tem apresentação própria (critérios 2 e 9)", () => {
  it("não disputa slot com o título do capítulo", async () => {
    api.synthesize.mockReturnValue(new Promise(() => {}));
    const Reader = await loadReader();
    render(<Reader entry={ENTRY} paras={PARAS} onProgress={() => {}} onSettings={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: /reproduzir|pausar/i }));

    const loading = await screen.findByTestId("player-loading");
    const chapter = screen.getByTestId("player-chapter");

    // os dois coexistem: o carregamento não substitui o capítulo
    expect(loading).toBeInTheDocument();
    expect(chapter.textContent).toMatch(/O despertar/);
    expect(loading.contains(chapter)).toBe(false);
    expect(chapter.contains(loading)).toBe(false);

    // e é anunciado, não apenas desenhado
    expect(loading).toHaveAttribute("role", "status");
    expect(loading.textContent).toMatch(/gerando voz/i);
    // marca o player inteiro como ocupado, para leitor de tela e para o CSS
    expect(screen.getByTestId("player")).toHaveAttribute("data-loading", "true");
  });

  it("some quando o áudio fica pronto", async () => {
    const Reader = await loadReader();
    render(<Reader entry={ENTRY} paras={PARAS} onProgress={() => {}} onSettings={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: /reproduzir|pausar/i }));

    await waitFor(() =>
      expect(screen.getByTestId("player")).toHaveAttribute("data-loading", "false"),
    );
    expect(screen.queryByTestId("player-loading")).toBeNull();
  });
});

describe("biblioteca acessível pelo teclado (critério 7)", () => {
  it("cada livro é um elemento focável com nome acessível", async () => {
    localStorage.setItem("incipit.library", JSON.stringify([ENTRY]));
    const App = await loadApp();
    render(<App />);

    // o botão que abre o livro começa pelo título; renomear/remover são outros
    const item = await screen.findByRole("button", { name: /^A Metamorfose/ });
    expect(item).toBeInTheDocument();
    item.focus();
    expect(document.activeElement).toBe(item);
  });

  it("as ações de renomear e remover não ficam escondidas do teclado", async () => {
    localStorage.setItem("incipit.library", JSON.stringify([ENTRY]));
    const App = await loadApp();
    render(<App />);

    expect(await screen.findByRole("button", { name: /renomear/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /remover/i })).toBeInTheDocument();
  });
});
