import test from 'node:test';
import assert from 'node:assert/strict';
import { MenuState } from '../assets/scripts/MenuState.ts';

// Catches an incorrect cold-start default; literals come from the approved scope.
test('cold start has best 128 and no resumable session', () => {
    const s = new MenuState();
    assert.deepEqual([s.best, s.sessionId, s.screen, s.dialogOpen], [128, null, 'menu', false]);
});
