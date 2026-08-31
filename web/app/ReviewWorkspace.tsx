"use client";

import { useEffect, useRef, useState } from "react";
import { Document as PdfDocument, Page, pdfjs } from "react-pdf";
import {
  Document,
  pdfUrl,
  ReviewSuggestion,
  suggestReviewComment,
} from "../lib/api";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const categories = [
  "Scientific accuracy",
  "Completeness",
  "Uncertainty language",
  "Traceability / citation",
  "Balance and neutrality",
  "Clarity / editorial",
  "Figure or table",
  "General comment",
];

type Draft = {
  id: string;
  documentName: string;
  documentTitle: string;
  category: string;
  fromPage: number;
  fromLine: number;
  toPage: number;
  toLine: number;
  selectedText: string;
  comment: string;
  createdAt: string;
};

type Props = {
  documents: Document[];
  selected: string;
  setSelected: (value: string) => void;
};

const storageKey = "ipcc-review-studio-drafts-v1";

function csvCell(value: string | number) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

export default function ReviewWorkspace({ documents, selected, setSelected }: Props) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const [pages, setPages] = useState(0);
  const [page, setPage] = useState(1);
  const [fromLine, setFromLine] = useState(0);
  const [toLine, setToLine] = useState(0);
  const [selectedText, setSelectedText] = useState("");
  const [category, setCategory] = useState(categories[0]);
  const [reviewerNote, setReviewerNote] = useState("");
  const [comment, setComment] = useState("");
  const [suggestion, setSuggestion] = useState<ReviewSuggestion | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selectedDocument = documents.find((document) => document.real === selected);

  useEffect(() => {
    const stored = window.localStorage.getItem(storageKey);
    if (stored) setDrafts(JSON.parse(stored));
  }, []);

  useEffect(() => {
    setPage(1);
    setSelectedText("");
    setFromLine(0);
    setToLine(0);
    setSuggestion(null);
  }, [selected]);

  const captureSelection = () => {
    const selection = window.getSelection();
    const viewer = viewerRef.current;
    if (!selection || selection.isCollapsed || !viewer) return;
    const range = selection.getRangeAt(0);
    if (!viewer.contains(range.commonAncestorContainer)) return;
    const text = selection.toString().replace(/\s+/g, " ").trim();
    if (!text) return;

    const spans = Array.from(
      viewer.querySelectorAll<HTMLElement>(".react-pdf__Page__textContent span"),
    );
    const elementFor = (node: Node) => {
      const element = node.nodeType === Node.ELEMENT_NODE
        ? node as Element
        : node.parentElement;
      return element?.closest(
        ".react-pdf__Page__textContent span",
      ) as HTMLElement | null;
    };
    const start = elementFor(range.startContainer);
    const end = elementFor(range.endContainer);
    setSelectedText(text);
    setFromLine(start ? spans.indexOf(start) + 1 : 0);
    setToLine(end ? spans.indexOf(end) + 1 : 0);
    setSuggestion(null);
  };

  const generateSuggestion = async () => {
    if (!selected || !selectedText) {
      setError("Select text in the PDF before asking the review agent.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await suggestReviewComment({
        document_name: selected,
        category,
        page,
        from_line: fromLine,
        to_line: toLine,
        selected_text: selectedText,
        reviewer_note: reviewerNote,
      });
      setSuggestion(result);
      setComment(result.proposed_comment);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to draft comment");
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = () => {
    if (!selectedDocument || !comment.trim()) {
      setError("Add a comment before saving the draft.");
      return;
    }
    const draft: Draft = {
      id: crypto.randomUUID(),
      documentName: selectedDocument.real,
      documentTitle: selectedDocument.display,
      category,
      fromPage: page,
      fromLine,
      toPage: page,
      toLine,
      selectedText,
      comment: comment.trim(),
      createdAt: new Date().toISOString(),
    };
    const next = [draft, ...drafts];
    setDrafts(next);
    window.localStorage.setItem(storageKey, JSON.stringify(next));
    setComment("");
    setReviewerNote("");
    setSuggestion(null);
    setError("");
  };

  const removeDraft = (id: string) => {
    const next = drafts.filter((draft) => draft.id !== id);
    setDrafts(next);
    window.localStorage.setItem(storageKey, JSON.stringify(next));
  };

  const exportDrafts = () => {
    const header = [
      "Chapter",
      "Category",
      "From Page",
      "From Line",
      "To Page",
      "To Line",
      "Text selected",
      "My Comment",
    ];
    const rows = drafts.map((draft) => [
      draft.documentTitle,
      draft.category,
      draft.fromPage,
      draft.fromLine,
      draft.toPage,
      draft.toLine,
      draft.selectedText,
      draft.comment,
    ]);
    const csv = [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "review-studio-comments.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="review-studio">
      <div className="review-banner">
        <div><strong>Hackathon prototype</strong><span>Gemini suggestions require human review</span></div>
        <p>No portal credentials are stored. Nothing is submitted automatically.</p>
      </div>

      <div className="review-toolbar">
        <label>
          Review document
          <select value={selected} onChange={(event) => setSelected(event.target.value)}>
            {documents.map((document) => (
              <option key={document.real} value={document.real}>{document.display}</option>
            ))}
          </select>
        </label>
        <div className="review-progress"><strong>{drafts.length}</strong><span>draft comments</span></div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="review-grid">
        <div className="pdf-panel">
          <div className="panel-heading">
            <div><span className="section-kicker">SOURCE DOCUMENT</span><strong>{selectedDocument?.display || "Choose a document"}</strong></div>
            <div className="page-controls">
              <button disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>←</button>
              <span>Page <input min={1} max={pages || 1} type="number" value={page} onChange={(event) => setPage(Math.max(1, Math.min(pages || 1, Number(event.target.value))))} /> of {pages || "—"}</span>
              <button disabled={!pages || page >= pages} onClick={() => setPage((value) => value + 1)}>→</button>
            </div>
          </div>
          <div className="selection-tip">Highlight text on the page. Page and approximate line positions will be captured.</div>
          <div className="pdf-canvas" ref={viewerRef} onMouseUp={captureSelection}>
            {selected && (
              <PdfDocument
                file={pdfUrl(selected)}
                loading={<div className="pdf-loading">Loading confidential source…</div>}
                onLoadSuccess={({ numPages }) => setPages(numPages)}
                onLoadError={() => setError("Unable to load this PDF.")}
              >
                <Page pageNumber={page} width={720} renderAnnotationLayer={false} renderTextLayer />
              </PdfDocument>
            )}
          </div>
        </div>

        <aside className="comment-panel">
          <div className="panel-heading"><div><span className="section-kicker">NEW COMMENT</span><strong>Review selected passage</strong></div><span className="agent-dot">AI</span></div>
          <label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((item) => <option key={item}>{item}</option>)}</select></label>
          <div className="location-grid">
            <label>From page<input type="number" min={1} value={page} onChange={(event) => setPage(Number(event.target.value))} /></label>
            <label>From line<input type="number" min={0} value={fromLine} onChange={(event) => setFromLine(Number(event.target.value))} /></label>
            <label>To page<input type="number" min={1} value={page} readOnly /></label>
            <label>To line<input type="number" min={0} value={toLine} onChange={(event) => setToLine(Number(event.target.value))} /></label>
          </div>
          <label>Text selected<textarea className="selected-passage" value={selectedText} onChange={(event) => setSelectedText(event.target.value)} placeholder="Highlight text in the document or paste a passage here." /></label>
          <label>Reviewer direction <span className="optional">optional</span><textarea value={reviewerNote} onChange={(event) => setReviewerNote(event.target.value)} placeholder="What should the agent examine?" /></label>
          <button className="agent-button" disabled={busy || !selectedText} onClick={generateSuggestion}>{busy ? "Reviewing evidence…" : "✦ Draft evidence-grounded comment"}</button>

          {suggestion && <div className="suggestion-card"><div><span>Issue</span><p>{suggestion.issue}</p></div><div><span>Evidence</span><p>{suggestion.evidence}</p></div><div><span>Proposed resolution</span><p>{suggestion.proposed_resolution}</p></div><small>Confidence: {suggestion.confidence} · Demo only</small></div>}

          <label>My comment<textarea className="comment-text" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Edit the agent suggestion or write your own comment." /></label>
          <div className="comment-actions"><button className="secondary" onClick={() => navigator.clipboard.writeText(comment)} disabled={!comment}>Copy</button><button className="primary" onClick={saveDraft} disabled={!comment}>Save draft</button></div>
        </aside>
      </div>

      <section className="draft-queue">
        <div className="section-heading"><div><span className="section-kicker">REVIEW QUEUE</span><h3>Human-approved draft comments</h3></div><div className="queue-actions"><button className="secondary" disabled={!drafts.length} onClick={exportDrafts}>Export CSV</button><a className="portal-link" href="https://apps.ipcc.ch/comments/ar7wg1/" target="_blank" rel="noreferrer">Open official portal ↗</a></div></div>
        {!drafts.length && <div className="empty-queue">Saved drafts remain in this browser until you export or remove them.</div>}
        {drafts.map((draft) => <article className="draft-card" key={draft.id}><div className="draft-location"><strong>{draft.documentTitle}</strong><span>p. {draft.fromPage}, lines {draft.fromLine || "—"}–{draft.toLine || "—"}</span></div><span className="draft-category">{draft.category}</span><blockquote>{draft.comment}</blockquote><details><summary>Selected text</summary><p>{draft.selectedText}</p></details><div className="draft-actions"><button onClick={() => navigator.clipboard.writeText(draft.comment)}>Copy comment</button><button className="danger-link" onClick={() => removeDraft(draft.id)}>Remove</button></div></article>)}
      </section>
    </section>
  );
}
