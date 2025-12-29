/**
 * TypeScript type definitions matching backend data models
 */

export type SlideType = 'title' | 'content' | 'section_header' | 'conclusion' | 'diagram_heavy';

export interface ImageContent {
  image_id: string;
  format: string;
  extracted_from_slide: number;
  vision_description?: string;
}

export interface SlideContent {
  slide_index: number;
  slide_type: SlideType;
  title?: string;
  bullet_points: string[];
  body_text: string;
  images: ImageContent[];
  notes?: string;
  raw_markdown: string;
}

export interface Section {
  title: string;
  start_slide: number;
  end_slide: number;
  summary: string;
}

export interface GlobalContextPlan {
  lecture_title: string;
  total_slides: number;
  sections: Section[];
  topic_progression: string[];
  learning_objectives: string[];
  terminology: Record<string, string>;
  prerequisites: string[];
  cross_references: Record<number, number[]>;
  instructional_style: string;
  audience_level: string;
  key_diagrams: Array<{
    slide_idx: number;
    description: string;
    purpose: string;
  }>;
  created_at: string;
  total_tokens_analyzed: number;
}

export interface NarrationSegment {
  slide_index: number;
  narration_text: string;
  estimated_duration_seconds: number;
  references_previous_slides: number[];
  introduces_concepts: string[];
  prepares_for_next?: string;
  tokens_used: number;
  generation_timestamp: string;
}

export type SessionStatus =
  | 'uploading'
  | 'parsing'
  | 'analyzing'
  | 'generating'
  | 'complete'
  | 'error';

export interface LectureSession {
  session_id: string;
  created_at: string;
  expires_at: string;
  status: SessionStatus;
  current_phase: 1 | 2 | 3;
  progress_percentage: number;
  original_filename: string;
  file_format: string;
  slides: SlideContent[];
  global_plan?: GlobalContextPlan;
  narrations: Record<number, NarrationSegment>;
  errors: string[];
  warnings: string[];
}

export interface UploadResponse {
  session_id: string;
}
