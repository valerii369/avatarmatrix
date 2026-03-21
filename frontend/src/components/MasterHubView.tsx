import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useSWR, { mutate } from "swr";
import { masterHubAPI, economyAPI } from "@/lib/api";
import { useUserStore } from "@/lib/store";
import { useAudio } from "@/lib/hooks/useAudio";
import { 
  User, Wallet, Heart, Home, Award, Activity, Zap, Moon, 
  ArrowLeft, Info, Eye, EyeOff, Sparkles, AlertCircle, ShieldCheck,
  Compass, Users, ChevronDown, ChevronUp
} from "lucide-react";
import { dsbAPI } from "@/lib/api";

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

// --- DSB Patch Constants ---
const DSB_SYSTEM_SHORT: Record<string, string> = {
  western_astrology: "ASTRO",
  human_design: "HD",
  gene_keys: "GK",
  numerology: "NUM",
};

const INFLUENCE_SORT: Record<string, number> = {
  high: 3,
  medium: 2,
  low: 1
};

// --- DSB Patch Components ---

function DSBInfluenceBadge({ level }: { level: string }) {
  const cfg: Record<string, any> = {
    high: { color: "#EF4444", bg: "rgba(239, 68, 68, 0.1)", label: "HIGH" },
    medium: { color: "#F59E0B", bg: "rgba(245, 158, 11, 0.1)", label: "MED" },
    low: { color: "#10B981", bg: "rgba(16, 185, 129, 0.1)", label: "LOW" },
  };
  const s = cfg[level] || cfg.low;
  return (
    <div className="px-1.5 py-0.5 rounded text-[7px] font-black tracking-tighter" style={{ backgroundColor: s.bg, color: s.color, border: `1px solid ${s.color}20` }}>
      {s.label}
    </div>
  );
}

function DSBInfluenceDot({ level }: { level: string }) {
  const colors: Record<string, string> = { high: "#EF4444", medium: "#F59E0B", low: "#10B981" };
  return <div className="w-1 h-1 rounded-full" style={{ backgroundColor: colors[level] || "#ccc" }} />;
}

function DSBFactorCard({ factor, onClick }: { factor: any, onClick: () => void }) {
  return (
    <motion.div 
      onClick={onClick}
      whileTap={{ scale: 0.98 }}
      className="p-3 rounded-2xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-all cursor-pointer group flex flex-col gap-2"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <DSBInfluenceDot level={factor.influence_level} />
          <span className="text-[8px] font-black text-white/30 uppercase tracking-widest">
            {DSB_SYSTEM_SHORT[factor.source_system] || "DSB"}
          </span>
        </div>
        <DSBInfluenceBadge level={factor.influence_level} />
      </div>
      <h4 className="text-[13px] font-bold text-white/90 leading-tight group-hover:text-white transition-colors">
        {factor.position}
      </h4>
      <p className="text-[11px] text-white/50 leading-snug line-clamp-2 font-light">
        {factor.core_theme}
      </p>
    </motion.div>
  );
}

function DSBPatternBlock({ pattern }: { pattern: any }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="rounded-2xl bg-gradient-to-br from-violet-500/10 to-transparent border border-violet-500/20 overflow-hidden">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center text-violet-400">
            <Zap size={16} />
          </div>
          <div className="flex flex-col items-start">
            <span className="text-[13px] font-bold text-white/90">{pattern.pattern_name}</span>
            <span className="text-[9px] text-violet-400/60 font-mono tracking-wider">{pattern.formula}</span>
          </div>
        </div>
        <div className="text-white/20">
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }}
            className="px-4 pb-4 overflow-hidden"
          >
            <p className="text-xs text-white/60 leading-relaxed font-light border-t border-white/5 pt-3">
              {pattern.description}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function DSBShadowBlock({ shadow }: { shadow: any }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="rounded-2xl bg-red-500/[0.03] border border-red-500/20 overflow-hidden">
      <button onClick={() => setIsOpen(!isOpen)} className="w-full p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center text-red-400"><AlertCircle size={16} /></div>
          <span className="text-[13px] font-bold text-white/90">{shadow.risk_name}</span>
        </div>
        <div className="text-white/20">{isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</div>
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="px-4 pb-4 overflow-hidden">
            <div className="space-y-3 border-t border-white/5 pt-3">
              <p className="text-xs text-white/60 leading-relaxed font-light">{shadow.description}</p>
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <span className="text-[9px] font-bold text-emerald-400 uppercase tracking-widest block mb-1">Противоядие</span>
                <p className="text-[11px] text-emerald-200/80 font-medium italic">{shadow.antidote}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function DSBDetailSection({ title, children, icon: Icon }: any) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-white/20">
        {Icon && <Icon size={12} />}
        <span className="text-[9px] font-bold uppercase tracking-[0.2em]">{title}</span>
      </div>
      {children}
    </div>
  );
}

function DSBFactorDetail({ factor, onClose }: { factor: any, onClose: () => void }) {
  if (!factor) return null;
  return (
    <motion.div 
      initial={{ opacity: 0, y: 100 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 100 }}
      className="fixed inset-0 z-[200] bg-[#050505] flex flex-col"
    >
      <div className="flex items-center justify-between p-6 border-b border-white/5">
        <div className="flex items-center gap-3">
           <DSBInfluenceBadge level={factor.influence_level} />
           <span className="text-[10px] font-bold text-white/30 tracking-widest">{factor.source_system.toUpperCase()}</span>
        </div>
        <button onClick={onClose} className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-white/40"><ArrowLeft size={20} /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-6 space-y-8 pb-32">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-white tracking-tight">{factor.position}</h2>
          <p className="text-sm text-violet-400/90 font-medium">{factor.core_theme}</p>
        </div>

        <DSBDetailSection title="Энергия и потенциал" icon={Sparkles}>
          <p className="text-sm text-white/80 leading-relaxed font-light">{factor.light_aspect}</p>
        </DSBDetailSection>

        <DSBDetailSection title="Теневая ловушка" icon={AlertCircle}>
          <p className="text-sm text-white/60 leading-relaxed font-light">{factor.shadow_aspect}</p>
        </DSBDetailSection>

        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-white/[0.03] space-y-2 border border-white/5">
            <span className="text-[9px] font-bold text-white/20 uppercase tracking-widest">Задача развития</span>
            <p className="text-xs text-white/80 leading-relaxed font-light">{factor.developmental_task}</p>
          </div>
          <div className="p-4 rounded-2xl bg-white/[0.03] space-y-2 border border-white/5">
            <span className="text-[9px] font-bold text-white/20 uppercase tracking-widest">Ключ интеграции</span>
            <p className="text-xs text-white/80 leading-relaxed font-light">{factor.integration_key}</p>
          </div>
        </div>

        {factor.triggers?.length > 0 && (
          <DSBDetailSection title="Триггеры проявления" icon={Zap}>
            <div className="flex flex-wrap gap-2">
              {factor.triggers.map((t: string, i: number) => (
                <div key={i} className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-[11px] text-white/60">{t}</div>
              ))}
            </div>
          </DSBDetailSection>
        )}
      </div>
      <div className="fixed bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black to-transparent">
        <button onClick={onClose} className="w-full py-4 bg-white text-black font-bold rounded-2xl">Вернуться к сфере</button>
      </div>
    </motion.div>
  );
}

export default function MasterHubView({ userId }: { userId: number }) {
  const [selectedSphere, setSelectedSphere] = useState<string | null>(null);
  const [selectedFactor, setSelectedFactor] = useState<any | null>(null);
  const [subTab, setSubTab] = useState<"personality" | "sides" | "analysis">("personality");
  const [activeTooltip, setActiveTooltip] = useState<{label: string, value: string} | null>(null);
  const { play } = useAudio();
  const { setUser } = useUserStore();
  const [isClaiming, setIsClaiming] = useState(false);

  const { data: hub, isValidating: hubLoading } = useSWR(
    userId ? ["master-hub", userId] : null,
    () => masterHubAPI.get(userId).then(res => res.data).catch(() => null)
  );

  const sphereKeyToNumber = (key: string) => SPHERES_META.findIndex(s => s.key === key) + 1;

  const { data: dsbPortrait, isValidating: dsbLoading } = useSWR(
    selectedSphere && userId ? ["dsb-sphere", userId, selectedSphere] : null,
    () => dsbAPI.getSphere(userId, sphereKeyToNumber(selectedSphere!)).then(res => res.data)
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
            
            {/* ── Energy Claim Notification ── */}
            {hub.energy_claim?.can_claim && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                onClick={async () => {
                  if (isClaiming) return;
                  setIsClaiming(true);
                  play('success');
                  try {
                    const res = await economyAPI.claim(userId);
                    if (res.data.success) {
                      setUser({ energy: res.data.new_energy });
                      // Refresh hub to update claim status
                      mutate(["master-hub", userId]);
                    }
                  } catch (e) {
                    console.error("Claim error", e);
                  } finally {
                    setIsClaiming(false);
                  }
                }}
                className="mx-2 p-4 rounded-2xl bg-gradient-to-r from-amber-500/20 to-amber-600/10 border border-amber-500/30 flex items-center justify-between cursor-pointer active:scale-[0.98] transition-all relative overflow-hidden group shadow-lg shadow-amber-500/5"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-amber-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="flex items-center gap-3 relative z-10">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center text-xl shadow-inner">⚡</div>
                  <div>
                    <p className="text-sm font-bold text-amber-200">Доступна энергия! (+10 ✦)</p>
                    <p className="text-[10px] text-amber-200/50 uppercase font-bold tracking-widest">Нажми чтобы забрать</p>
                  </div>
                </div>
                <div className="relative z-10">
                  {isClaiming ? (
                    <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <motion.div
                      animate={{ x: [0, 5, 0] }}
                      transition={{ repeat: Infinity, duration: 1.5 }}
                      className="text-amber-500/40"
                    >
                      →
                    </motion.div>
                  )}
                </div>
              </motion.div>
            )}

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
          /* ── Sphere Detail View (DSB Expansion) ── */
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

              {dsbLoading && !dsbPortrait ? (
                <div className="px-2 space-y-4">
                  <div className="h-24 bg-white/5 rounded-2xl animate-pulse" />
                  <div className="grid grid-cols-2 gap-3">
                    <div className="h-32 bg-white/5 rounded-2xl animate-pulse" />
                    <div className="h-32 bg-white/5 rounded-2xl animate-pulse" />
                  </div>
                </div>
              ) : (
                <div className="space-y-8 pb-32">
                   {/* 1. Brief Synthesis */}
                   <div className="px-2">
                     <div className="p-4 rounded-3xl bg-white/[0.03] border border-white/5 relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-3 opacity-10"><Sparkles size={40} /></div>
                        <span className="text-[9px] font-bold text-white/20 uppercase tracking-[0.2em] block mb-3">Глубинный синтез</span>
                        <p className="text-sm leading-relaxed text-white/80 font-light italic">
                          «{dsbPortrait?.brief || activeSphereData?.insight || "Глубинный смысл этой сферы раскроется в процессе твоей эволюции."}»
                        </p>
                     </div>
                   </div>

                   {/* 2. Key Factors Layer */}
                   <DSBDetailSection title="Ключевые факторы (Прошивка)" icon={Info}>
                     <div className="grid grid-cols-2 gap-3 px-2">
                        {dsbPortrait?.factors?.sort((a: any, b: any) => INFLUENCE_SORT[b.influence_level] - INFLUENCE_SORT[a.influence_level]).map((f: any) => (
                          <DSBFactorCard key={f.id} factor={f} onClick={() => setSelectedFactor(f)} />
                        ))}
                     </div>
                   </DSBDetailSection>

                   {/* 3. Patterns Layer */}
                   {dsbPortrait?.patterns?.length > 0 && (
                     <DSBDetailSection title="Системные конфигурации" icon={Zap}>
                       <div className="space-y-3 px-2">
                         {dsbPortrait.patterns.map((p: any) => (
                           <DSBPatternBlock key={p.id} pattern={p} />
                         ))}
                       </div>
                     </DSBDetailSection>
                   )}

                   {/* 4. Recommendations Layer */}
                   {dsbPortrait?.recommendations?.length > 0 && (
                     <DSBDetailSection title="Векторы развития" icon={Zap}>
                        <div className="space-y-2 px-2">
                          {dsbPortrait.recommendations.map((r: any) => (
                            <div key={r.id} className="p-4 rounded-2xl bg-emerald-500/[0.03] border border-emerald-500/10 flex gap-3">
                               <div className="mt-1"><ShieldCheck size={14} className="text-emerald-500" /></div>
                               <p className="text-[12px] text-white/80 leading-snug">{r.recommendation}</p>
                            </div>
                          ))}
                        </div>
                     </DSBDetailSection>
                   )}

                   {/* 5. Shadow Audit Layer */}
                   {dsbPortrait?.shadows?.length > 0 && (
                     <DSBDetailSection title="Аудит искажений" icon={AlertCircle}>
                        <div className="space-y-3 px-2">
                           {dsbPortrait.shadows.map((s: any) => (
                             <DSBShadowBlock key={s.id} shadow={s} />
                           ))}
                        </div>
                     </DSBDetailSection>
                   )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {selectedFactor && (
          <DSBFactorDetail factor={selectedFactor} onClose={() => setSelectedFactor(null)} />
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
