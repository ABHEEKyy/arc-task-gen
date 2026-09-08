export type Incident = {
  id?: string;
  transcript: string;
  location: string;
  issue: string;
  urgency: 'critical' | 'high' | 'standard';
  owner: string;
  nextStep: string;
  status?: 'open' | 'acknowledged' | 'resolved';
  spokenText?: string;
  createdAt?: string;
};
