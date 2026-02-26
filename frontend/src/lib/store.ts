import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UserState {
    userId: number | null;
    tgId: number | null;
    firstName: string;
    token: string | null;
    energy: number;
    streak: number;
    evolutionLevel: number;
    title: string;
    onboardingDone: boolean;
    setUser: (data: Partial<UserState>) => void;
    reset: () => void;
}

export const useUserStore = create<UserState>()(
    persist(
        (set) => ({
            userId: null,
            tgId: null,
            firstName: "",
            token: null,
            energy: 0,
            streak: 0,
            evolutionLevel: 1,
            title: "Искатель",
            onboardingDone: false,
            setUser: (data) => set((state) => ({ ...state, ...data })),
            reset: () => set({
                userId: null, tgId: null, firstName: "", token: null,
                energy: 0, streak: 0, evolutionLevel: 1, title: "Искатель", onboardingDone: false,
            }),
        }),
        { name: "avatar-user" }
    )
);

// Cards state
interface CardsState {
    cards: CardProgress[];
    loading: boolean;
    filterTab: "all" | "recommended" | "active";
    sphereFilter: string;
    setCards: (cards: CardProgress[]) => void;
    updateCard: (cardId: number, updates: Partial<CardProgress>) => void;
    setLoading: (v: boolean) => void;
    setFilters: (tab?: "all" | "recommended" | "active", sphere?: string) => void;
}

export interface CardProgress {
    id: number;
    archetype_id: number;
    sphere: string;
    archetype_name: string;
    sphere_name_ru: string;
    status: string;
    rank: number;
    rank_name: string;
    hawkins_current: number;
    hawkins_peak: number;
    is_recommended_astro: boolean;
    is_recommended_portrait: boolean;
    astro_priority: string | null;
    sync_sessions_count: number;
    align_sessions_count: number;
}

export const useCardsStore = create<CardsState>()(
    persist(
        (set) => ({
            cards: [],
            loading: false,
            filterTab: "all",
            sphereFilter: "ALL",
            setCards: (cards) => set({ cards }),
            updateCard: (cardId, updates) =>
                set((state) => ({
                    cards: state.cards.map((c) =>
                        c.id === cardId ? { ...c, ...updates } : c
                    ),
                })),
            setLoading: (loading) => set({ loading }),
            setFilters: (tab, sphere) => set((state) => ({
                filterTab: tab ?? state.filterTab,
                sphereFilter: sphere ?? state.sphereFilter
            })),
        }),
        { name: "avatar-cards" }
    )
);

// Active sync session state  
interface SyncState {
    sessionId: number | null;
    currentPhase: number;
    phaseContent: string;
    isComplete: boolean;
    cardProgressId: number | null;
    setSyncSession: (data: Partial<SyncState>) => void;
    resetSync: () => void;
}

export const useSyncStore = create<SyncState>()((set) => ({
    sessionId: null,
    currentPhase: 0,
    phaseContent: "",
    isComplete: false,
    cardProgressId: null,
    setSyncSession: (data) => set((state) => ({ ...state, ...data })),
    resetSync: () => set({ sessionId: null, currentPhase: 0, phaseContent: "", isComplete: false, cardProgressId: null }),
}));
