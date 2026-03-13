import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useSWR from "swr";
import { masterHubAPI, profileAPI } from "@/lib/api";
import { 
  User, Database, MessageCircle, Home, Heart, Clipboard, 
  Link as LinkIcon, Zap, Compass, Award, Users, Moon, ArrowLeft
} from "lucide-react";

const ICON_MAP: Record<string, any> = {
  user: User,
  database: Database,
  "message-circle": MessageCircle,
  home: Home,
  heart: Heart,
  clipboard: Clipboard,
  link: LinkIcon,
  zap: Zap,
  compass: Compass,
  award: Award,
  users: Users,
  moon: Moon,
};

const SPHERES_META = [
  { key: "IDENTITY", icon: "user", name: "Личность", color: "#F59E0B" },
  { key: "RESOURCES", icon: "database", name: "Ресурсы", color: "#10B981" },
  { key: "COMMUNICATION", icon: "message-circle", name: "Связи", color: "#06B6D4" },
  { key: "ROOTS", icon: "home", name: "Корни", color: "#F97316" },
  { key: "CREATIVITY", icon: "heart", name: "Творчество", color: "#EC4899" },
  { key: "SERVICE", icon: "clipboard", name: "Служение", color: "#14B8A6" },
  { key: "PARTNERSHIP", icon: "link", name: "Партнерство", color: "#3B82F6" },
  { key: "TRANSFORMATION", icon: "zap", name: "Тень", color: "#6366F1" },
  { key: "EXPANSION", icon: "compass", name: "Поиск", color: "#8B5CF6" },
  { key: "STATUS", icon: "award", name: "Статус", color: "#EF4444" },
  { key: "VISION", icon: "users", name: "Будущее", color: "#D946EF" },
  { key: "SPIRIT", icon: "moon", name: "Дух", color: "#64748B" },
];

export default function MasterHubView({ userId }: { userId: number }) {
  const [selectedSphere, setSelectedSphere] = useState<string | null>(null);

  const { data: hub, error: hubError, isValidating: hubLoading } = useSWR(
    userId ? ["master-hub", userId] : null,
    () => masterHubAPI.get(userId).then(res => res.data).catch(() => null)
  );

  const { data: profile } = useSWR(
    userId ? ["profile", userId] : null,
    () => profileAPI.get(userId).then(res => res.data)
  );

  if ((hubLoading && !hub) || (!profile && !hub)) {
    return (
      <div className="p-6 flex flex-col gap-4">
        {[...Array(12)].map((_, i) => (
          <div key={i} className="h-24 bg-white/5 rounded-2xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (hubError && !profile) {
    return (
      <div className="p-10 text-center opacity-50">
        <p>Информация о вашем AVATAR еще формируется...</p>
      </div>
    );
  }

  const identitySummary = hub?.identity?.summary 
    || "Глубинная суть вашего AVATAR формируется... Пройдите онбординг или первую сессию, чтобы пробудить Океан.";

  const activeSphereMeta = SPHERES_META.find(s => s.key === selectedSphere);
  const activeSphereData = selectedSphere ? hub?.spheres?.[selectedSphere] : null;

  return (
    <div className="px-4 py-2 space-y-4 pb-10 relative">
      <AnimatePresence>
        {!selectedSphere ? (
          <motion.div
            key="list"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-4"
          >
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-5 rounded-3xl bg-white/[0.03] border border-white/[0.05] backdrop-blur-xl shadow-2xl relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-violet-500/10 blur-3xl -z-10" />
              <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest mb-3 block">
                Суть Героя (The Ocean)
              </span>
              <p className="text-sm font-medium text-white/90 mb-3 leading-relaxed">
                {identitySummary}
              </p>
              
              <div className="flex flex-wrap gap-2">
                {hub?.identity?.core_archetype && (
                  <span className="px-3 py-1 bg-violet-500/20 text-violet-300 rounded-full text-[10px] font-bold border border-violet-500/30">
                    {hub.identity.core_archetype}
                  </span>
                )}
                {hub?.identity?.narrative_role && (
                  <span className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-[10px] font-bold border border-blue-500/30">
                    {hub.identity.narrative_role}
                  </span>
                )}
                {hub?.identity?.energy_description && (
                  <span className="px-3 py-1 bg-emerald-500/10 text-emerald-300/70 rounded-full text-[9px] font-medium border border-emerald-500/20">
                    {hub.identity.energy_description}
                  </span>
                )}
              </div>
            </motion.div>

            <div className="grid grid-cols-1 gap-3">
              {SPHERES_META.map((meta, idx) => {
                const sphereData = hub?.spheres?.[meta.key];
                const Icon = ICON_MAP[meta.icon] || User;
                
                return (
                  <motion.div
                    key={meta.key}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    onClick={() => setSelectedSphere(meta.key)}
                    className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.04] flex flex-col gap-2 relative overflow-hidden active:scale-95 transition-transform cursor-pointer hover:bg-white/[0.04]"
                  >
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: `${meta.color}20`, color: meta.color }}
                      >
                        <Icon size={18} />
                      </div>
                      <span className="font-bold text-sm text-white/90">{meta.name}</span>
                      {sphereData?.evolution_stage && (
                        <span className="ml-auto text-[9px] font-bold text-white/30 uppercase tracking-tighter">
                          {sphereData.evolution_stage}
                        </span>
                      )}
                    </div>
                    
                    <p className="text-xs text-white/60 leading-relaxed font-light line-clamp-2">
                      {sphereData?.state_description || "Глава истории еще не синтезирована..."}
                    </p>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="detail"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="space-y-6 pt-2"
          >
            <button 
              onClick={() => setSelectedSphere(null)}
              className="flex items-center gap-2 text-white/40 hover:text-white transition-colors text-xs font-bold uppercase tracking-widest"
            >
              <ArrowLeft size={16} /> Назад в Хаб
            </button>

            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div 
                  className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg"
                  style={{ 
                    backgroundColor: `${activeSphereMeta?.color}20`, 
                    color: activeSphereMeta?.color,
                    border: `1px solid ${activeSphereMeta?.color}40`
                  }}
                >
                  {activeSphereMeta && (() => {
                    const Icon = ICON_MAP[activeSphereMeta.icon];
                    return <Icon size={28} />;
                  })()}
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white">
                    {activeSphereMeta?.name}
                  </h1>
                  <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest">
                    {activeSphereData?.evolution_stage || "Стадия не определена"}
                  </p>
                </div>
              </div>

              <div className="p-6 rounded-3xl bg-white/[0.03] border border-white/[0.05] relative overflow-hidden min-h-[300px]">
                 <div 
                  className="absolute -top-24 -right-24 w-64 h-64 blur-[100px] -z-10 opacity-20"
                  style={{ backgroundColor: activeSphereMeta?.color }}
                 />
                 
                 <p className="text-sm leading-relaxed text-white/80 whitespace-pre-wrap font-light first-letter:text-3xl first-letter:font-serif first-letter:mr-2 first-letter:float-left">
                   {activeSphereData?.state_description || "В этой главе пока только тишина. Проходите сессии синхронизации, чтобы пробудить этот аспект своего AVATAR."}
                 </p>

                 {activeSphereData?.key_lesson && (
                   <div className="mt-10 p-4 rounded-xl bg-violet-500/10 border border-violet-500/20 italic text-violet-300/90 text-xs text-center">
                     <span className="block text-[9px] font-bold uppercase tracking-[0.2em] mb-1 opacity-50 not-italic">Вызов и Урок</span>
                     «{activeSphereData.key_lesson}»
                   </div>
                 )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
