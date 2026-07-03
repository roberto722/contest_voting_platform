import { useLayoutEffect, useRef, useState } from "react";
import { buildLineCandidates, chooseAutoFitMode, findBestFontSize } from "./autoFitTextLogic";

type AutoFitTextProps = {
  text: string;
  className?: string;
  title?: string;
};

export function AutoFitText({ text, className = "", title }: AutoFitTextProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const textRef = useRef<HTMLElement | null>(null);
  const [fontSize, setFontSize] = useState(80);
  const [singleLine, setSingleLine] = useState(true);
  const [lines, setLines] = useState<string[]>([text]);

  useLayoutEffect(() => {
    const wrapper = wrapperRef.current;
    const el = textRef.current;

    if (!wrapper || !el) return undefined;

    const fit = () => {
      const wrapperWidth = wrapper.clientWidth;
      const wrapperHeight = wrapper.clientHeight;

      if (!wrapperWidth || !wrapperHeight) return;

      const minFont = 14;
      const maxFont = 140;

      const testFit = (size: number, candidateLines: string[], nowrap: boolean) => {
        el.textContent = candidateLines.join("\n");
        el.style.fontSize = `${size}px`;
        el.style.whiteSpace = nowrap ? "nowrap" : "pre-line";

        return el.scrollWidth <= wrapperWidth + 1 && el.scrollHeight <= wrapperHeight + 1;
      };

      const multilineCandidates = buildLineCandidates(text);
      const bestMultiline = multilineCandidates.reduce(
        (best, candidateLines) => {
          const candidateSize = findBestFontSize(minFont, maxFont, (size) =>
            testFit(size, candidateLines, false),
          );

          return candidateSize > best.fontSize
            ? { fontSize: candidateSize, lines: candidateLines }
            : best;
        },
        { fontSize: minFont, lines: [text] },
      );

      const next = chooseAutoFitMode({
        minFont,
        maxFont,
        wrapperHeight,
        hasMultilineCandidate: multilineCandidates.length > 0,
        fitsSingleLine: (size) => testFit(size, [text], true),
        fitsMultiLine: (size) => size <= bestMultiline.fontSize,
      });

      el.textContent = (next.singleLine ? [text] : bestMultiline.lines).join("\n");
      el.style.fontSize = `${next.fontSize}px`;
      el.style.whiteSpace = next.singleLine ? "nowrap" : "pre-line";
      setSingleLine(next.singleLine);
      setFontSize(next.fontSize);
      setLines(next.singleLine ? [text] : bestMultiline.lines);
    };

    fit();

    const resizeObserver = new ResizeObserver(fit);
    resizeObserver.observe(wrapper);
    window.addEventListener("resize", fit);
    let cancelled = false;
    void document.fonts?.ready.then(() => {
      if (!cancelled) fit();
    });

    return () => {
      cancelled = true;
      resizeObserver.disconnect();
      window.removeEventListener("resize", fit);
    };
  }, [text]);

  return (
    <div className="auto-fit-text-wrapper" ref={wrapperRef}>
      <strong
        ref={textRef}
        className={className}
        title={title || text}
        style={{
          fontSize: `${fontSize}px`,
          whiteSpace: singleLine ? "nowrap" : "pre-line",
        }}
      >
        {lines.join("\n")}
      </strong>
    </div>
  );
}

export default AutoFitText;
