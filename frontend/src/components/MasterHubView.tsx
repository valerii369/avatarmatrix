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
  { key: "IDENTITY", name: "Личность", subtitle: "Я и тело", color: "#A855F7" },
  { key: "RESOURCES", name: "Ресурсы", subtitle: "Деньги и ценности", color: "#10B981" },
  { key: "COMMUNICATION", name: "Связи", subtitle: "Ум и окружение", color: "#06B6D4" },
  { key: "ROOTS", name: "Корни", subtitle: "Дом и семья", color: "#F97316" },
  { key: "CREATIVITY", name: "Творчество", subtitle: "Любовь и хобби", color: "#EC4899" },
  { key: "SERVICE", name: "Служение", subtitle: "Работа и здоровье", color: "#14B8A6" },
  { key: "PARTNERSHIP", name: "Партнерство", subtitle: "Отношения и союзы", color: "#3B82F6" },
  { key: "TRANSFORMATION", name: "Тень", subtitle: "Трансформация и сила", color: "#6366F1" },
  { key: "EXPANSION", name: "Поиск", subtitle: "Мудрость и вера", color: "#8B5CF6" },
  { key: "STATUS", name: "Статус", subtitle: "Карьера и цели", color: "#EF4444" },
  { key: "VISION", name: "Будущее", subtitle: "Мечты и группы", color: "#D946EF" },
  { key: "SPIRIT", name: "Дух", subtitle: "Тишина и тайны", color: "#64748B" },
];

const TRAIT_DESCRIPTIONS: Record<string, string> = {
  // Архетипы
  "Странник": "Поиск свободы и новых смыслов через опыт",
  "Герой": "Преодоление препятствий и достижение великих целей",
  "Мудрец": "Постижение истины и системное понимание мира",
  "Маг": "Трансформация реальности через волю и знание",
  "Творец": "Самовыражение и создание нового уникального продукта",
  "Правитель": "Создание порядка и управление структурами",
  "Опекун": "Забота, поддержка и защита окружающих",
  "Искатель": "Исследование неизведанного и поиск истины",
  "Бунтарь": "Разрушение старых структур ради перемен",
  "Шут": "Радость жизни и высмеивание ложных догм",
  
  // Энергии
  "Ян": "Активная, направленная вовне мужская энергия",
  "Инь": "Принимающая, интуитивная женская энергия",
  
  // Роли
  "Лидер": "Ведущий и вдохновляющий за собой других",
  "Наблюдатель": "Анализирующий и видящий суть процессов со стороны",
  "Целитель": "Восстанавливающий баланс и гармонию систем",
  "Архитектор": "Проектирующий будущее и сложные структуры",

  // Социальный интерфейс
  "Мировоззрение": "Индивидуальная система взглядов и ценностей аватара",
  "Коммуникация": "Приоритетный способ взаимодействия и обмена информацией",
  "Экзистенциальный урок": "Ключевая жизненная задача для текущего этапа",
};

export default function MasterHubView({ userId }: { userId: number }) {
  const [selectedSphere, setSelectedSphere] = useState<string | null>(null);
  const [subTab, setSubTab] = useState<"personality" | "sides" | "analysis">("personality");
  const [activeTooltip, setActiveTooltip] = useState<{label: string, value: string} | null>(null);

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
    <div className="px-4 pt-0 space-y-6 pb-12 relative">
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
            <div className="flex p-1 gap-1 bg-white/[0.04] border border-white/10 rounded-[14px]">
              <button
                onClick={() => setSubTab("personality")}
                style={{
                  padding: "8px 4px",
                  borderRadius: 10,
                  fontSize: 11,
                  fontWeight: 500,
                  transition: "all 0.2s",
                  background: subTab === "personality" ? "rgba(255,255,255,0.1)" : "transparent",
                  color: subTab === "personality" ? "var(--text-primary)" : "var(--text-muted)",
                  border: "none",
                  flex: 1
                }}
              >
                О личности
              </button>
              <button
                onClick={() => setSubTab("sides")}
                style={{
                  padding: "8px 4px",
                  borderRadius: 10,
                  fontSize: 11,
                  fontWeight: 500,
                  transition: "all 0.2s",
                  background: subTab === "sides" ? "rgba(255,255,255,0.1)" : "transparent",
                  color: subTab === "sides" ? "var(--text-primary)" : "var(--text-muted)",
                  border: "none",
                  flex: 1
                }}
              >
                Стороны
              </button>
              <button
                onClick={() => setSubTab("analysis")}
                style={{
                  padding: "8px 4px",
                  borderRadius: 10,
                  fontSize: 11,
                  fontWeight: 500,
                  transition: "all 0.2s",
                  background: subTab === "analysis" ? "rgba(255,255,255,0.1)" : "transparent",
                  color: subTab === "analysis" ? "var(--text-primary)" : "var(--text-muted)",
                  border: "none",
                  flex: 1
                }}
              >
                Разбор сфер
              </button>
            </div>

            {subTab === "personality" && (
              <motion.div
                key="personality-tab"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                {/* ── Portrait Summary Card ── */}
                <motion.div
                  layout
                  className="p-5 rounded-[1.25rem] bg-gradient-to-br from-violet-600/[0.08] to-blue-600/[0.04] border border-white/10 backdrop-blur-3xl shadow-xl relative overflow-hidden"
                >
                  <div className="absolute -top-10 -right-10 w-40 h-40 bg-violet-500/10 blur-[60px] rounded-full" />
                  <div className="flex flex-col gap-3.5">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
                      <span className="text-[9px] font-bold text-violet-400/80 uppercase tracking-[0.2em]">
                        Идентификация Аватара
                      </span>
                    </div>

                    <p className="text-sm font-medium text-white leading-snug">
                      {portrait_summary.core_identity}
                    </p>

                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <SummaryTag label="Архетип" value={portrait_summary.core_archetype} color="violet" onClick={() => setActiveTooltip({ label: "Архетип", value: portrait_summary.core_archetype })} />
                      <SummaryTag label="Роль" value={portrait_summary.narrative_role} color="blue" onClick={() => setActiveTooltip({ label: "Роль", value: portrait_summary.narrative_role })} />
                      <SummaryTag label="Энергия" value={portrait_summary.energy_type} color="emerald" onClick={() => setActiveTooltip({ label: "Энергия", value: portrait_summary.energy_type })} />
                      <SummaryTag label="Фокус" value={portrait_summary.current_dynamic} color="amber" onClick={() => setActiveTooltip({ label: "Фокус", value: portrait_summary.current_dynamic })} />
                    </div>

                    <div className="pt-4 mt-2 border-t border-white/[0.05] space-y-3">
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-bold text-white/20 uppercase tracking-[0.2em]">Социальный интерфейс</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <SummaryTag label="Мировоззрение" value={deep_profile_data.social_interface.worldview_stance} color="blue" onClick={() => setActiveTooltip({ label: "Мировоззрение", value: deep_profile_data.social_interface.worldview_stance })} />
                        <SummaryTag label="Коммуникация" value={deep_profile_data.social_interface.communication_style} color="violet" onClick={() => setActiveTooltip({ label: "Коммуникация", value: deep_profile_data.social_interface.communication_style })} />
                      </div>
                      <div 
                        onClick={() => setActiveTooltip({ label: "Экзистенциальный урок", value: deep_profile_data.social_interface.karmic_lesson })}
                        className="pt-3 border-t border-white/[0.03] cursor-pointer group active:scale-[0.99] transition-all"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="text-[9px] font-bold uppercase tracking-tight text-white/30">Экзистенциальный урок</div>
                          <Info size={10} className="text-white/10 group-hover:text-white/30 transition-colors" />
                        </div>
                        <div className="text-xs italic text-violet-300/90 leading-relaxed">
                          «{deep_profile_data.social_interface.karmic_lesson}»
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              </motion.div>
            )}

            {subTab === "sides" && (
              <motion.div
                key="sides-tab"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-4"
              >
                <div className="grid grid-cols-2 gap-3">
                  <PolarityCard title="Сильные стороны" items={deep_profile_data.polarities.core_strengths} icon={ShieldCheck} color="#10B981" />
                  <PolarityCard title="Теневые аспекты" items={deep_profile_data.polarities.shadow_aspects} icon={AlertCircle} color="#EF4444" />
                </div>
              </motion.div>
            )}

            {subTab === "analysis" && (
              <motion.div
                key="analysis-tab"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                {/* ── 12 Spheres Grid (6x2) ── */}
                <div className="grid grid-cols-2 gap-2.5">
                  {SPHERES_META.map((meta, idx) => {
                    const status = deep_profile_data.spheres_status[meta.key];
                    const Icon = ICON_MAP[meta.key] || User;
                    return (
                      <motion.div
                        key={meta.key}
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.015 }}
                        onClick={() => setSelectedSphere(meta.key)}
                        className="p-2.5 rounded-[1.25rem] bg-white/[0.02] border border-white/[0.04] flex items-center gap-3 active:scale-[0.98] transition-all cursor-pointer hover:bg-white/[0.05] group"
                      >
                        <div 
                          className="w-10 h-10 flex-shrink-0 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110"
                          style={{ backgroundColor: `${meta.color}15`, color: meta.color, border: `1px solid ${meta.color}20` }}
                        >
                          <Icon size={20} />
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span className="text-[8px] font-bold text-white/20 uppercase tracking-wider mb-0.5">
                            {status?.status || "Инициация"}
                          </span>
                          <span className="font-bold text-[12px] text-white/90 block leading-none truncate">
                            {meta.name}
                          </span>
                          <p className="text-[9px] text-white/40 leading-tight font-light truncate mt-1">
                            {meta.subtitle}
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

            <div className="space-y-4">
              <div className="flex items-center gap-4 px-2">
                <div 
                  className="w-11 h-11 rounded-2xl flex items-center justify-center shadow-lg"
                  style={{ 
                    backgroundColor: `${activeSphereMeta?.color}20`, 
                    color: activeSphereMeta?.color,
                    border: `1px solid ${activeSphereMeta?.color}30`
                  }}
                >
                  {activeSphereMeta && (() => {
                    const Icon = ICON_MAP[activeSphereMeta.key];
                    return <Icon size={22} />;
                  })()}
                </div>
                <div className="flex flex-col">
                  <h1 className="text-xl font-bold text-white tracking-tight mb-0.5">
                    {activeSphereMeta?.name}
                  </h1>
                  <span className="text-[9px] font-bold text-white/30 uppercase tracking-widest leading-none">
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

      {/* ── Tooltip Overlay ── */}
      <AnimatePresence>
        {activeTooltip && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setActiveTooltip(null)}
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100]"
            />
            <motion.div 
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed bottom-0 left-0 right-0 bg-[#0a0a0a] border-t border-white/10 rounded-t-[2rem] px-6 pt-5 pb-10 z-[101] shadow-2xl"
            >
              <div className="w-12 h-1.5 bg-white/10 rounded-full mx-auto mb-6" />
              <div className="space-y-2.5">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest">{activeTooltip.label}</span>
                  <h3 className="text-xl font-bold text-white tracking-tight">{activeTooltip.value}</h3>
                </div>
                <p className="text-[13px] text-white/60 leading-relaxed font-light">
                  {TRAIT_DESCRIPTIONS[activeTooltip.value] || "Глубинный смысл этого качества раскрывается в твоей персональной истории развития."}
                </p>
                <button 
                  onClick={() => setActiveTooltip(null)}
                  className="w-full py-4 mt-1.5 bg-white/5 hover:bg-white/10 border border-white/5 rounded-2xl text-xs font-bold uppercase tracking-widest transition-colors"
                >
                  Понятно
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Sub-components for cleaner code ──────────────────────────────────────────

function SummaryTag({ label, value, color, onClick }: any) {
  const colors: Record<string, string> = {
    violet: "bg-violet-500/10 text-violet-300 border-violet-500/20 hover:bg-violet-500/20",
    blue: "bg-blue-500/10 text-blue-300 border-blue-500/20 hover:bg-blue-500/20",
    emerald: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20 hover:bg-emerald-500/20",
    amber: "bg-amber-500/10 text-amber-300 border-amber-500/20 hover:bg-amber-500/20",
  };
  return (
    <div 
      onClick={onClick}
      className={`p-2 rounded-lg border cursor-pointer transition-all active:scale-[0.97] ${colors[color] || colors.violet} flex flex-col gap-0.5 relative group`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[8px] uppercase font-bold opacity-40">{label}</span>
        <Info size={10} className="text-white/20 group-hover:text-white/40 transition-colors" />
      </div>
      <span className="text-[12px] font-bold truncate tracking-tight">{value}</span>
    </div>
  );
}

function PolarityCard({ title, items, icon: Icon, color }: any) {
  return (
    <div className="p-4 rounded-[1.25rem] bg-white/[0.03] border border-white/5 flex flex-col gap-3">
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
