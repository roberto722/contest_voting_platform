import React, { useEffect, useRef } from "react";

export const GoldDustCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    let w = 0;
    let h = 0;
    interface Particle {
      x: number;
      y: number;
      r: number;
      alpha: number;
      vx: number;
      vy: number;
      twinkle: number;
      warm: boolean;
    }
    interface Flake {
      x: number;
      y: number;
      size: number;
      alpha: number;
      vx: number;
      vy: number;
      angle: number;
      spin: number;
    }

    let particles: Particle[] = [];
    let flakes: Flake[] = [];
    let raf: number | null = null;

    function rand(min: number, max: number) {
      return min + Math.random() * (max - min);
    }

    function resize() {
      if (!canvas || !ctx) return;
      const stage = canvas.parentElement;
      if (!stage) return;

      const rect = stage.getBoundingClientRect();
      w = Math.max(1, Math.floor(rect.width));
      h = Math.max(1, Math.floor(rect.height));

      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      createParticles();
    }

    function createParticles() {
      const dustCount = Math.floor(Math.max(320, w / 4.2));
      const flakeCount = Math.floor(Math.max(64, w / 28));

      particles = Array.from({ length: dustCount }, () => {
        const yBand = Math.random();
        return {
          x: rand(0, w),
          y: yBand < .42 ? rand(0, h * .42) : rand(h * .42, h * .86),
          r: rand(.35, 1.85),
          alpha: rand(.24, .92),
          vx: rand(-.055, .055),
          vy: rand(-.16, -.035),
          twinkle: rand(0, Math.PI * 2),
          warm: Math.random() > .22
        };
      });

      flakes = Array.from({ length: flakeCount }, () => ({
        x: rand(0, w),
        y: rand(-h * .08, h * .48),
        size: rand(2.4, 8.6) * (w / 1920),
        alpha: rand(.38, .96),
        vx: rand(-.18, .18),
        vy: rand(.08, .34),
        angle: rand(0, Math.PI),
        spin: rand(-.012, .012)
      }));
    }

    function drawParticle(c: CanvasRenderingContext2D, p: Particle) {
      p.x += p.vx + Math.sin(p.twinkle) * .025;
      p.y += p.vy;
      p.twinkle += .035;

      if (p.y < -8) {
        p.y = rand(h * .72, h * .95);
        p.x = rand(0, w);
      }
      if (p.x < -8) p.x = w + 8;
      if (p.x > w + 8) p.x = -8;

      const pulse = .68 + Math.sin(p.twinkle) * .36;
      const a = Math.max(.04, p.alpha * pulse);
      const color = p.warm ? "214, 165, 72" : "255, 238, 190";

      c.beginPath();
      c.fillStyle = `rgba(${color}, ${a})`;
      c.shadowBlur = p.r * 7.4;
      c.shadowColor = `rgba(${color}, .32)`;
      c.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      c.fill();
    }

    function drawFlake(c: CanvasRenderingContext2D, f: Flake) {
      f.x += f.vx;
      f.y += f.vy;
      f.angle += f.spin;

      if (f.y > h * .72 || f.x < -20 || f.x > w + 20) {
        f.x = rand(0, w);
        f.y = rand(-h * .18, h * .15);
        f.vx = rand(-.18, .18);
        f.vy = rand(.08, .34);
      }

      const s = f.size;
      c.save();
      c.translate(f.x, f.y);
      c.rotate(f.angle);
      c.fillStyle = `rgba(222, 165, 62, ${f.alpha})`;
      c.shadowBlur = s * 1.7;
      c.shadowColor = "rgba(255, 218, 135, .38)";
      c.fillRect(-s / 2, -s / 2, s, s);
      c.restore();
    }

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, w, h);

      for (const p of particles) drawParticle(ctx, p);
      for (const f of flakes) drawFlake(ctx, f);

      ctx.shadowBlur = 0;
      raf = requestAnimationFrame(draw);
    }

    resize();
    draw();

    window.addEventListener("resize", resize, { passive: true });

    return () => {
      window.removeEventListener("resize", resize);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return <canvas id="goldDust" ref={canvasRef} aria-hidden="true" />;
};
