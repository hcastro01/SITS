import { get } from './client';

export interface DatosDashboard {
  generatedAt: string;
  casesOpen?: number;
  casesClosed?: number;
  casesPending?: number;
  upcomingFollowUps?: number;
  overdueCommitments?: number;
  pendingNews?: number;
  toursCompleted?: number;
  pendingCases?: DashboardItem[];
  upcomingFollowUpItems?: DashboardItem[];
  overdueCommitmentItems?: DashboardItem[];
}

export interface DashboardItem {
  caseId: string;
  caseCode: string;
  date: string | null;
  description?: string | null;
  owner?: string | null;
  status?: string | null;
  priority?: string | null;
}

export function obtenerDashboard(): Promise<DatosDashboard> {
  return get<DatosDashboard>('/dashboard');
}
