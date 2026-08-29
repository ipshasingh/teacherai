// import Mascot from "./Mascot";

// function Badge({ label, color, icon }) {
//   return (
//     <span
//       className="animate-pop-in inline-flex items-center gap-1 rounded-full px-3 py-1.5
//                  font-body text-sm font-semibold text-white shadow-sm"
//       style={{ backgroundColor: color }}
//     >
//       {icon} {label}
//     </span>
//   );
// }

// function Section({ title, count, children, color }) {
//   if (count === 0) return null;
//   return (
//     <div>
//       <h3 className="font-display text-sm mb-2" style={{ color }}>
//         {title} ({count})
//       </h3>
//       <div className="flex flex-wrap gap-2">{children}</div>
//     </div>
//   );
// }

// export default function KnowledgePanel({ summary }) {
//   if (!summary) return null;

//   const {
//     known_concepts = [],
//     uncertain_concepts = [],
//     partially_understood_concepts = [],
//     contradictory_concepts = [],
//     questions_asked_count = 0,
//     turn_count = 0,
//   } = summary;

//   return (
//     <div className="flex flex-col h-full bg-white rounded-3xl border-4 border-grass/40 shadow-lg p-5 overflow-y-auto">
//       <Mascot knownCount={known_concepts.length} mood={known_concepts.length > 0 ? "happy" : "curious"} />

//       <div className="mt-6 space-y-5">
//         <Section title="Things I know" count={known_concepts.length} color="#4CD787">
//           {known_concepts.map((c) => (
//             <Badge key={c} label={c} color="#4CD787" icon="✓" />
//           ))}
//         </Section>

//         <Section title="Still learning" count={partially_understood_concepts.length} color="#4EC5F1">
//           {partially_understood_concepts.map((c) => (
//             <Badge key={c} label={c} color="#4EC5F1" icon="…" />
//           ))}
//         </Section>

//         <Section title="Not sure about" count={uncertain_concepts.length} color="#FFC93C">
//           {uncertain_concepts.map((c) => (
//             <Badge key={c} label={c} color="#FFC93C" icon="?" />
//           ))}
//         </Section>

//         {contradictory_concepts.length > 0 && (
//           <Section title="Mixed up!" count={contradictory_concepts.length} color="#FF6B9D">
//             {contradictory_concepts.map((c) => (
//               <span key={c} className="animate-wiggle inline-block">
//                 <Badge label={c} color="#FF6B9D" icon="⚡" />
//               </span>
//             ))}
//           </Section>
//         )}
//       </div>

//       <div className="mt-auto pt-5 flex justify-between text-center font-display text-grape">
//         <div>
//           <div className="text-2xl">{turn_count}</div>
//           <div className="text-xs text-ink/60 font-body">turns</div>
//         </div>
//         <div>
//           <div className="text-2xl">{questions_asked_count}</div>
//           <div className="text-xs text-ink/60 font-body">questions</div>
//         </div>
//       </div>
//     </div>
//   );
// }

import Mascot from "./Mascot";

function Badge({ label, color, icon }) {
  return (
    <span
            className="animate-pop-in inline-flex items-center gap-1.5 rounded-full px-3.5 py-2
                 font-body text-sm font-semibold shadow-sm"
      style={{
        backgroundColor: color,
        color: "#2B2250",
      }}
    >
      {icon && <span>{icon}</span>}
      {label}
    </span>
  );
}

function Section({ title, count, children, color }) {
  if (count === 0) return null;

  return (
    <div>
      <h3
        className="font-display text-sm mb-2"
        style={{ color }}
      >
        {title} ({count})
      </h3>

      <div className="flex flex-wrap gap-2">
        {children}
      </div>
    </div>
  );
}

export default function KnowledgePanel({ summary }) {
  if (!summary) return null;

  const {
    known_concepts = [],
    uncertain_concepts = [],
    partially_understood_concepts = [],
    contradictory_concepts = [],
    questions_asked_count = 0,
    turn_count = 0,
    total_concepts = 0,
  } = summary;

  return (
    <aside className="flex flex-col h-full px-3 py-4">
      {/* Feyn */}
      <div className="flex justify-center mb-5">
        <Mascot
          knownCount={known_concepts.length}
          learnedCount={total_concepts}
        />
      </div>

      {/* Knowledge state */}
      <div className="space-y-6">
        <Section
          title="Things I know"
          count={known_concepts.length}
          color="#4CD787"
        >
          {known_concepts.map((concept) => (
            <Badge
              key={concept}
              label={concept}
              color="#4CD787"
              icon="✓"
            />
          ))}
        </Section>

        <Section
          title="Still learning"
          count={partially_understood_concepts.length}
          color="#4EC5F1"
        >
          {partially_understood_concepts.map((concept) => (
            <Badge
              key={concept}
              label={concept}
              color="#4EC5F1"
              icon="..."
            />
          ))}
        </Section>

        <Section
          title="Not sure about"
          count={uncertain_concepts.length}
          color="#FFC93C"
        >
          {uncertain_concepts.map((concept) => (
            <Badge
              key={concept}
              label={concept}
              color="#FFC93C"
              icon="?"
            />
          ))}
        </Section>

        {contradictory_concepts.length > 0 && (
          <Section
            title="Mixed up!"
            count={contradictory_concepts.length}
            color="#FF6B9D"
          >
            {contradictory_concepts.map((concept) => (
              <span
                key={concept}
                className="animate-wiggle inline-block"
              >
                <Badge
                  label={concept}
                  color="#FF6B9D"
                  icon="!"
                />
              </span>
            ))}
          </Section>
        )}
      </div>

      {/* Counters */}
      <div className="mt-auto pt-6 flex justify-center gap-12 text-center">
        <div>
          <div className="text-2xl font-display text-grape">
            {turn_count}
          </div>
          <div className="text-xs text-ink/60 font-body">
            turns
          </div>
        </div>

        <div>
          <div className="text-2xl font-display text-grape">
            {questions_asked_count}
          </div>
          <div className="text-xs text-ink/60 font-body">
            questions
          </div>
        </div>
      </div>
    </aside>
  );
}