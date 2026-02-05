export type UserTier = 'FREE' | 'CREATOR' | 'STUDIO' | 'ENTERPRISE';

export interface UserState {
  tier: UserTier;
  balance: number;
  avatar: string;
  name: string;
}
