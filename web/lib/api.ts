const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080").replace(/\/$/, "");

export type Document = { real: string; display: string; chunks: number; size_mb: number };
export type Source = { document: string; chunk: number; distance: number; content: string };
export type ReviewSuggestionRequest = { document_name: string; category: string; page: number; from_line: number; to_line: number; selected_text: string; reviewer_note: string };
export type ReviewSuggestion = { issue: string; evidence: string; proposed_comment: string; proposed_resolution: string; confidence: "high" | "medium" | "low"; demo_only: true; requires_human_review: true };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...options, headers: { "Content-Type": "application/json", ...options?.headers } });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || "Something went wrong");
  return response.json();
}

export const getDocuments = () => request<{ documents: Document[] }>("/api/documents");
export const ask = (question: string) => request<{ answer: string; sources: Source[] }>("/api/ask", { method: "POST", body: JSON.stringify({ question }) });
export const analyze = (action: "summary" | "review" | "improvement", document_name: string) => request<{ result: string }>(`/api/document/${action}`, { method: "POST", body: JSON.stringify({ document_name }) });
export const pdfUrl = (documentName: string) => `${API_URL}/api/documents/${encodeURIComponent(documentName)}/pdf`;
export const suggestReviewComment = (payload: ReviewSuggestionRequest) => request<ReviewSuggestion>("/api/review/suggest", { method: "POST", body: JSON.stringify(payload) });
