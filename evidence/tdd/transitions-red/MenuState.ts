export type MenuAction = 'new-game' | 'continue' | 'menu' | 'ask-reset' | 'cancel' | 'reset' | 'back' | 'outside';

export class MenuState {
    best = 128;
    sessionId: number | null = null;
    screen: 'menu' | 'session' = 'menu';
    dialogOpen = false;

    dispatch(_action: MenuAction): 'stay' | 'leave' { return 'stay'; }
}
