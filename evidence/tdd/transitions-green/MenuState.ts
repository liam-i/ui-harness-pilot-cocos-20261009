export type MenuAction = 'new-game' | 'continue' | 'menu' | 'ask-reset' | 'cancel' | 'reset' | 'back' | 'outside';

export class MenuState {
    best = 128;
    sessionId: number | null = null;
    screen: 'menu' | 'session' = 'menu';
    dialogOpen = false;
    private nextSessionId = 1;

    dispatch(action: MenuAction): 'stay' | 'leave' {
        if (this.dialogOpen) {
            if (action === 'reset') {
                this.best = 0;
                this.dialogOpen = false;
            } else if (action === 'cancel' || action === 'back') {
                this.dialogOpen = false;
            }
            return 'stay';
        }
        if (action === 'back') {
            if (this.screen === 'session') { this.screen = 'menu'; return 'stay'; }
            return 'leave';
        }
        if (this.screen === 'session') {
            if (action === 'menu') this.screen = 'menu';
            return 'stay';
        }
        if (action === 'new-game') {
            this.sessionId = this.nextSessionId++;
            this.screen = 'session';
        } else if (action === 'continue' && this.sessionId !== null) {
            this.screen = 'session';
        } else if (action === 'ask-reset') {
            this.dialogOpen = true;
        }
        return 'stay';
    }
}
