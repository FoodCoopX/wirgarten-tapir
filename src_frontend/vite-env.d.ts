/// <reference types="vite/client" />

interface Window {
  bootstrap?: {
    Tooltip: {
      new (
        element: Element,
        options?: Partial<Record<string, unknown>>,
      ): { dispose(): void };
      getInstance(element: Element): { dispose(): void } | null;
    };
  };
}
