import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ProjectDetail } from '@/services/projects'

interface ProjectState {
    currentProject: ProjectDetail | null
    setCurrentProject: (project: ProjectDetail | null) => void
}

export const useProjectStore = create<ProjectState>()(
    persist(
        (set) => ({
            currentProject: null,
            setCurrentProject: (project) => set({ currentProject: project }),
        }),
        { name: 'csvs-project' },
    ),
)
