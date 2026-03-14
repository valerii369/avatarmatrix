import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useSWR from "swr";
import { masterHubAPI } from "@/lib/api";
import { 
  User, Wallet, Heart, Home, Award, Activity, Zap, Moon, 
  ArrowLeft, Info, Eye, EyeOff, Sparkles, AlertCircle, ShieldCheck,
  Compass, Users
} from "lucide-react";

const ICON_MAP: Record<string, any> = {
  IDENTITY: User,
  RESOURCES: Wallet,
  COMMUNICATION: Zap,
  ROOTS: Home,
  CREATIVITY: Heart,
  SERVICE: Activity,
  PARTNERSHIP: Zap, // Using Zap or another icon if needed
  TRANSFORMATION: Sparkles,
  EXPANSION: Compass,
  STATUS: Award,
  VISION: Users,
  SPIRIT: Moon,
};

const SPHERES_META = [
  { key: "IDENTITY", name: "Личность", color: "#A855F7" },
  { key: "RESOURCES", name: "Ресурсы", color: "#10B981" },
  { key: "COMMUNICATION", name: "Связи", color: "#06B6D4" },
  { key: "ROOTS", name: "Корни", color: "#F97316" },
  { key: "CREATIVITY", name: "Творчество", color: "#EC4899" },
  { key: "SERVICE", name: "Служение", color: "#14B8A6" },
  { key: "PARTNERSHIP", name: "Партнерство", color: "#3B82F6" },
  { key: "TRANSFORMATION", name: "Тень", color: "#6366F1" },
  { key: "EXPANSION", name: "Поиск", color: "#8B5CF6" },
  { key: "STATUS", name: "Статус", color: "#EF4444" },
  { key: "VISION", name: "Будущее", color: "#D946EF" },
  { key: "SPIRIT", name: "Дух", color: "#64748B" },
];

export default function MasterHubView({ userId }: { userId: number }) {
  const [selectedSphere, setSelectedSphere] = useState<string | null>(null);
  const [subTab, setSubTab] = useState<"personality" | "analysis">("personality");

  const { data: hub, isValidating: hubLoading } = useSWR(
    userId ? ["master-hub", userId] : null,
    () => masterHubAPI.get(userId).then(res => res.data).catch(() => null)
  );

  if (hubLoading && !hub) {
    return (
      <div className="p-6 grid grid-cols-1 gap-4">
        {[...Array(12)].map((_, i) => (
          <div key={i} className="h-20 bg-white/5 rounded-3xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (!hub && !hubLoading) {
    return (
      <div className="p-10 text-center opacity-50 flex flex-col items-center gap-4">
        <Sparkles className="text-violet-500 animate-pulse" size={48} />
        <p className="text-sm font-medium">Твой Паспорт Личности формируется... Пройди первую сессию рефлексии.</p>
      </div>
    );
  }

  const { portrait_summary, deep_profile_data } = hub;

  const activeSphereMeta = SPHERES_META.find(s => s.key === selectedSphere);
  const activeSphereData = selectedSphere ? deep_profile_data?.spheres_status?.[selectedSphere] : null;

  return (
    <div className="px-4 py-2 space-y-6 pb-12 relative">
      <AnimatePresence mode="wait">
        {!selectedSphere ? (
          <motion.div
            key="hub-main"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            {/* ── Sub-Navigation Tabs ── */}
            <div className="flex p-1 gap-1 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 mx-1">
              <button
                onClick={() => setSubTab("personality")}
                className={`flex-1 py-2.5 rounded-xl text-[11px] font-bold uppercase tracking-wider transition-all ${
                  subTab === "personality" 
                  ? "bg-violet-500/20 text-violet-300 border border-violet-500/30 shadow-lg" 
                  : "text-white/40 hover:text-white/60"
                }`}
              >
                О личности
              </button>
              <button
                onClick={() => setSubTab("analysis")}
                className={`flex-1 py-2.5 rounded-xl text-[11px] font-bold uppercase tracking-wider transition-all ${
                  subTab === "analysis" 
                  ? "bg-blue-500/20 text-blue-300 border border-blue-500/30 shadow-lg" 
                  : "text-white/40 hover:text-white/60"
                }`}
              >
                Разбор
              </button>
            </div>

            {subTab === "personality" ? (
              <motion.div
                key="personality-tab"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-6"
              >
                {/* ── Portrait Summary Card ── */}
                <motion.div
                  layout
                  className="p-6 rounded-[2.5rem] bg-gradient-to-br from-violet-600/10 to-blue-600/5 border border-white/10 backdrop-blur-3xl shadow-2xl relative overflow-hidden"
                >
                  <div className="absolute -top-10 -right-10 w-40 h-40 bg-violet-500/20 blur-[60px] rounded-full" />
                  <div className="flex flex-col gap-4">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
                      <span className="text-[10px] font-bold text-violet-400 uppercase tracking-[0.3em]">
                        Идентификация Аватара
                      </span>
                    </div>

                    <p className="text-sm font-medium text-white leading-snug">
                      {portrait_summary.core_identity}
                    </p>

                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <SummaryTag label="Архетип" value={portrait_summary.core_archetype} color="violet" />
                      <SummaryTag label="Роль" value={portrait_summary.narrative_role} color="blue" />
                      <SummaryTag label="Энергия" value={portrait_summary.energy_type} color="emerald" />
                      <SummaryTag label="Фокус" value={portrait_summary.current_dynamic} color="amber" />
                    </div>
                  </div>
                </motion.div>

                {/* ── Polarities & Social Interface (Always visible in personality tab) ── */}
                <div className="grid grid-cols-2 gap-3">
                  <PolarityCard title="Сильные стороны" items={deep_profile_data.polarities.core_strengths} icon={ShieldCheck} color="#10B981" />
                  <PolarityCard title="Теневые аспекты" items={deep_profile_data.polarities.shadow_aspects} icon={AlertCircle} color="#EF4444" />
                </div>
                
                <div className="p-5 rounded-3xl bg-white/[0.03] border border-white/[0.05] space-y-4 shadow-xl">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-white/30 flex items-center gap-2">
                    <Info size={14} /> Социальный интерфейс
                  </h3>
                  <div className="space-y-3">
                    <InfoBlock label="Мировоззрение" text={deep_profile_data.social_interface.worldview_stance} />
                    <InfoBlock label="Коммуникация" text={deep_profile_data.social_interface.communication_style} />
                    <div className="pt-2 border-t border-white/5">
                      <div className="text-[9px] text-white/40 mb-1">Экзистенциальный урок</div>
                      <div className="text-xs italic text-violet-300">«{deep_profile_data.social_interface.karmic_lesson}»</div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="analysis-tab"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                {/* ── 12 Spheres Grid ── */}
                <div className="grid grid-cols-1 gap-3">
                  {SPHERES_META.map((meta, idx) => {
                    const status = deep_profile_data.spheres_status[meta.key];
                    const Icon = ICON_MAP[meta.key] || User;
                    return (
                      <motion.div
                        key={meta.key}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.05 }}
                        onClick={() => setSelectedSphere(meta.key)}
                        className="p-4 rounded-3xl bg-white/[0.02] border border-white/[0.04] flex items-center gap-4 active:scale-[0.98] transition-all cursor-pointer hover:bg-white/[0.05] group"
                      >
                        <div 
                          className="w-12 h-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110"
                          style={{ backgroundColor: `${meta.color}15`, color: meta.color, border: `1px solid ${meta.color}20` }}
                        >
                          <Icon size={22} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-sm text-white/90">{meta.name}</span>
                            <span className="text-[9px] font-bold text-white/30 uppercase tracking-tighter bg-white/5 px-2 py-0.5 rounded-full">
                              {status?.status || "Инициация"}
                            </span>
                          </div>
                          <p className="text-[11px] text-white/50 leading-relaxed line-clamp-1 mt-0.5 font-light">
                            {status?.insight || "Гармонизация сферы..."}
                          </p>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </motion.div>
        ) : (
          /* ── Sphere Detail View ── */
          <motion.div
            key="sphere-detail"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="space-y-6 pt-2"
          >
            <button 
              onClick={() => setSelectedSphere(null)}
              className="flex items-center gap-2 text-white/40 hover:text-white transition-colors text-[10px] font-bold uppercase tracking-widest pl-2"
            >
              <ArrowLeft size={16} /> Назад в Океан
            </button>

            <div className="space-y-6">
              <div className="flex items-center gap-5 px-2">
                <div 
                  className="w-16 h-16 rounded-[1.5rem] flex items-center justify-center shadow-2xl"
                  style={{ 
                    backgroundColor: `${activeSphereMeta?.color}20`, 
                    color: activeSphereMeta?.color,
                    border: `1px solid ${activeSphereMeta?.color}30`
                  }}
                >
                  {activeSphereMeta && (() => {
                    const Icon = ICON_MAP[activeSphereMeta.key];
                    return <Icon size={32} />;
                  })()}
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-white tracking-tight">
                    {activeSphereMeta?.name}
                  </h1>
                  <span className="px-2 py-0.5 rounded-full bg-white/5 text-[10px] font-bold text-white/40 uppercase tracking-widest">
                    {activeSphereData?.status || "Стадия не определена"}
                  </span>
                </div>
              </div>

              <div className="relative overflow-hidden min-h-[400px] px-2 py-4">
                 <div 
                  className="absolute -top-32 -right-32 w-80 h-80 blur-[120px] -z-10 opacity-20"
                  style={{ backgroundColor: activeSphereMeta?.color }}
                 />
                 
                 <p className="text-sm leading-relaxed text-white/80 whitespace-pre-wrap font-light">
                   {activeSphereData?.insight || "Глубинный смысл этой сферы раскроется в процессе твоей эволюции."}
                 </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Sub-components for cleaner code ──────────────────────────────────────────

function SummaryTag({ label, value, color }: any) {
  const colors: Record<string, string> = {
    violet: "bg-violet-500/10 text-violet-300 border-violet-500/20",
    blue: "bg-blue-500/10 text-blue-300 border-blue-500/20",
    emerald: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    amber: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  };
  return (
    <div className={`p-2 rounded-xl border ${colors[color] || colors.violet} flex flex-col gap-0.5`}>
      <span className="text-[8px] uppercase font-bold opacity-50">{label}</span>
      <span className="text-[10px] font-bold truncate">{value}</span>
    </div>
  );
}

function PolarityCard({ title, items, icon: Icon, color }: any) {
  return (
    <div className="p-4 rounded-3xl bg-white/5 border border-white/10 flex flex-col gap-3">
      <div className="flex items-center gap-2" style={{ color }}>
        <Icon size={16} />
        <span className="text-[10px] font-bold uppercase tracking-wider">{title}</span>
      </div>
      <div className="space-y-1">
        {items.length > 0 ? items.map((item: string, i: number) => (
          <div key={i} className="text-[11px] text-white/70 leading-tight flex gap-1.5 font-light">
            <span className="opacity-30">•</span> {item}
          </div>
        )) : <span className="text-[10px] italic text-white/20">Исследуется...</span>}
      </div>
    </div>
  );
}

function InfoBlock({ label, text }: any) {
  return (
    <div>
      <div className="text-[9px] font-bold uppercase tracking-tight text-white/40 mb-0.5">{label}</div>
      <p className="text-xs text-white/80 font-light leading-snug">{text}</p>
    </div>
  );
}
