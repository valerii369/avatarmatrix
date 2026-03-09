# QUANTUM SHIFT — Оптимизация для мобильных

## Проблема

Canvas 2D с текущей визуализацией генерирует ~15 000 draw calls за кадр на desktop. На мобильных это критично из-за слабого GPU и теплового троттлинга.

Главные убийцы FPS: `shadowBlur` (софтверный blur), массовые `createRadialGradient`, большое количество path operations.

---

## Стратегия: адаптивный рендеринг

### Определение устройства

```typescript
function getPerformanceTier(): 'high' | 'medium' | 'low' {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl');
  const isMobile = /iPhone|iPad|Android/i.test(navigator.userAgent);
  const cores = navigator.hardwareConcurrency || 2;
  const memory = (navigator as any).deviceMemory || 2; // GB
  
  if (!isMobile && cores >= 8) return 'high';
  if (isMobile && cores >= 6 && memory >= 4) return 'medium';
  return isMobile ? 'low' : 'medium';
}
```

### Или автоматически через FPS-мониторинг

```typescript
// Авто-понижение качества если FPS просел
let frameCount = 0;
let lastCheck = performance.now();
let currentTier: 'high' | 'medium' | 'low' = 'high';

function checkFPS(now: number) {
  frameCount++;
  if (now - lastCheck >= 2000) { // проверяем каждые 2 сек
    const fps = frameCount / ((now - lastCheck) / 1000);
    if (fps < 35 && currentTier === 'high') currentTier = 'medium';
    if (fps < 25 && currentTier === 'medium') currentTier = 'low';
    if (fps > 55 && currentTier === 'low') currentTier = 'medium';
    frameCount = 0;
    lastCheck = now;
  }
}
```

---

## Параметры по уровням

| Параметр | Desktop (high) | Планшет (medium) | Телефон (low) |
|----------|---------------|-------------------|---------------|
| Canvas DPR | devicePixelRatio | min(dpr, 2) | min(dpr, 1.5) |
| Фоновые частицы | 120 | 60 | 30 |
| Steps в нити | 60 | 35 | 20 |
| Max нитей на поток | 22 | 12 | 8 |
| shadowBlur | Да | Нет — заменить на glow-линию | Нет |
| Glow layers на сферу | 2–8 | 2–4 | 1–2 |
| Потоки сфера↔сфера | Да (22 thread) | Упрощённые (3–5 линий) | Только 1 линия |
| Орбитальные точки центра | 6–16 | 4–8 | 2–4 |
| Цветок Жизни (круги) | 7 + 6 внешних | 7 только | 1 центральный + 6 |
| Чакра-точки | 7 | 7 | 3 (верх, центр, низ) |
| Core line потока | Да | Да | Нет |
| Flying particles | Да | Нет | Нет |
| Target FPS | 60 | 45+ | 30+ |

---

## Ключевые оптимизации

### 1. Убрать shadowBlur на мобильных (главное!)

shadowBlur — это софтверный gaussian blur, выполняется на CPU. Замена — рисуем ту же линию дважды: толстую полупрозрачную (имитация glow) + тонкую яркую поверх.

```javascript
// БЫЛО (дорого):
ctx.shadowColor = `rgba(${r},${g},${b}, 0.3)`;
ctx.shadowBlur = 12;
ctx.stroke();

// СТАЛО (дёшево, визуально похоже):
// Широкая полупрозрачная "glow" линия
ctx.strokeStyle = `rgba(${r},${g},${b}, 0.06)`;
ctx.lineWidth = threadWidth * 4;
ctx.stroke();
// Основная линия
ctx.strokeStyle = `rgba(${r},${g},${b}, ${alpha})`;
ctx.lineWidth = threadWidth;
ctx.stroke();
```

### 2. Уменьшить steps в нитях

60 steps на desktop, 20 на мобильных. Разница в плавности минимальна при тонких линиях, но экономит 66% path operations.

### 3. Ограничить количество нитей

Даже если активно 22 карты — на мобильном рисуем только top-8 (или top-12) по hawkins_score. Визуально разница мала (всё равно сливается в поток), но нагрузка в 2–3 раза меньше.

```javascript
const maxThreads = tier === 'high' ? 22 : tier === 'medium' ? 12 : 8;
const visibleCards = activeCards
  .sort((a, b) => b.hawkins_score - a.hawkins_score)
  .slice(0, maxThreads);
```

### 4. Снизить DPR

На Retina-экранах мобильных (dpr=3) canvas рисует в 9 раз больше пикселей чем на dpr=1. Ограничиваем до 1.5:

```javascript
const dpr = Math.min(window.devicePixelRatio || 1, tier === 'low' ? 1.5 : 2);
```

### 5. Offscreen-кэширование glow-слоёв сфер

Glow-слои сфер перерисовывать каждый кадр не нужно — они меняются только при смене уровня. Кэшируем в offscreen canvas.

```javascript
// Создаём 1 раз при смене уровня
const glowCache = new OffscreenCanvas(size, size);
const gCtx = glowCache.getContext('2d');
// Рисуем все glow layers в кэш
// ...

// В основном loop — просто drawImage
ctx.drawImage(glowCache, x - size/2, y - size/2);
```

### 6. Потоки сфера↔сфера — упростить

На мобильных вместо 22-thread системы между соседними сферами — рисуем 1–3 простых волнистых линии. Экономит ~40% вычислений.

### 7. requestAnimationFrame throttling на low-end

```javascript
let lastFrame = 0;
const minInterval = tier === 'low' ? 33 : 0; // ~30fps cap

function draw(timestamp) {
  if (timestamp - lastFrame < minInterval) {
    animRef.current = requestAnimationFrame(draw);
    return;
  }
  lastFrame = timestamp;
  // ... render
}
```

---

## Альтернатива: WebGL / Three.js

Если нужно 60fps на всех устройствах с полным визуалом — рассмотреть перенос на WebGL:

| | Canvas 2D | WebGL (Three.js / Pixi.js) |
|---|----------|---------------------------|
| Glow/Blur | CPU (дорого) | GPU shader (дёшево) |
| Градиенты | CPU per-pixel | GPU texture |
| 1000 линий | Тяжело | Легко |
| Частицы | ~200 макс | 10 000+ |
| Сложность кода | Средняя | Высокая |
| Размер бандла | 0 KB | +50–150 KB |

Рекомендация: **начать с Canvas 2D + адаптивные оптимизации**, переходить на WebGL только если не удаётся удержать 30fps на целевых устройствах.

---

## Реализация в коде

```typescript
const TIER_CONFIG = {
  high: {
    dprMax: 2,
    particles: 120,
    threadSteps: 60,
    maxThreadsPerFlow: 22,
    useShadowBlur: true,
    maxGlowLayers: 8,
    interSphereThreads: 6,
    orbitalDots: 16,
    flyingParticles: true,
    coreLine: true,
  },
  medium: {
    dprMax: 2,
    particles: 60,
    threadSteps: 35,
    maxThreadsPerFlow: 12,
    useShadowBlur: false,
    maxGlowLayers: 4,
    interSphereThreads: 3,
    orbitalDots: 8,
    flyingParticles: false,
    coreLine: true,
  },
  low: {
    dprMax: 1.5,
    particles: 30,
    threadSteps: 20,
    maxThreadsPerFlow: 8,
    useShadowBlur: false,
    maxGlowLayers: 2,
    interSphereThreads: 1,
    orbitalDots: 4,
    flyingParticles: false,
    coreLine: false,
  },
};
```

---

## Тестовые устройства

| Устройство | Ожидаемый tier | Целевой FPS |
|-----------|---------------|-------------|
| iPhone 15 Pro | high | 60 |
| iPhone 12 | medium | 45+ |
| iPhone SE 2 | low | 30+ |
| Samsung S24 | high | 60 |
| Samsung A54 | medium | 45+ |
| Xiaomi Redmi Note 12 | low | 30+ |
| iPad Air | high | 60 |

---

## Чеклист

- [ ] Реализовать `getPerformanceTier()` или FPS-мониторинг
- [ ] Создать `TIER_CONFIG` с параметрами для 3 уровней
- [ ] Убрать `shadowBlur` на medium/low — заменить на double-stroke glow
- [ ] Ограничить нити до `maxThreadsPerFlow` per tier
- [ ] Снизить DPR на low-end
- [ ] Кэшировать glow-слои сфер в offscreen canvas
- [ ] Упростить межсферные потоки на мобильных
- [ ] Протестировать на iPhone SE 2, Redmi Note 12, Samsung A54
- [ ] Добавить FPS-счётчик в dev mode для отладки
