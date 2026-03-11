"use client";
import { useState, useEffect, useRef, useCallback } from 'react';

type SoundId = 'click' | 'success' | 'ambient_main' | 'ambient_reflect';

interface AudioState {
    musicEnabled: boolean;
    sfxEnabled: boolean;
}

export function useAudio() {
    const [state, setState] = useState<AudioState>({
        musicEnabled: true,
        sfxEnabled: true,
    });

    const audioRefs = useRef<Record<string, HTMLAudioElement>>({});

    useEffect(() => {
        // Load settings from localStorage
        const saved = localStorage.getItem('avatar_audio_settings');
        if (saved) {
            setState(JSON.parse(saved));
        }

        // Preload sounds
        const sounds: Record<SoundId, string> = {
            click: '/audio/click.mp3',
            success: '/audio/success.mp3',
            ambient_main: '/audio/ambient_main.mp3',
            ambient_reflect: '/audio/ambient_reflect.mp3',
        };

        Object.entries(sounds).forEach(([id, url]) => {
            const audio = new Audio(url);
            if (id.startsWith('ambient')) {
                audio.loop = true;
            }
            audioRefs.current[id] = audio;
        });

        return () => {
            // Clean up
            Object.values(audioRefs.current).forEach(audio => {
                audio.pause();
                audio.src = '';
            });
        };
    }, []);

    const play = useCallback((id: SoundId, volume = 1) => {
        const audio = audioRefs.current[id];
        if (!audio) return;

        const isAmbient = id.startsWith('ambient');
        const enabled = isAmbient ? state.musicEnabled : state.sfxEnabled;

        if (enabled) {
            audio.volume = volume;
            if (!isAmbient) {
                audio.currentTime = 0;
            }
            audio.play().catch(e => console.warn(`Audio play blocked: ${id}`, e));
        }
    }, [state]);

    const stop = useCallback((id: SoundId) => {
        const audio = audioRefs.current[id];
        if (audio) {
            audio.pause();
            if (!id.startsWith('ambient')) {
                audio.currentTime = 0;
            }
        }
    }, []);

    const toggleMusic = () => {
        const newState = { ...state, musicEnabled: !state.musicEnabled };
        setState(newState);
        localStorage.setItem('avatar_audio_settings', JSON.stringify(newState));

        // Stop all ambient sounds if music is disabled
        if (!newState.musicEnabled) {
            Object.keys(audioRefs.current).forEach(id => {
                if (id.startsWith('ambient')) stop(id as SoundId);
            });
        }
    };

    const toggleSfx = () => {
        const newState = { ...state, sfxEnabled: !state.sfxEnabled };
        setState(newState);
        localStorage.setItem('avatar_audio_settings', JSON.stringify(newState));
    };

    return {
        ...state,
        play,
        stop,
        toggleMusic,
        toggleSfx
    };
}
