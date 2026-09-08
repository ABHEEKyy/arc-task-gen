export type UrgencyLevel = 'critical' | 'high' | 'standard';
export type IncidentStatus = 'open' | 'acknowledged' | 'resolved';

export type Incident = {
  id?: string;
  transcript: string;
  location: string;
  issue: string;
  urgency: UrgencyLevel;
  owner: string;
  nextStep: string;
  status?: IncidentStatus;
  spokenText?: string;
  createdAt?: string;
  updatedAt?: string;
};

export type ScenarioPreset = {
  id: string;
  badge: string;
  title: string;
  description: string;
  transcript: string;
};
