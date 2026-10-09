import test from 'node:test';
import assert from 'node:assert/strict';
import { MenuState } from '../assets/scripts/MenuState.ts';

// Catches an incorrect cold-start default; literals come from the approved scope.
test('cold start has best 128 and no resumable session', () => {
    const s = new MenuState();
    assert.deepEqual([s.best, s.sessionId, s.screen, s.dialogOpen], [128, null, 'menu', false]);
});

test('disabled Continue does not create a session', () => {
    const s = new MenuState();
    assert.equal(s.dispatch('continue'), 'stay');
    assert.deepEqual([s.sessionId, s.screen], [null, 'menu']);
});

test('New game creates a session; Menu and Continue preserve its identity', () => {
    const s = new MenuState();
    s.dispatch('new-game');
    assert.equal(s.screen, 'session');
    assert.equal(s.sessionId, 1);
    s.dispatch('menu');
    assert.equal(s.screen, 'menu');
    s.dispatch('continue');
    assert.equal(s.screen, 'session');
    assert.equal(s.sessionId, 1);
    s.dispatch('menu');
    s.dispatch('new-game');
    assert.equal(s.sessionId, 2);
});

test('reset dialog blocks outside and underlying actions; Cancel preserves state', () => {
    const s = new MenuState();
    s.dispatch('ask-reset');
    assert.equal(s.dialogOpen, true);
    s.dispatch('outside');
    s.dispatch('new-game');
    s.dispatch('continue');
    assert.deepEqual([s.best, s.sessionId, s.screen, s.dialogOpen], [128, null, 'menu', true]);
    s.dispatch('cancel');
    assert.deepEqual([s.best, s.sessionId, s.screen, s.dialogOpen], [128, null, 'menu', false]);
});

test('confirmed reset clears best without creating a session', () => {
    const s = new MenuState();
    s.dispatch('ask-reset');
    s.dispatch('reset');
    assert.deepEqual([s.best, s.sessionId, s.screen, s.dialogOpen], [0, null, 'menu', false]);
    s.dispatch('continue');
    assert.equal(s.sessionId, null);
    s.dispatch('new-game');
    assert.deepEqual([s.best, s.sessionId, s.screen], [0, 1, 'session']);
});

test('confirmed reset preserves an existing session through Continue and Menu', () => {
    const s = new MenuState();
    s.dispatch('new-game');
    s.dispatch('menu');
    s.dispatch('ask-reset');
    s.dispatch('reset');
    assert.deepEqual([s.best, s.sessionId, s.screen, s.dialogOpen], [0, 1, 'menu', false]);
    s.dispatch('continue');
    assert.deepEqual([s.best, s.sessionId, s.screen], [0, 1, 'session']);
    s.dispatch('menu');
    s.dispatch('ask-reset');
    s.dispatch('cancel');
    assert.deepEqual([s.best, s.sessionId, s.screen, s.dialogOpen], [0, 1, 'menu', false]);
});

test('Back closes dialog, returns from session, then requests native leave at root', () => {
    const s = new MenuState();
    s.dispatch('new-game');
    assert.equal(s.dispatch('back'), 'stay');
    assert.deepEqual([s.sessionId, s.screen], [1, 'menu']);
    s.dispatch('ask-reset');
    assert.equal(s.dispatch('back'), 'stay');
    assert.deepEqual([s.best, s.sessionId, s.dialogOpen], [128, 1, false]);
    assert.equal(s.dispatch('back'), 'leave');
    assert.deepEqual([s.best, s.sessionId, s.screen], [128, 1, 'menu']);
});

test('zero best survives dialog cancellation and Back with and without a session', () => {
    for (const hasSession of [false, true]) {
        const s = new MenuState();
        if (hasSession) { s.dispatch('new-game'); s.dispatch('menu'); }
        s.dispatch('ask-reset'); s.dispatch('reset');
        s.dispatch('ask-reset'); s.dispatch('back');
        assert.deepEqual([s.best, s.sessionId, s.screen, s.dialogOpen], [0, hasSession ? 1 : null, 'menu', false]);
        s.dispatch('ask-reset'); s.dispatch('cancel');
        assert.equal(s.best, 0);
    }
});
