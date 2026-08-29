// const SPOT_COLORS = ["#FF6B9D", "#4EC5F1", "#4CD787", "#8C6FE6", "#FFC93C"];

// const SPOT_POSITIONS = [
//   { cx: 70, cy: 55 },
//   { cx: 110, cy: 65 },
//   { cx: 55, cy: 90 },
//   { cx: 130, cy: 95 },
//   { cx: 90, cy: 110 },
//   { cx: 40, cy: 60 },
//   { cx: 150, cy: 70 },
//   { cx: 75, cy: 130 },
//   { cx: 115, cy: 125 },
//   { cx: 100, cy: 40 },
// ];

// export default function Mascot({ knownCount = 0, mood = "curious" }) {
//   const spots = SPOT_POSITIONS.slice(0, Math.min(knownCount, SPOT_POSITIONS.length));

//   return (
//     <div className="flex flex-col items-center">
//       <svg viewBox="0 0 190 190" className="w-32 h-32 drop-shadow-lg">
//         <ellipse cx="95" cy="100" rx="80" ry="75" fill="#F4F1FF" stroke="#8C6FE6" strokeWidth="5" />

//         {spots.map((pos, i) => (
//           <circle
//             key={i}
//             cx={pos.cx}
//             cy={pos.cy}
//             r="11"
//             fill={SPOT_COLORS[i % SPOT_COLORS.length]}
//             className="animate-pop-in"
//           />
//         ))}

//         <circle cx="70" cy="90" r="7" fill="#2B2250" />
//         <circle cx="120" cy="90" r="7" fill="#2B2250" />
//         <circle cx="72" cy="88" r="2" fill="white" />
//         <circle cx="122" cy="88" r="2" fill="white" />

//         {mood === "happy" ? (
//           <path
//             d="M 75 115 Q 95 132 115 115"
//             stroke="#2B2250"
//             strokeWidth="5"
//             fill="none"
//             strokeLinecap="round"
//           />
//         ) : (
//           <ellipse cx="95" cy="118" rx="8" ry="6" fill="#2B2250" />
//         )}
//       </svg>
//       <p className="font-display text-ink text-sm mt-1 text-center">
//         {knownCount === 0
//           ? "I don't know anything yet!"
//           : `I know ${knownCount} thing${knownCount === 1 ? "" : "s"}!`}
//       </p>
//     </div>
//   );
// }


import { useEffect, useRef, useState } from "react";

const SPOT_COLORS = [
  "#FF6B9D",
  "#4EC5F1",
  "#4CD787",
  "#8C6FE6",
  "#FFC93C",
];

const SPOT_POSITIONS = [
  { cx: 67, cy: 57 },
  { cx: 112, cy: 64 },
  { cx: 55, cy: 91 },
  { cx: 130, cy: 94 },
  { cx: 88, cy: 112 },
  { cx: 42, cy: 67 },
  { cx: 145, cy: 73 },
  { cx: 69, cy: 128 },
  { cx: 117, cy: 126 },
  { cx: 98, cy: 42 },
];

const POP_BUBBLES = [
  { cx: 28, cy: 45, color: "#FF6B9D", delay: "0ms" },
  { cx: 165, cy: 48, color: "#4EC5F1", delay: "70ms" },
  { cx: 42, cy: 20, color: "#FFC93C", delay: "130ms" },
  { cx: 148, cy: 20, color: "#4CD787", delay: "190ms" },
  { cx: 18, cy: 100, color: "#8C6FE6", delay: "250ms" },
  { cx: 172, cy: 103, color: "#FF6B9D", delay: "310ms" },
  { cx: 48, cy: 151, color: "#4EC5F1", delay: "370ms" },
  { cx: 145, cy: 151, color: "#FFC93C", delay: "430ms" },
];

export default function Mascot({
  knownCount = 0,
  learnedCount = 0,
}) {
  const [smiling, setSmiling] = useState(false);
  const [popping, setPopping] = useState(false);

  const previousLearnedCount = useRef(learnedCount);

  useEffect(() => {
    if (learnedCount > previousLearnedCount.current) {
      setSmiling(true);
      setPopping(true);

      const smileTimer = setTimeout(() => {
        setSmiling(false);
      }, 1100);

      const popTimer = setTimeout(() => {
        setPopping(false);
      }, 850);

      previousLearnedCount.current = learnedCount;

      return () => {
        clearTimeout(smileTimer);
        clearTimeout(popTimer);
      };
    }

    previousLearnedCount.current = learnedCount;
  }, [learnedCount]);

  const spots = SPOT_POSITIONS.slice(
    0,
    Math.min(knownCount, SPOT_POSITIONS.length)
  );

  return (
    <div className="flex flex-col items-center select-none">
      <div className="relative w-56 h-56 flex items-center justify-center">
        {/* Celebration bubbles */}
        {popping &&
          POP_BUBBLES.map((bubble, index) => (
            <span
              key={`${learnedCount}-${index}`}
              className="absolute animate-feyn-pop"
              style={{
                left: `${bubble.cx}px`,
                top: `${bubble.cy}px`,
                animationDelay: bubble.delay,
                backgroundColor: bubble.color,
              }}
            />
          ))}

        {/* Feyn */}
        <svg
          viewBox="0 0 190 190"
          className={`relative z-10 w-36 h-36 drop-shadow-md ${
            smiling ? "animate-feyn-happy" : ""
          }`}
          aria-label="Feyn"
          role="img"
        >
          {/* Body */}
          <circle
            cx="95"
            cy="95"
            r="68"
            fill="#FFF8D9"
            stroke="#FFC93C"
            strokeWidth="6"
          />

          {/* Learned concept spots */}
          {spots.map((pos, index) => (
            <circle
              key={index}
              cx={pos.cx}
              cy={pos.cy}
              r="10"
              fill={SPOT_COLORS[index % SPOT_COLORS.length]}
              className="animate-feyn-spot"
            />
          ))}

          {/* Eyes */}
          <circle cx="70" cy="88" r="7" fill="#2B2250" />
          <circle cx="120" cy="88" r="7" fill="#2B2250" />

          <circle cx="72" cy="86" r="2.5" fill="white" />
          <circle cx="122" cy="86" r="2.5" fill="white" />

          {/* Momentary smile */}
          {smiling ? (
            <path
              d="M 70 111 Q 95 139 120 111"
              stroke="#2B2250"
              strokeWidth="6"
              fill="#FF6B9D"
              strokeLinecap="round"
            />
          ) : (
            <path
              d="M 88 116 Q 95 121 102 116"
              stroke="#2B2250"
              strokeWidth="5"
              fill="none"
              strokeLinecap="round"
            />
          )}
        </svg>
      </div>

            <div className="text-center mt-1">
        <p className="font-display text-ink text-base font-bold">
          {smiling
            ? "I learned something new!"
            : knownCount === 0
              ? "I'm ready to learn!"
              : `I'm learning ${knownCount} thing${
                  knownCount === 1 ? "" : "s"
                }!`}
        </p>
      </div>
    </div>
  );
}