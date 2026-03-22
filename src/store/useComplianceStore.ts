import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { ComplianceScore, ComplianceSubmission, SubmissionStatus } from '@/types';
import { MOCK_SUBMISSIONS } from '@/lib/mockData';

interface ComplianceStore {
  // Live scoring
  currentScore: ComplianceScore | null;
  isScoringInProgress: boolean;

  // Submissions
  submissions: ComplianceSubmission[];
  activeSubmissionId: string | null;

  // Multi-step submission wizard
  draftSubject: string;
  draftContent: string;
  draftRecipientIds: string[];
  currentStep: number;

  // Actions
  setScore: (score: ComplianceScore | null) => void;
  setScoringInProgress: (v: boolean) => void;
  setSubmissions: (s: ComplianceSubmission[]) => void;
  addSubmission: (s: ComplianceSubmission) => void;
  updateSubmissionStatus: (id: string, status: SubmissionStatus, notes?: string) => void;
  setActiveSubmission: (id: string | null) => void;
  setDraftSubject: (v: string) => void;
  setDraftContent: (v: string) => void;
  setDraftRecipients: (ids: string[]) => void;
  nextStep: () => void;
  prevStep: () => void;
  resetDraft: () => void;
}

export const useComplianceStore = create<ComplianceStore>()(
  devtools(
    (set) => ({
      currentScore: null,
      isScoringInProgress: false,
      submissions: MOCK_SUBMISSIONS,
      activeSubmissionId: null,
      draftSubject: '',
      draftContent: '',
      draftRecipientIds: [],
      currentStep: 0,

      setScore: (currentScore) => set({ currentScore }),
      setScoringInProgress: (isScoringInProgress) => set({ isScoringInProgress }),
      setSubmissions: (submissions) => set({ submissions }),
      addSubmission: (s) => set((st) => ({ submissions: [s, ...st.submissions] })),
      updateSubmissionStatus: (id, status, officerNotes) =>
        set((st) => ({
          submissions: st.submissions.map((s) =>
            s.id === id
              ? { ...s, status, officerNotes: officerNotes ?? s.officerNotes, reviewedAt: new Date().toISOString() }
              : s,
          ),
        })),
      setActiveSubmission: (id) => set({ activeSubmissionId: id }),
      setDraftSubject: (draftSubject) => set({ draftSubject }),
      setDraftContent: (draftContent) => set({ draftContent }),
      setDraftRecipients: (draftRecipientIds) => set({ draftRecipientIds }),
      nextStep: () => set((s) => ({ currentStep: Math.min(s.currentStep + 1, 3) })),
      prevStep: () => set((s) => ({ currentStep: Math.max(s.currentStep - 1, 0) })),
      resetDraft: () =>
        set({ draftSubject: '', draftContent: '', draftRecipientIds: [], currentStep: 0, currentScore: null }),
    }),
    { name: 'compliance-store' },
  ),
);
