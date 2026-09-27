export interface TextRun {
  text: string;
  options?: Record<string, unknown>;
}

export interface SlideLike {
  background: Record<string, unknown>;
  addImage(options: Record<string, unknown>): unknown;
  addNotes(notes: string): unknown;
  addShape(shapeName: string, options?: Record<string, unknown>): unknown;
  addTable(rows: unknown[][], options?: Record<string, unknown>): unknown;
  addText(text: string | TextRun[], options?: Record<string, unknown>): unknown;
}
