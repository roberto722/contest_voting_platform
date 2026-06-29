declare module "vanta/dist/vanta.fog.min" {
  import type * as Three from "three";

  type VantaFogOptions = {
    el: HTMLElement;
    THREE: typeof Three;
    mouseControls?: boolean;
    touchControls?: boolean;
    gyroControls?: boolean;
    minHeight?: number;
    minWidth?: number;
    highlightColor?: number;
    midtoneColor?: number;
    lowlightColor?: number;
    baseColor?: number;
    blurFactor?: number;
    speed?: number;
    zoom?: number;
  };

  type VantaEffect = {
    destroy: () => void;
  };

  export default function FOG(options: VantaFogOptions): VantaEffect;
}
