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
}

export function obtenerDashboard(): Promise<DatosDashboard> {
  return get<DatosDashboard>('/dashboard');
}
