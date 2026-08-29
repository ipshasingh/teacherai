import React from "react";
import { jsPDF } from "jspdf";

function generateStudySheetPDF(summary) {
  const {
    topic,
    known_concepts = [],
    partially_understood_concepts = [],
    uncertain_concepts = [],
    contradictory_concepts = [],
    corrected_concepts = [],
    learned_relationships = [],
    turn_count = 0,
    questions_asked_count = 0,
    total_concepts = 0,
    total_relationships = 0,
    unresolved_contradiction_count = 0,
  } = summary;

  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 48;
  const maxWidth = pageWidth - margin * 2;
  let y = margin;

  const INK = [43, 34, 80];
  const GRAPE = [140, 111, 230];
  const MUTED = [130, 122, 145];
  const COLORS = {
    known: [76, 215, 135],
    partial: [78, 197, 241],
    uncertain: [200, 150, 20],
    corrected: [140, 111, 230],
    contradictory: [220, 70, 120],
  };

  function ensureSpace(lineHeight) {
    if (y + lineHeight > pageHeight - margin) {
      doc.addPage();
      y = margin;
    }
  }

  function addTitle(text, size, color, spacingAfter = 10) {
    ensureSpace(size + spacingAfter);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(size);
    doc.setTextColor(...color);
    doc.text(text, margin, y);
    y += size + spacingAfter;
  }

  function addBody(text, size, color, spacingAfter) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(size);
    doc.setTextColor(...color);
    doc.splitTextToSize(text, maxWidth).forEach((line) => {
      ensureSpace(size + 4);
      doc.text(line, margin, y);
      y += size + 4;
    });
    y += spacingAfter;
  }

  function addSection(title, items, color) {
    if (!items || items.length === 0) return;
    addTitle(title, 14, color, 8);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    doc.setTextColor(...INK);
    items.forEach((item) => {
      doc.splitTextToSize(`-  ${item}`, maxWidth - 10).forEach((line, i) => {
        ensureSpace(16);
        doc.text(line, margin + (i === 0 ? 0 : 14), y);
        y += 16;
      });
    });
    y += 8;
  }

  addTitle("Feyn AI \u2014 Teaching Report", 22, GRAPE, 4);
  addBody(`What you taught Feyn about: ${topic}`, 12, INK, 2);
  addBody(`Generated: ${new Date().toLocaleString()}`, 9, MUTED, 10);

  doc.setDrawColor(230, 220, 200);
  doc.line(margin, y, pageWidth - margin, y);
  y += 16;

  addBody(
    `${total_concepts} concepts  |  ${total_relationships} connections  |  ${turn_count} teaching turns  |  ${questions_asked_count} questions asked`,
    10,
    MUTED,
    14
  );

  addSection("What you taught clearly", known_concepts, COLORS.known);
  addSection("What needs more detail", partially_understood_concepts, COLORS.partial);
  addSection("What confused Feyn", uncertain_concepts, COLORS.uncertain);
  addSection("Where you corrected yourself", corrected_concepts, COLORS.corrected);
  addSection("What you should clarify next", contradictory_concepts, COLORS.contradictory);

  if (learned_relationships.length > 0) {
    addTitle("Connections you made successfully", 14, GRAPE, 8);
    learned_relationships.forEach((r) => {
      const desc = r.description ? ` \u2014 ${r.description}` : "";
      addBody(`${r.source_concept}  (${r.relation_type})  ${r.target_concept}${desc}`, 11, INK, 4);
    });
    y += 6;
  }

  if (unresolved_contradiction_count > 0) {
    addBody(
      `Focus on this before your next session: ${unresolved_contradiction_count} thing${
        unresolved_contradiction_count !== 1 ? "s" : ""
      } you explained two different ways. Revisit ${
        unresolved_contradiction_count !== 1 ? "them" : "it"
      } to lock in the right version.`,
      10,
      COLORS.contradictory,
      10
    );
  }

  ensureSpace(30);
  doc.setDrawColor(230, 220, 200);
  doc.line(margin, y, pageWidth - margin, y);
  y += 14;
  addBody(
    "This isn't an answer key \u2014 it's a reflection of how clearly you explained this topic.",
    9,
    MUTED,
    0
  );

  return doc;
}

function downloadStudySheet(summary) {
  const doc = generateStudySheetPDF(summary);
  const safeTopic = (summary.topic || "session").replace(/[^a-z0-9]+/gi, "-").toLowerCase();
  doc.save(`feyn-study-sheet-${safeTopic}.pdf`);
}

function ConceptSection({ title, concepts, icon, className = "" })  {
  if (!concepts || concepts.length === 0) return null;

  return (
    <section className={`summary-card ${className}`}>
      <div className="summary-card-header">
        <span className="summary-icon">{icon}</span>
        <h3>{title}</h3>
      </div>

      <div className="concept-list">
        {concepts.map((concept) => (
          <span key={concept} className="concept-chip">
            {concept}
          </span>
        ))}
      </div>
    </section>
  );
}

export default function SessionSummary({ summary, onDone }) {
  if (!summary) return null;

  const {
    topic,
    known_concepts = [],
    partially_understood_concepts = [],
    uncertain_concepts = [],
    contradictory_concepts = [],
    corrected_concepts = [],
    learned_relationships = [],
    turn_count = 0,
    questions_asked_count = 0,
    total_concepts = 0,
    total_relationships = 0,
    unresolved_contradiction_count = 0,
  } = summary;

  return (
    <div className="session-summary">
      <div className="summary-hero">
        <div className="summary-celebration">✨</div>

        <p className="summary-eyebrow">SESSION COMPLETE</p>

        <h1>Your teaching report</h1>

        <p className="summary-topic">
          Here's how clearly you explained{" "}
          <strong>{topic}</strong>
        </p>
      </div>

      <div className="summary-stats">
        <div className="stat">
          <strong>{total_concepts}</strong>
          <span>concepts</span>
        </div>

        <div className="stat">
          <strong>{total_relationships}</strong>
          <span>connections</span>
        </div>

        <div className="stat">
          <strong>{turn_count}</strong>
          <span>teaching turns</span>
        </div>

        <div className="stat">
          <strong>{questions_asked_count}</strong>
          <span>questions</span>
        </div>
      </div>

      <div className="summary-grid">
        <ConceptSection
          title="What you taught clearly"
          icon="✓"
          concepts={known_concepts}
          className="known"
        />

        <ConceptSection
          title="What needs more detail"
          icon="🧩"
          concepts={partially_understood_concepts}
          className="partial"
        />

        <ConceptSection
          title="What confused Feyn"
          icon="?"
          concepts={uncertain_concepts}
          className="uncertain"
        />

        <ConceptSection
          title="Where you corrected yourself"
          icon="🔄"
          concepts={corrected_concepts}
          className="corrected"
        />

        <ConceptSection
          title="What you should clarify next"
          icon="⚡"
          concepts={contradictory_concepts}
          className="contradictory"
        />
      </div>

      {learned_relationships.length > 0 && (
        <section className="relationships-card">
          <div className="summary-card-header">
            <span className="summary-icon">🔗</span>
            <h3>Connections you made successfully</h3>
          </div>

          <div className="relationship-list">
            {learned_relationships.map((relationship, index) => (
              <div
                key={`${relationship.source_concept}-${relationship.target_concept}-${index}`}
                className="relationship"
              >
                <span className="relationship-node">
                  {relationship.source_concept}
                </span>

                <span className="relationship-arrow">
                  {relationship.relation_type}
                </span>

                <span className="relationship-node">
                  {relationship.target_concept}
                </span>

                {relationship.description && (
                  <p>{relationship.description}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {unresolved_contradiction_count > 0 && (
        <div className="summary-notice">
          <span>💭</span>
                    <p>
            You explained{" "}
            <strong>{unresolved_contradiction_count}</strong>{" "}
            thing{unresolved_contradiction_count !== 1 ? "s" : ""} two different
            ways. Revisit {unresolved_contradiction_count !== 1 ? "them" : "it"} to
            lock in the right version before your next session.
          </p>
        </div>
      )}

      <div className="summary-footer">
                <p>
          This isn't an answer key.
          <br />
          It's a reflection of how clearly you explained this topic.
        </p>

                <div className="summary-actions">
          <button
            onClick={() => downloadStudySheet(summary)}
            className="summary-download-button"
          >
            Download study sheet
          </button>
          <button onClick={onDone} className="summary-done-button">
            Done
          </button>
        </div>
      </div>
    </div>
  );
}