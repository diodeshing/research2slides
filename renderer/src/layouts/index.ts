import type { SlideLayout } from "../types.js";

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LayoutBoxes {
  title: Box;
  content: Box;
  text: Box;
  visual: Box;
  takeaway: Box;
  citation: Box;
}

const TITLE: Box = { x: 0.72, y: 0.56, w: 11.9, h: 0.75 };
const TAKEAWAY: Box = { x: 0.72, y: 6.43, w: 11.9, h: 0.55 };
const CITATION: Box = { x: 0.72, y: 7.08, w: 11.9, h: 0.2 };

export function boxesFor(layout: SlideLayout): LayoutBoxes {
  const content = { x: 0.72, y: 1.55, w: 11.9, h: 4.55 };
  const base = {
    title: TITLE,
    content,
    takeaway: TAKEAWAY,
    citation: CITATION,
  };
  switch (layout) {
    case "visual_left_text_right":
      return {
        ...base,
        visual: { x: 0.72, y: 1.6, w: 7.15, h: 4.45 },
        text: { x: 8.25, y: 1.72, w: 4.2, h: 4.05 },
      };
    case "text_left_visual_right":
      return {
        ...base,
        text: { x: 0.72, y: 1.72, w: 4.2, h: 4.05 },
        visual: { x: 5.3, y: 1.6, w: 7.32, h: 4.45 },
      };
    case "full_visual":
      return {
        ...base,
        text: { x: 8.9, y: 5.1, w: 3.25, h: 0.7 },
        visual: { x: 0.72, y: 1.48, w: 11.9, h: 4.68 },
      };
    case "equation_focus":
      return {
        ...base,
        visual: { x: 1.25, y: 1.75, w: 10.83, h: 1.85 },
        text: { x: 1.25, y: 3.95, w: 10.83, h: 1.85 },
      };
    case "table_focus":
      return {
        ...base,
        visual: { x: 1.05, y: 1.7, w: 11.23, h: 3.15 },
        text: { x: 1.05, y: 5.05, w: 11.23, h: 0.9 },
      };
    case "comparison":
      return {
        ...base,
        visual: { x: 6.82, y: 1.65, w: 5.8, h: 4.35 },
        text: { x: 0.72, y: 1.65, w: 5.65, h: 4.35 },
      };
    case "process":
      return {
        ...base,
        visual: { x: 0.9, y: 2.0, w: 11.53, h: 2.8 },
        text: { x: 1.25, y: 4.95, w: 10.83, h: 1.05 },
      };
    case "minimal_text":
    default:
      return {
        ...base,
        visual: { x: 0.72, y: 1.65, w: 11.9, h: 2.0 },
        text: { x: 1.3, y: 2.0, w: 10.75, h: 3.55 },
      };
  }
}
