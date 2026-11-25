/**
 * Extensão e MIME para artefactos exportados (chaves do mapa devolvidas pela API).
 * Ficheiro dedicado para evitar desalinhamento de linhas no analisador Sonar JS/TS (CPD/highlights).
 */

export function extFor(key: string): string {
  if (key.includes("mermaid")) return "mmd";
  if (key.includes("markdown")) return "md";
  return "json";
}

export function mimeFor(key: string): string {
  if (key.includes("markdown")) return "text/markdown;charset=utf-8";
  if (key.includes("mermaid")) return "text/plain;charset=utf-8";
  return "application/json;charset=utf-8";
}


export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = globalThis.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
