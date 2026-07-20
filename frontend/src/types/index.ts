export type RepoStatus = "pending"|"cloning"|"parsing"|"building_graph"|"embedding"|"analyzing"|"ready"|"failed";

export interface Repository {
  id: string; url: string; owner: string; name: string;
  status: RepoStatus; progress: number;
  error_message: string | null;
  total_files: number; total_lines: number;
  created_at: string; updated_at: string;
}

export interface CodeElement {
  id: string; element_type: string; name: string;
  qualified_name: string; file_path: string;
  language: string; start_line: number; end_line: number;
  is_dead_code: boolean;
}

export interface ArchitectureResult {
  pattern: string;
  layers: Record<string, string[]>;
  microservices_detected: string[];
  confidence: number;
}

export interface DiagramResult {
  dependency_diagram: string;
  architecture_diagram: string;
  code_graph: {
    nodes: { id: string; label: string; type: string; file_path?: string }[];
    edges: { source: string; target: string; type: string }[];
  };
}

export interface DeadCodeFinding {
  qualified_name: string; node_type: string;
  file_path: string | null; start_line: number | null; end_line: number | null;
  reason: string; confidence: "high"|"medium";
}

export interface QASource { file_path: string; qualified_name: string; element_type: string; }
export interface QAResponse { answer: string; sources: QASource[]; }
