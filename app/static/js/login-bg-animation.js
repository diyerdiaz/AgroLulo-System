/**
 * Animación de Fondo Futuristia para AgroLulo Login & Dashboard
 * - Partículas flotando lentamente adaptables al tema de color (Verde, Azul, Naranja)
 * - Puntos de luz parpadeantes (twinkle)
 * - Líneas digitales flotantes estilo rejilla agrícola
 */
let currentThemeColor = { r: 57, g: 255, b: 20 };

window.updateCanvasTheme = function(themeName) {
  if (themeName === 'blue') {
    currentThemeColor = { r: 0, g: 240, b: 255 };
  } else if (themeName === 'orange') {
    currentThemeColor = { r: 255, g: 136, b: 0 };
  } else {
    currentThemeColor = { r: 57, g: 255, b: 20 };
  }
};

// Cargar preferencia inicial si está almacenada en localStorage
const savedTheme = localStorage.getItem('agrolulo_theme');
if (savedTheme) {
  window.updateCanvasTheme(savedTheme);
}

document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('bgCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  const particleCount = 45;
  const particles = [];

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 2.5 + 0.8,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3 - 0.15,
      pulseSpeed: Math.random() * 0.02 + 0.005,
      pulseFactor: Math.random() * Math.PI,
    });
  }

  const starCount = 30;
  const stars = [];

  for (let i = 0; i < starCount; i++) {
    stars.push({
      x: Math.random() * width,
      y: Math.random() * height,
      size: Math.random() * 1.5 + 0.5,
      alpha: Math.random(),
      speed: Math.random() * 0.015 + 0.005,
      increasing: Math.random() > 0.5,
    });
  }

  let scanLineY = 0;
  const scanSpeed = 0.4;

  function animate() {
    ctx.clearRect(0, 0, width, height);

    const { r, g, b } = currentThemeColor;

    // 1. Dibujar Rejilla Digital Suave
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.035)`;
    ctx.lineWidth = 1;
    const gridSize = 60;

    ctx.beginPath();
    for (let x = 0; x < width; x += gridSize) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
    }
    for (let y = 0; y < height; y += gridSize) {
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
    }
    ctx.stroke();

    // 2. Línea Digital con Desplazamiento Suave
    scanLineY += scanSpeed;
    if (scanLineY > height) scanLineY = 0;

    const scanGrad = ctx.createLinearGradient(0, scanLineY - 20, 0, scanLineY + 20);
    scanGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0)`);
    scanGrad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.1)`);
    scanGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);

    ctx.fillStyle = scanGrad;
    ctx.fillRect(0, scanLineY - 20, width, 40);

    // 3. Dibujar y Actualizar Puntos Parpadeantes (Twinkle Lights)
    stars.forEach((star) => {
      if (star.increasing) {
        star.alpha += star.speed;
        if (star.alpha >= 0.8) star.increasing = false;
      } else {
        star.alpha -= star.speed;
        if (star.alpha <= 0.05) star.increasing = true;
      }

      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${star.alpha * 0.7})`;
      ctx.shadowBlur = 8;
      ctx.shadowColor = `rgba(${r}, ${g}, ${b}, 0.8)`;
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
      ctx.fill();
    });

    // 4. Dibujar y Actualizar Partículas Flotantes
    particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0) p.x = width;
      if (p.x > width) p.x = 0;
      if (p.y < 0) p.y = height;
      if (p.y > height) p.y = 0;

      p.pulseFactor += p.pulseSpeed;
      const currentAlpha = 0.2 + (Math.sin(p.pulseFactor) + 1) * 0.25;

      ctx.shadowBlur = 12;
      ctx.shadowColor = `rgba(${r}, ${g}, ${b}, 0.9)`;
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${currentAlpha})`;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.shadowBlur = 0;

    requestAnimationFrame(animate);
  }

  animate();
});
