import { getPercentage, getEmojiIndex } from "./emojiHelper";

interface EmojiSliderProps {
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
}

const FLUENT_EMOJIS_3D = [
  // 0: Seedling 🌱
  "https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Seedling/3D/seedling_3d.png",
  // 1: Sparkles ✨
  "https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Sparkles/3D/sparkles_3d.png",
  // 2: Star ⭐
  "https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Star/3D/star_3d.png",
  // 3: Fire 🔥
  "https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Fire/3D/fire_3d.png",
  // 4: Trophy 🏆
  "https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@main/assets/Trophy/3D/trophy_3d.png"
];

export default function EmojiSlider({ min, max, value, onChange }: EmojiSliderProps) {
  const percentage = getPercentage(value, min, max);
  const emojiIdx = getEmojiIndex(percentage);
  const emojiUrl = FLUENT_EMOJIS_3D[emojiIdx];
  const pctString = `${percentage * 100}%`;

  const borderRadius = percentage > 0.5 ? "1.25em" : "0";

  return (
    <div className="judge-emoji-slider">
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="slider-outer" aria-hidden="true">
        <div
          className="slider-inner"
          style={{
            width: pctString,
            borderRadius: `var(--slider-roundness) ${borderRadius} ${borderRadius} var(--slider-roundness)`
          }}
        />
        <div
          className="emoji-thumb-container"
          style={{
            left: pctString,
            transform: `translate(-${pctString}, -50%)`
          }}
        >
          <div className="emoji-thumb">
            <img src={emojiUrl} alt="" />
          </div>
        </div>
      </div>
    </div>
  );
}
