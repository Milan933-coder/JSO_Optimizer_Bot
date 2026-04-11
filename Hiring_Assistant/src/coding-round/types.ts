export interface CodingLanguage {
  slug: string;
  label: string;
  judge0_language_id: number;
  starter_code: string;
}

export interface CodingSample {
  index: number;
  title: string;
  input: string;
  output: string;
}

export interface CodingSampleResult {
  sample_index: number;
  input: string;
  expected_output: string;
  actual_output: string;
  passed: boolean;
  judge0_status: string;
  judge0_status_id?: number | null;
  stdout?: string | null;
  stderr?: string | null;
  compile_output?: string | null;
  message?: string | null;
  time?: string | null;
  memory?: number | null;
}

export interface CodingAttemptResult {
  mode: "run" | "submit";
  passed: boolean;
  verdict: string;
  status_summary: string;
  passed_samples: number;
  total_samples: number;
  sample_results: CodingSampleResult[];
}

export interface CodingProblem {
  source: string;
  source_url: string;
  mirror_url: string;
  title: string;
  codeforces_id: string;
  contest_id: number;
  index: string;
  rating: number;
  solved_count?: number | null;
  tags: string[];
  statement: string;
  input_spec: string;
  output_spec: string;
  notes?: string | null;
  time_limit: string;
  memory_limit: string;
  samples: CodingSample[];
  available_languages: CodingLanguage[];
}

export interface CodingRoundState {
  status: string;
  is_active: boolean;
  is_completed: boolean;
  time_limit_minutes: number;
  max_attempts: number;
  attempts_used: number;
  attempts_left: number;
  remaining_seconds: number;
  started_at?: string | null;
  expires_at?: string | null;
  completion_reason?: string | null;
  problem: CodingProblem;
  last_result?: CodingAttemptResult | null;
}

export interface CodingRoundActionResponse {
  session_id: string;
  action: "run" | "submit";
  phase: string;
  is_closed: boolean;
  reply?: string | null;
  coding_round?: CodingRoundState | null;
  result: CodingAttemptResult;
}
