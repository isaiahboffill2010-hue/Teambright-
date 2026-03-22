import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Campaign, Template } from '@/types';
import { MOCK_CAMPAIGNS, MOCK_TEMPLATES } from '@/lib/mockData';

interface OutreachStore {
  campaigns: Campaign[];
  templates: Template[];
  composerSubject: string;
  composerBody: string;
  selectedRecipientIds: string[];
  selectedTemplateId: string | null;
  isSending: boolean;

  setCampaigns: (c: Campaign[]) => void;
  addCampaign: (c: Campaign) => void;
  setComposerSubject: (v: string) => void;
  setComposerBody: (v: string) => void;
  setRecipients: (ids: string[]) => void;
  setTemplate: (id: string | null) => void;
  setIsSending: (v: boolean) => void;
  resetComposer: () => void;
}

export const useOutreachStore = create<OutreachStore>()(
  devtools(
    (set) => ({
      campaigns: MOCK_CAMPAIGNS,
      templates: MOCK_TEMPLATES,
      composerSubject: '',
      composerBody: '',
      selectedRecipientIds: [],
      selectedTemplateId: null,
      isSending: false,

      setCampaigns: (campaigns) => set({ campaigns }),
      addCampaign: (c) => set((s) => ({ campaigns: [c, ...s.campaigns] })),
      setComposerSubject: (composerSubject) => set({ composerSubject }),
      setComposerBody: (composerBody) => set({ composerBody }),
      setRecipients: (selectedRecipientIds) => set({ selectedRecipientIds }),
      setTemplate: (selectedTemplateId) => set({ selectedTemplateId }),
      setIsSending: (isSending) => set({ isSending }),
      resetComposer: () =>
        set({ composerSubject: '', composerBody: '', selectedRecipientIds: [], selectedTemplateId: null }),
    }),
    { name: 'outreach-store' },
  ),
);
