"use client";

import { motion } from "framer-motion";
import useSWR from "swr";
import { masterHubAPI } from "@/lib/api";
import { 
  User, Database, MessageCircle, Home, Heart, Clipboard, 
  Link as LinkIcon, Zap, Compass, Award, Users, Moon 
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
  const { data: hub, error, isValidating } = useSWR(
    userId ? ["master-hub", userId] : null,
    () => masterHubAPI.get(userId).then(res => res.data)
  );

  if (isValidating && !hub) {
    return (
      <div className="p-6 flex flex-col gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-24 bg-white/5 rounded-2xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-10 text-center opacity-50">
        <p>Информация о вашем AVATAR еще формируется...</p>
      </div>
    );
  }

  return (
    <div className="px-4 py-2 space-y-4 pb-10">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-4 rounded-3xl bg-white/[0.03] border border-white/[0.05] backdrop-blur-xl"
      >
        <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest mb-2 block">
          Суть Героя
        </span>
        <h2 className="text-xl font-bold text-white mb-2">{hub?.identity?.summary || "Загрузка..."}</h2>
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-violet-500/20 text-violet-300 rounded-full text-[10px] font-bold border border-violet-500/30">
            {hub?.identity?.core_archetype}
          </span>
          <span className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-[10px] font-bold border border-blue-500/30">
            {hub?.identity?.narrative_role}
          </span>
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
              transition={{ delay: idx * 0.05 }}
              className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.04] flex flex-col gap-2"
            >
              <div className="flex items-center gap-2">
                <div 
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${meta.color}20`, color: meta.color }}
                >
                  <Icon size={18} />
                </div>
                <span className="font-bold text-sm text-white/90">{meta.name}</span>
                <span className="ml-auto text-[9px] font-bold text-white/30 uppercase tracking-tighter">
                  {sphereData?.evolution_stage || "Зарождение"}
                </span>
              </div>
              
              <p className="text-xs text-white/60 leading-relaxed">
                {sphereData?.state_description || "Глава вашей истории в этой сфере еще не написана. Проходите сессии рефлексии и синхронизации, чтобы пробудить это знание."}
              </p>
              
              {sphereData?.key_lesson && (
                <div className="mt-2 text-[10px] text-violet-400/80 italic border-l border-violet-500/30 pl-3">
                  Урок: {sphereData.key_lesson}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
