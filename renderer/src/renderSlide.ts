import { addBodyText } from "./components/body.js";
import { addSlideChrome, addSpeakerNotes } from "./components/chrome.js";
import { addConceptualDiagram, addVisuals } from "./components/visuals.js";
import { boxesFor } from "./layouts/index.js";
import type { SlideLike } from "./pptx.js";
import type { RenderInputs, SlideSpecSlide } from "./types.js";

export function renderSlide(
  slide: SlideLike,
  specSlide: SlideSpecSlide,
  inputs: RenderInputs,
  displayNumber: number,
): void {
  const boxes = boxesFor(specSlide.layout);
  addSlideChrome(
    slide,
    specSlide,
    inputs.theme,
    boxes.title,
    boxes.takeaway,
    boxes.citation,
    displayNumber,
  );

  if (specSlide.layout === "minimal_text") {
    addBodyText(slide, specSlide, inputs.theme, boxes.text, true);
  } else if (specSlide.layout === "process" && specSlide.visuals.length === 0) {
    addConceptualDiagram(slide, specSlide, inputs.theme, boxes.visual);
    addBodyText(slide, specSlide, inputs.theme, boxes.text);
  } else {
    addVisuals(slide, specSlide, inputs, boxes.visual);
    if (specSlide.layout !== "table_focus") {
      addBodyText(slide, specSlide, inputs.theme, boxes.text);
    }
  }

  addSpeakerNotes(slide, specSlide);
}
