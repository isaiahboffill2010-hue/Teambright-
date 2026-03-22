import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Prospect, ProspectStatus } from '@/types';
import { MOCK_PROSPECTS } from '@/lib/mockData';

interface Filters {
  search: string;
  status: ProspectStatus | 'all';
  tags: string[];
}

interface ProspectStore {
  prospects: Prospect[];
  selectedIds: Set<string>;
  filters: Filters;
  isLoading: boolean;
  activeProspectId: string | null;

  // Actions
  setProspects: (p: Prospect[]) => void;
  addProspect: (p: Prospect) => void;
  updateProspect: (id: string, patch: Partial<Prospect>) => void;
  deleteProspect: (id: string) => void;
  toggleSelect: (id: string) => void;
  selectAll: () => void;
  clearSelection: () => void;
  setFilters: (f: Partial<Filters>) => void;
  setActiveProspect: (id: string | null) => void;
  setLoading: (v: boolean) => void;

  // Derived
  filteredProspects: () => Prospect[];
}

export const useProspectStore = create<ProspectStore>()(
  devtools(
    (set, get) => ({
      prospects: MOCK_PROSPECTS,
      selectedIds: new Set<string>(),
      filters: { search: '', status: 'all', tags: [] },
      isLoading: false,
      activeProspectId: null,

      setProspects: (prospects) => set({ prospects }),
      addProspect: (p) => set((s) => ({ prospects: [p, ...s.prospects] })),
      updateProspect: (id, patch) =>
        set((s) => ({
          prospects: s.prospects.map((p) =>
            p.id === id ? { ...p, ...patch, updatedAt: new Date().toISOString() } : p,
          ),
        })),
      deleteProspect: (id) =>
        set((s) => ({ prospects: s.prospects.filter((p) => p.id !== id) })),
      toggleSelect: (id) =>
        set((s) => {
          const next = new Set(s.selectedIds);
          if (next.has(id)) { next.delete(id); } else { next.add(id); }
          return { selectedIds: next };
        }),
      selectAll: () =>
        set((s) => ({ selectedIds: new Set(s.prospects.map((p) => p.id)) })),
      clearSelection: () => set({ selectedIds: new Set<string>() }),
      setFilters: (f) => set((s) => ({ filters: { ...s.filters, ...f } })),
      setActiveProspect: (id) => set({ activeProspectId: id }),
      setLoading: (v) => set({ isLoading: v }),

      filteredProspects: () => {
        const { prospects, filters } = get();
        return prospects.filter((p) => {
          const q = filters.search.toLowerCase();
          const matchSearch =
            !q ||
            `${p.firstName} ${p.lastName} ${p.email} ${p.enrichment?.companyName ?? ''}`
              .toLowerCase()
              .includes(q);
          const matchStatus = filters.status === 'all' || p.status === filters.status;
          const matchTags =
            filters.tags.length === 0 ||
            filters.tags.every((t) => p.tags.includes(t));
          return matchSearch && matchStatus && matchTags;
        });
      },
    }),
    { name: 'prospect-store' },
  ),
);
