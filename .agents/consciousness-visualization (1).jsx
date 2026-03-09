import { useState, useEffect, useRef, useCallback } from "react";

const SPHERES = [
  { name: "Здоровье", icon: "♡", color: [120, 255, 180] },
  { name: "Финансы", icon: "◈", color: [255, 215, 80] },
  { name: "Отношения", icon: "∞", color: [255, 130, 180] },
  { name: "Карьера", icon: "⬡", color: [80, 180, 255] },
  { name: "Духовность", icon: "✦", color: [200, 160, 255] },
  { name: "Творчество", icon: "◎", color: [255, 160, 80] },
  { name: "Знания", icon: "◇", color: [100, 220, 255] },
  { name: "Социум", icon: "⊛", color: [180, 255, 160] },
];

const lerp = (a, b, t) => a + (b - a) * t;
const easePow = (t, p) => Math.pow(t, p);

function hawkinsToRank(s) {
  const t = [20,50,100,175,200,310,400,500,600,1000];
  const i = t.findIndex(v => s <= v);
  return i === -1 ? 10 : i + 1;
}

function generateCards() {
  return SPHERES.map((_, si) => {
    const presets = [[8,780],[5,420],[7,650],[4,350],[12,900],[6,550],[7,600],[3,300]];
    const [ac, avg] = presets[si];
    return Array.from({length: 22}, (_, ci) => {
      const active = ci < ac;
      return { id: ci, is_active: active, hawkins_score: active ? Math.round(Math.max(20, Math.min(1000, avg + (Math.random()-0.5)*300))) : 0 };
    });
  });
}

function calcState(cards) {
  const active = cards.filter(c => c.is_active);
  const total = active.reduce((s,c) => s + c.hawkins_score, 0);
  return {
    active_count: active.length,
    sphere_score: total / 22000,
    sphere_hawkins: active.length > 0 ? Math.round(total / active.length) : 0,
    active_cards: active,
  };
}

// Detect performance tier
function getTier() {
  const mob = /iPhone|iPad|Android/i.test(navigator.userAgent);
  const cores = navigator.hardwareConcurrency || 2;
  if (!mob && cores >= 6) return 'high';
  if (mob && cores >= 6) return 'medium';
  return mob ? 'low' : 'medium';
}

const TIERS = {
  high:   { dpr: 2, particles: 120, steps: 55, maxThreads: 22, glowLayers: 8, interThreads: 5, dots: 14 },
  medium: { dpr: 1.5, particles: 60, steps: 32, maxThreads: 12, glowLayers: 4, interThreads: 3, dots: 8 },
  low:    { dpr: 1.5, particles: 30, steps: 20, maxThreads: 8,  glowLayers: 2, interThreads: 1, dots: 4 },
};

export default function QuantumShiftFinal() {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const [allCards, setAllCards] = useState(generateCards);
  const particlesRef = useRef([]);
  const smoothRef = useRef(SPHERES.map(() => 0));
  const tierRef = useRef('high');
  const fpsRef = useRef({ count: 0, last: 0, current: 60 });

  const states = allCards.map(c => calcState(c));

  const initParticles = useCallback((w, h, count) => {
    particlesRef.current = Array.from({length: count}, () => ({
      x: Math.random()*w, y: Math.random()*h,
      vx: (Math.random()-0.5)*0.3, vy: (Math.random()-0.5)*0.3,
      size: Math.random()*2+0.5, alpha: Math.random()*0.3+0.08,
      pulse: Math.random()*Math.PI*2,
    }));
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let w, h;
    tierRef.current = getTier();
    let T = TIERS[tierRef.current];

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio||1, T.dpr);
      const rect = canvas.getBoundingClientRect();
      w = rect.width; h = rect.height;
      canvas.width = w*dpr; canvas.height = h*dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      initParticles(w, h, T.particles);
    };
    resize();
    window.addEventListener("resize", resize);

    const getPositions = () => {
      const cx = w/2, cy = h/2, r = Math.min(w,h)*0.32;
      return SPHERES.map((s,i) => {
        const a = (i/8)*Math.PI*2 - Math.PI/2;
        return { x: cx+Math.cos(a)*r, y: cy+Math.sin(a)*r, ...s };
      });
    };

    // ===== BACKGROUND =====
    const drawBg = (t) => {
      const g = ctx.createRadialGradient(w/2,h/2,0,w/2,h/2,w*0.7);
      g.addColorStop(0,"rgba(15,8,30,1)"); g.addColorStop(0.5,"rgba(8,4,20,1)"); g.addColorStop(1,"rgba(2,1,8,1)");
      ctx.fillStyle = g; ctx.fillRect(0,0,w,h);
      for (let i=0;i<3;i++) {
        const nx=w*(0.3+i*0.2)+Math.sin(t*0.0002+i)*30, ny=h*(0.3+i*0.15)+Math.cos(t*0.0003+i)*20;
        const ng = ctx.createRadialGradient(nx,ny,0,nx,ny,w*0.25);
        const hu = (200+i*40+t*0.01)%360;
        ng.addColorStop(0,`hsla(${hu},60%,20%,0.04)`); ng.addColorStop(0.5,`hsla(${hu},40%,15%,0.02)`); ng.addColorStop(1,"transparent");
        ctx.fillStyle = ng; ctx.fillRect(0,0,w,h);
      }
    };

    // ===== PARTICLES =====
    const drawParts = (t) => {
      particlesRef.current.forEach(p => {
        p.x+=p.vx; p.y+=p.vy;
        if(p.x<0) p.x=w; if(p.x>w) p.x=0; if(p.y<0) p.y=h; if(p.y>h) p.y=0;
        const pu = Math.sin(t*0.002+p.pulse)*0.3+0.7;
        ctx.beginPath(); ctx.arc(p.x,p.y,p.size*pu,0,Math.PI*2);
        ctx.fillStyle=`rgba(180,200,255,${p.alpha*pu})`; ctx.fill();
      });
    };

    // ===== SACRED CENTER =====
    const drawCenter = (t, cx, cy, sts) => {
      const gs = sts.reduce((s,st) => s+st.sphere_score, 0)/8;
      const gi = easePow(gs, 1.3);
      const bR = Math.min(w,h)*0.1;
      const br = Math.sin(t*0.0008)*4;

      // Aura
      for (let l=4;l>=0;l--) {
        const sp = bR*1.2+l*(12+gi*20)+br;
        const al = (0.04+gi*0.05)*(1-l/5);
        const ag = ctx.createRadialGradient(cx,cy,bR*0.3,cx,cy,sp);
        ag.addColorStop(0,`rgba(180,200,255,${al})`); ag.addColorStop(0.4,`rgba(140,160,230,${al*0.5})`); ag.addColorStop(1,"transparent");
        ctx.fillStyle=ag; ctx.beginPath(); ctx.arc(cx,cy,sp,0,Math.PI*2); ctx.fill();
      }

      const fR = bR*0.55, rot = t*0.0002;
      ctx.save(); ctx.translate(cx,cy);

      // Rings
      for (let rn=3;rn>=1;rn--) {
        const rr = fR*rn*0.65;
        ctx.strokeStyle=`rgba(180,210,255,${((0.06+gi*0.08)*(1-rn*0.2))*(Math.sin(t*0.001+rn)*0.15+0.85)})`;
        ctx.lineWidth=0.5+gi*0.5; ctx.beginPath(); ctx.arc(0,0,rr,0,Math.PI*2); ctx.stroke();
      }

      // Center circle
      const cp = Math.sin(t*0.0015)*0.1+0.9;
      ctx.strokeStyle=`rgba(200,225,255,${(0.12+gi*0.15)*cp})`; ctx.lineWidth=0.6+gi*0.8;
      ctx.beginPath(); ctx.arc(0,0,fR*cp,0,Math.PI*2); ctx.stroke();

      // 6 petals
      for (let i=0;i<6;i++) {
        const a=(i/6)*Math.PI*2+rot, pp=Math.sin(t*0.0012+i*1.05)*0.1+0.9;
        const si2=i%8, [sr,sg,sb]=SPHERES[si2].color;
        const inf = easePow(sts[si2].sphere_score, 1.2);
        ctx.strokeStyle=`rgba(${Math.floor(lerp(180,sr,inf*0.5))},${Math.floor(lerp(210,sg,inf*0.5))},${Math.floor(lerp(255,sb,inf*0.5))},${(0.08+gi*0.14)*pp})`;
        ctx.lineWidth=0.5+gi*0.7;
        ctx.beginPath(); ctx.arc(Math.cos(a)*fR,Math.sin(a)*fR,fR*pp,0,Math.PI*2); ctx.stroke();
      }

      // Outer petals
      if (gi>0.25) {
        const oa=(gi-0.25)*0.2;
        for (let i=0;i<6;i++) {
          const a=(i/6)*Math.PI*2+rot+Math.PI/6, pp=Math.sin(t*0.001+i*0.9+2)*0.1+0.9;
          ctx.strokeStyle=`rgba(160,190,240,${oa*pp})`; ctx.lineWidth=0.4+gi*0.4;
          ctx.beginPath(); ctx.arc(Math.cos(a)*fR*1.73,Math.sin(a)*fR*1.73,fR*pp,0,Math.PI*2); ctx.stroke();
        }
      }

      // Metatron lines + Star
      if (gi>0.15) {
        const la = Math.min(0.12,(gi-0.15)*0.15);
        ctx.strokeStyle=`rgba(200,220,255,${la})`; ctx.lineWidth=0.4;
        for (let i=0;i<6;i++) {
          const a1=(i/6)*Math.PI*2+rot, a2=((i+2)/6)*Math.PI*2+rot;
          ctx.beginPath(); ctx.moveTo(Math.cos(a1)*fR,Math.sin(a1)*fR); ctx.lineTo(Math.cos(a2)*fR,Math.sin(a2)*fR); ctx.stroke();
        }
        for (let tr=0;tr<2;tr++) {
          ctx.beginPath();
          for (let v=0;v<3;v++) {
            const a=((v*2+tr)/6)*Math.PI*2+rot;
            if(v===0)ctx.moveTo(Math.cos(a)*fR*1.15,Math.sin(a)*fR*1.15);
            else ctx.lineTo(Math.cos(a)*fR*1.15,Math.sin(a)*fR*1.15);
          }
          ctx.closePath(); ctx.strokeStyle=`rgba(200,220,255,${la*0.8})`; ctx.lineWidth=0.5+gi*0.5; ctx.stroke();
        }
      }

      // Core
      const cPu = Math.sin(t*0.002)*0.2+0.8;
      const cg = ctx.createRadialGradient(0,0,0,0,0,fR*0.54);
      cg.addColorStop(0,`rgba(255,255,255,${(0.5+gi*0.4)*cPu})`);
      cg.addColorStop(0.3,`rgba(200,220,255,${(0.2+gi*0.2)*cPu})`);
      cg.addColorStop(1,"transparent");
      ctx.fillStyle=cg; ctx.beginPath(); ctx.arc(0,0,fR*0.54,0,Math.PI*2); ctx.fill();

      // Orbital dots
      const dc = T.dots;
      for (let d=0;d<dc;d++) {
        const or2=fR*(0.4+(d/dc)*1.2), spd=0.0006+(d%3)*0.0002, dir=d%2===0?1:-1;
        const da=t*spd*dir+(d/dc)*Math.PI*2;
        const dotA=(0.2+gi*0.5)*(Math.sin(t*0.003+d*1.7)*0.3+0.7);
        const ds=1+gi*2;
        const dg=ctx.createRadialGradient(Math.cos(da)*or2,Math.sin(da)*or2,0,Math.cos(da)*or2,Math.sin(da)*or2,ds*3);
        dg.addColorStop(0,`rgba(220,240,255,${dotA})`); dg.addColorStop(1,"transparent");
        ctx.fillStyle=dg; ctx.beginPath(); ctx.arc(Math.cos(da)*or2,Math.sin(da)*or2,ds*3,0,Math.PI*2); ctx.fill();
      }

      // Chakra axis
      const axG=ctx.createLinearGradient(0,-fR*1.6,0,fR*1.6);
      axG.addColorStop(0,`rgba(200,160,255,${0.05+gi*0.1})`); axG.addColorStop(0.5,`rgba(120,255,180,${0.08+gi*0.12})`); axG.addColorStop(1,`rgba(255,100,100,${0.05+gi*0.1})`);
      ctx.strokeStyle=axG; ctx.lineWidth=0.8+gi; ctx.beginPath(); ctx.moveTo(0,-fR*1.6); ctx.lineTo(0,fR*1.6); ctx.stroke();

      [[-1.4,[200,160,255]],[-0.95,[100,150,255]],[-0.5,[100,220,255]],[0,[120,255,180]],[0.5,[255,255,100]],[0.95,[255,180,80]],[1.4,[255,100,100]]].forEach(([yf,[cr,cg2,cb]],i) => {
        const yy=fR*yf, pu=Math.sin(t*0.003+i*0.9)*0.4+0.6, sz=3+gi*4;
        const chG=ctx.createRadialGradient(0,yy,0,0,yy,sz*3);
        chG.addColorStop(0,`rgba(${cr},${cg2},${cb},${(0.6+gi*0.3)*pu})`);
        chG.addColorStop(0.5,`rgba(${cr},${cg2},${cb},${0.15*pu})`); chG.addColorStop(1,"transparent");
        ctx.fillStyle=chG; ctx.beginPath(); ctx.arc(0,yy,sz*3,0,Math.PI*2); ctx.fill();
        ctx.fillStyle=`rgba(${Math.min(255,cr+60)},${Math.min(255,cg2+60)},${Math.min(255,cb+60)},${0.5*pu})`;
        ctx.beginPath(); ctx.arc(0,yy,sz*0.6,0,Math.PI*2); ctx.fill();
      });
      ctx.restore();
    };

    // ===== 22-THREAD FLOW (mobile-optimized) =====
    const drawFlow = (ctx, x1, y1, x2, y2, t, activeCards, ss, color, idx) => {
      if (!activeCards.length) return;
      const dx=x2-x1, dy=y2-y1, dist=Math.sqrt(dx*dx+dy*dy);
      const angle=Math.atan2(dy,dx), perpX=-Math.sin(angle), perpY=Math.cos(angle);
      const maxSpread = 6+ss*50;
      const steps = T.steps;

      // Limit threads for performance
      const visible = activeCards.length <= T.maxThreads
        ? activeCards
        : [...activeCards].sort((a,b) => b.hawkins_score - a.hawkins_score).slice(0, T.maxThreads);

      visible.forEach((card, ci) => {
        const pos = visible.length===1 ? 0 : (ci/(visible.length-1)-0.5)*maxSpread;
        const ci2 = card.hawkins_score/1000;
        const tw = 0.3+ci2*2.7;
        const ta = 0.04+ci2*0.18;
        const tAmp = 3+ci2*25;
        const tSpd = 0.001+ci2*0.002;
        const freq = 0.012+(card.id%5)*0.003;
        const [r,g,b] = color;
        const dim = 0.4+ci2*0.6;
        const pr=Math.floor(r*dim), pg=Math.floor(g*dim), pb=Math.floor(b*dim);
        const pulseA = 0.7+Math.sin(t*0.0012+card.id*0.5)*0.3;

        // Build path once
        ctx.beginPath();
        for (let s=0;s<=steps;s++) {
          const p=s/steps, fe=Math.sin(p*Math.PI);
          const px=x1+dx*p, py=y1+dy*p;
          const wv=Math.sin(p*dist*freq-t*tSpd+idx+card.id*0.7)*tAmp*fe;
          const wv2=Math.sin(p*dist*freq*2.1-t*tSpd*1.3+card.id)*tAmp*0.15*fe;
          const wx=px+perpX*(wv+wv2+pos), wy=py+perpY*(wv+wv2+pos);
          if(s===0) ctx.moveTo(wx,wy); else ctx.lineTo(wx,wy);
        }

        // Double-stroke glow (replaces shadowBlur — mobile friendly)
        if (ci2 > 0.2) {
          ctx.strokeStyle=`rgba(${r},${g},${b},${ta*pulseA*0.15})`;
          ctx.lineWidth=tw*4;
          ctx.stroke();
        }

        // Main thread
        ctx.strokeStyle=`rgba(${pr},${pg},${pb},${ta*pulseA})`;
        ctx.lineWidth=tw;
        ctx.stroke();

        // Bright core for high-level
        if (ci2>0.5) {
          ctx.strokeStyle=`rgba(${Math.min(255,r+80)},${Math.min(255,g+80)},${Math.min(255,b+80)},${(ci2-0.5)*0.2*pulseA})`;
          ctx.lineWidth=tw*0.4;
          ctx.stroke();
        }
      });

      // Core line
      if (ss>0.20) {
        const ca=(ss-0.20)*0.55;
        ctx.beginPath();
        for (let s=0;s<=steps;s++) {
          const p=s/steps, fe=Math.sin(p*Math.PI);
          const px=x1+dx*p, py=y1+dy*p;
          const wv=Math.sin(p*dist*0.014-t*0.002+idx)*5*fe;
          if(s===0) ctx.moveTo(px+perpX*wv,py+perpY*wv);
          else ctx.lineTo(px+perpX*wv,py+perpY*wv);
        }
        const [r,g,b]=color;
        // Glow via double-stroke
        ctx.strokeStyle=`rgba(${r},${g},${b},${ca*0.12})`;
        ctx.lineWidth=4+ss*8; ctx.stroke();
        ctx.strokeStyle=`rgba(${Math.min(255,r+80)},${Math.min(255,g+80)},${Math.min(255,b+80)},${ca})`;
        ctx.lineWidth=1+ss*2.5; ctx.stroke();
      }

      // Pulse particles
      if (ss>0.35) {
        const pc=Math.floor((ss-0.35)*12);
        for (let p=0;p<pc;p++) {
          const prog=((t*0.0003+p/pc+idx*0.1)%1), fe=Math.sin(prog*Math.PI);
          const px=x1+dx*prog, py=y1+dy*prog;
          const off=Math.sin(t*0.003+p*2.1)*maxSpread*0.5;
          const fx=px+perpX*off, fy=py+perpY*off;
          const [r,g,b]=color;
          const pA=fe*ss*0.5, pS=1+ss*2;
          const pgr=ctx.createRadialGradient(fx,fy,0,fx,fy,pS*2);
          pgr.addColorStop(0,`rgba(${Math.min(255,r+60)},${Math.min(255,g+60)},${Math.min(255,b+60)},${pA})`);
          pgr.addColorStop(1,"transparent");
          ctx.fillStyle=pgr; ctx.beginPath(); ctx.arc(fx,fy,pS*2,0,Math.PI*2); ctx.fill();
        }
      }
    };

    // ===== SPHERE =====
    const drawSphere = (ctx, x, y, name, icon, st, color, t, idx, isSel) => {
      const ss=st.sphere_score, vis=easePow(ss,1.3);
      const minR=Math.min(w,h)*0.022, maxR=Math.min(w,h)*0.08;
      const bR=minR+(maxR-minR)*vis;
      const br=Math.sin(t*0.0015+idx*0.8)*(2+vis*4);
      const cR=bR+br;
      const [r,g,b]=color;

      const gL=Math.min(T.glowLayers, 2+Math.floor(vis*6));
      for (let l=gL;l>=0;l--) {
        const sp=cR+l*(6+vis*18), al=(0.015+vis*0.06)*(1-l/(gL+1));
        const gl=ctx.createRadialGradient(x,y,cR*0.3,x,y,sp);
        gl.addColorStop(0,`rgba(${r},${g},${b},${al})`); gl.addColorStop(1,"transparent");
        ctx.fillStyle=gl; ctx.beginPath(); ctx.arc(x,y,sp,0,Math.PI*2); ctx.fill();
      }

      const sG=ctx.createRadialGradient(x-cR*0.3,y-cR*0.3,0,x,y,cR);
      sG.addColorStop(0,`rgba(${Math.min(255,r+80)},${Math.min(255,g+80)},${Math.min(255,b+80)},${0.1+vis*0.3})`);
      sG.addColorStop(0.6,`rgba(${r},${g},${b},${0.05+vis*0.15})`);
      sG.addColorStop(1,`rgba(${r*0.4},${g*0.4},${b*0.4},0.03)`);
      ctx.fillStyle=sG; ctx.beginPath(); ctx.arc(x,y,cR,0,Math.PI*2); ctx.fill();

      ctx.strokeStyle=`rgba(${r},${g},${b},${0.15+vis*0.5})`; ctx.lineWidth=0.5+vis*2;
      ctx.beginPath(); ctx.arc(x,y,cR,0,Math.PI*2); ctx.stroke();

      // Orbital
      ctx.save(); ctx.translate(x,y); ctx.rotate(t*0.0008+idx); ctx.scale(1,0.3);
      ctx.strokeStyle=`rgba(${r},${g},${b},${0.1+vis*0.25})`; ctx.lineWidth=0.5+vis;
      ctx.beginPath(); ctx.arc(0,0,cR*1.35,0,Math.PI*2); ctx.stroke();
      if(vis>0.3){ctx.rotate(0.5);ctx.strokeStyle=`rgba(${r},${g},${b},${(vis-0.3)*0.35})`;ctx.beginPath();ctx.arc(0,0,cR*1.55,0,Math.PI*2);ctx.stroke();}
      ctx.restore();

      // Sparkles
      const sc=Math.max(1,Math.floor(1+vis*12));
      for(let s=0;s<sc;s++){
        const sa=(s/sc)*Math.PI*2+t*0.002, sr=cR*0.6*(0.2+Math.sin(t*0.003+s*1.3)*0.5);
        ctx.fillStyle=`rgba(${Math.min(255,r+100)},${Math.min(255,g+100)},${Math.min(255,b+100)},${(0.2+Math.sin(t*0.004+s)*0.3)*vis})`;
        ctx.beginPath(); ctx.arc(x+Math.cos(sa)*sr,y+Math.sin(sa)*sr,0.5+vis*2,0,Math.PI*2); ctx.fill();
      }

      // Inner pulse
      if(vis>0.45){
        const pR=cR*(0.3+Math.sin(t*0.003+idx)*0.15);
        const pg=ctx.createRadialGradient(x,y,0,x,y,pR);
        pg.addColorStop(0,`rgba(${Math.min(255,r+60)},${Math.min(255,g+60)},${Math.min(255,b+60)},${(vis-0.45)*0.5})`);
        pg.addColorStop(1,"transparent");
        ctx.fillStyle=pg; ctx.beginPath(); ctx.arc(x,y,pR,0,Math.PI*2); ctx.fill();
      }

      // Icon
      ctx.fillStyle=`rgba(${r},${g},${b},${0.5+vis*0.5})`; ctx.font=`${12+vis*14}px sans-serif`;
      ctx.textAlign="center"; ctx.textBaseline="middle"; ctx.fillText(icon,x,y);

      // Labels
      ctx.fillStyle=`rgba(${r},${g},${b},${0.4+vis*0.4})`; ctx.font=`${10+vis*3}px "Segoe UI",system-ui,sans-serif`;
      ctx.textAlign="center"; ctx.fillText(name,x,y+cR+14);
      ctx.fillStyle=`rgba(${r},${g},${b},${0.3+vis*0.3})`; ctx.font=`bold 9px "Segoe UI",system-ui,sans-serif`;
      ctx.fillText(`${st.active_count}/22 · LVL ${hawkinsToRank(st.sphere_hawkins)}`,x,y+cR+26);

      if(isSel){ctx.strokeStyle=`rgba(${r},${g},${b},0.6)`;ctx.lineWidth=2;ctx.setLineDash([4,4]);ctx.beginPath();ctx.arc(x,y,cR+10,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);}
    };

    // ===== MAIN LOOP =====
    const draw = (ts) => {
      // FPS monitoring for auto-tier
      fpsRef.current.count++;
      if (ts - fpsRef.current.last >= 3000) {
        const fps = fpsRef.current.count / ((ts - fpsRef.current.last)/1000);
        fpsRef.current.current = fps;
        if (fps < 28 && tierRef.current !== 'low') { tierRef.current = 'low'; T = TIERS.low; }
        else if (fps < 40 && tierRef.current === 'high') { tierRef.current = 'medium'; T = TIERS.medium; }
        fpsRef.current.count = 0; fpsRef.current.last = ts;
      }

      for (let i=0;i<8;i++) smoothRef.current[i]=lerp(smoothRef.current[i],states[i].sphere_score,0.05);

      drawBg(ts); drawParts(ts);
      const pos = getPositions();
      const cx=w/2, cy=h/2;

      // Center → sphere
      pos.forEach((sp,i) => {
        drawFlow(ctx, cx, cy, sp.x, sp.y, ts, states[i].active_cards, smoothRef.current[i], sp.color, i*1.5);
      });

      // Sphere → sphere (simplified)
      pos.forEach((sp,i) => {
        const ni=(i+1)%8, next=pos[ni];
        const avg=(smoothRef.current[i]+smoothRef.current[ni])/2;
        if (avg>0.02) {
          const mc=sp.color.map((c,j)=>Math.floor(lerp(c,next.color[j],0.5)));
          const combo=[...states[i].active_cards.slice(0,T.interThreads),...states[ni].active_cards.slice(0,T.interThreads)];
          drawFlow(ctx,sp.x,sp.y,next.x,next.y,ts,combo,avg*0.5,mc,i*2.3+10);
        }
      });

      drawCenter(ts,cx,cy,states);

      pos.forEach((sp,i) => drawSphere(ctx,sp.x,sp.y,sp.name,sp.icon,states[i],sp.color,ts,i,selected===i));

      // Title
      ctx.fillStyle=`rgba(200,220,255,${0.35+Math.sin(ts*0.001)*0.1})`;
      ctx.font=`300 ${Math.min(w*0.028,17)}px "Segoe UI",system-ui,sans-serif`;
      ctx.textAlign="center";
      ctx.fillText("Q U A N T U M   S H I F T",w/2,h*0.055);

      // Bottom stats
      const gH=Math.round(states.reduce((s,st)=>s+st.sphere_hawkins,0)/8);
      const gC=states.reduce((s,st)=>s+st.active_count,0);
      ctx.fillStyle="rgba(180,200,255,0.25)";
      ctx.font=`200 ${Math.min(w*0.018,11)}px "Segoe UI",system-ui,sans-serif`;
      ctx.fillText(`${gC}/176 карт · Средний: ${gH} · ${Math.round(fpsRef.current.current)}fps · ${tierRef.current}`,w/2,h*0.955);

      animRef.current = requestAnimationFrame(draw);
    };

    fpsRef.current.last = performance.now();
    animRef.current = requestAnimationFrame(draw);

    const handleClick = (e) => {
      const rect=canvas.getBoundingClientRect(), mx=e.clientX-rect.left, my=e.clientY-rect.top;
      const pos=getPositions();
      let cl=null;
      pos.forEach((sp,i)=>{
        const vis=easePow(states[i].sphere_score,1.3);
        const hitR=Math.min(w,h)*0.022+(Math.min(w,h)*0.08-Math.min(w,h)*0.022)*vis+15;
        if(Math.sqrt((mx-sp.x)**2+(my-sp.y)**2)<hitR) cl=i;
      });
      setSelected(cl);
    };

    canvas.addEventListener("click",handleClick);
    return ()=>{window.removeEventListener("resize",resize);canvas.removeEventListener("click",handleClick);cancelAnimationFrame(animRef.current);};
  }, [allCards, selected, initParticles, states]);

  const setActiveCount = (si, count) => {
    setAllCards(prev => {
      const n=[...prev];
      n[si]=n[si].map((c,ci)=>({...c, is_active:ci<count, hawkins_score:ci<count?(c.hawkins_score||200+Math.floor(Math.random()*300)):0}));
      return n;
    });
  };

  const setAllLevels = (si, score) => {
    setAllCards(prev => {
      const n=[...prev];
      n[si]=n[si].map(c=>({...c, hawkins_score:c.is_active?score:0}));
      return n;
    });
  };

  const ss = selected!==null ? states[selected] : null;

  return (
    <div style={{width:"100%",height:"100vh",background:"#020108",position:"relative",overflow:"hidden",fontFamily:'"Segoe UI",system-ui,sans-serif'}}>
      <canvas ref={canvasRef} style={{width:"100%",height:"100%",display:"block"}} />
      {selected!==null && ss && (
        <div style={{position:"absolute",bottom:16,left:"50%",transform:"translateX(-50%)",background:"rgba(10,8,25,0.92)",backdropFilter:"blur(20px)",border:`1px solid rgba(${SPHERES[selected].color.join(",")},0.25)`,borderRadius:16,padding:"14px 22px",minWidth:320,maxWidth:"95vw",color:"#fff"}}>
          <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
            <span style={{fontSize:22,color:`rgb(${SPHERES[selected].color.join(",")})`}}>{SPHERES[selected].icon}</span>
            <span style={{fontSize:15,fontWeight:500,color:`rgb(${SPHERES[selected].color.join(",")})`}}>{SPHERES[selected].name}</span>
            <span style={{marginLeft:"auto",fontSize:12,opacity:0.5}}>Score: {(ss.sphere_score*100).toFixed(1)}%</span>
          </div>
          <div style={{display:"flex",justifyContent:"space-between",fontSize:10,opacity:0.5,marginBottom:4}}>
            <span>Активных карт: {ss.active_count}/22</span>
            <span>LVL {hawkinsToRank(ss.sphere_hawkins)} · Hawkins {ss.sphere_hawkins}</span>
          </div>
          <input type="range" min={0} max={22} step={1} value={ss.active_count}
            onChange={(e)=>setActiveCount(selected,Number(e.target.value))}
            style={{width:"100%",accentColor:`rgb(${SPHERES[selected].color.join(",")})`,height:4}} />
          <div style={{display:"flex",justifyContent:"space-between",fontSize:9,opacity:0.35,marginTop:2}}>
            <span>0 карт</span><span>5</span><span>10</span><span>15</span><span>22</span>
          </div>
          <div style={{marginTop:10,fontSize:10,opacity:0.5,marginBottom:4}}>Уровень всех карт</div>
          <input type="range" min={0} max={1000} step={10} value={ss.sphere_hawkins}
            onChange={(e)=>setAllLevels(selected,Number(e.target.value))}
            style={{width:"100%",accentColor:`rgb(${SPHERES[selected].color.join(",")})`,height:4}} />
          <div style={{display:"flex",justifyContent:"space-between",fontSize:9,opacity:0.35,marginTop:2}}>
            <span>Стыд · 0</span><span>Страх</span><span>Смелость · 200</span><span>Любовь · 500</span><span>1000</span>
          </div>
        </div>
      )}
    </div>
  );
}
