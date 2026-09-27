export type PresentationMode = "paper-reading" | "own-research";
export type LanguageProfile = "zh_cn_bilingual_terms";
export type ThemeName = "conference-minimal" | "group-meeting";
export type SlideLayout =
  | "minimal_text"
  | "visual_left_text_right"
  | "text_left_visual_right"
  | "full_visual"
  | "comparison"
  | "equation_focus"
  | "table_focus"
  | "process";

export type VisualKind =
  | "source_asset"
  | "source_table"
  | "source_equation"
  | "conceptual_diagram";

export interface SpeakerNotes {
  purpose: string;
  main_message: string;
  script: string;
  visual_guidance: string;
  transition: string;
  estimated_seconds: number;
}

export interface SlideCitation {
  evidence_id: string;
  source_ids: string[];
  display_text: string;
}

export interface SlideVisual {
  visual_id: string;
  kind: VisualKind;
  source_ref: string;
  role: "primary" | "supporting" | "background";
  treatment: "original" | "crop" | "zoom" | "highlight" | "native_table" | "equation" | "diagram";
  caption: string | null;
  annotations: string[];
  table_column_labels: string[] | null;
}

export interface SlideSpecSlide {
  slide_id: string;
  unit_id: string;
  order: number;
  section: string;
  purpose: string;
  question: string;
  title: string;
  title_kind: "topic" | "claim";
  technical_title: string | null;
  main_claim: string;
  body: string[];
  visuals: SlideVisual[];
  annotations: string[];
  takeaway: string;
  evidence_ids: string[];
  citations: SlideCitation[];
  layout: SlideLayout;
  speaker_notes: SpeakerNotes;
}

export interface SlideSpec {
  schema_version: "1.1";
  paper_id: string;
  mode: PresentationMode;
  theme: ThemeName;
  language: "zh-CN";
  language_profile: LanguageProfile;
  presentation: {
    language: "zh-CN";
    terminology_mode: "bilingual";
    preserve_source_visual_language: true;
    translate_generic_labels: true;
    translate_speaker_notes: true;
  };
  title: string;
  slides: SlideSpecSlide[];
  estimated_total_seconds: number;
  provenance: {
    provider: string;
    model: string;
    prompt_version: string;
    input_fingerprint: string;
  };
}

export interface VisualAsset {
  asset_id: string;
  type: string;
  output_path: string;
  caption: string | null;
  media_type: string;
}

export interface VisualManifest {
  paper_id: string;
  assets: VisualAsset[];
}

export interface PaperTable {
  table_id: string;
  number: string | null;
  caption: string | null;
  latex: string;
}

export interface PaperEquation {
  equation_id: string;
  number: string | null;
  latex: string;
}

export interface PaperStructure {
  paper_id: string;
  tables: PaperTable[];
  equations: PaperEquation[];
}

export interface ThemeTokens {
  name: ThemeName;
  fontFamily: string;
  fontFallbacks: string[];
  equationFontFamily: string;
  background: string;
  surface: string;
  text: string;
  muted: string;
  accent: string;
  accentSoft: string;
  secondary: string;
  warning: string;
  titleSize: number;
  technicalTitleSize: number;
  bodySize: number;
  takeawaySize: number;
  citationSize: number;
  lineWidth: number;
}

export interface RenderInputs {
  workspace: string;
  spec: SlideSpec;
  visuals: VisualManifest;
  paper: PaperStructure;
  theme: ThemeTokens;
}

export interface RenderSelection {
  slideNumbers?: number[];
}

export interface RenderResult {
  outputPath: string;
  renderedSlideIds: string[];
  theme: ThemeName;
  sourceSpecPath: string;
}
