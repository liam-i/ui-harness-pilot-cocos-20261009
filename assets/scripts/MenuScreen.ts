import { _decorator, BlockInputEvents, Button, Canvas, Color, Component, EventTouch, Graphics,
    JsonAsset, Label, Layers, native, Node, profiler, resources, ResolutionPolicy, Sprite, SpriteFrame,
    UITransform, UIOpacity, view } from 'cc';
import { NATIVE } from 'cc/env';
import { MenuState } from './MenuState';
import type { MenuAction } from './MenuState';
import { RuntimeObservation } from './RuntimeObservation';

const { ccclass } = _decorator;

@ccclass('MenuScreen')
export class MenuScreen extends Component {
    private state = new MenuState();
    private tokens: any;
    private primary!: SpriteFrame;
    private secondary!: SpriteFrame;
    private content: Node | null = null;
    private observer: RuntimeObservation | null = null;
    private height = 667;

    async start(): Promise<void> {
        try {
            profiler.hideStats();
            const load = <T>(path: string, type: any): Promise<T> => new Promise((resolve, reject) => {
                resources.load(path, type, (error, asset) => error ? reject(error) : resolve(asset as T));
            });
            const [tokens, primary, secondary] = await Promise.all([
                load<JsonAsset>('ui/menu/tokens', JsonAsset),
                load<SpriteFrame>('ui/menu/menu-primary/spriteFrame', SpriteFrame),
                load<SpriteFrame>('ui/menu/menu-secondary/spriteFrame', SpriteFrame),
            ]);
            this.tokens = tokens.json;
            this.primary = primary; this.secondary = secondary;
            for (const frame of [primary, secondary]) {
                frame.insetTop = frame.insetBottom = frame.insetLeft = frame.insetRight = this.tokens.layout.sourceSlicePx;
            }
            view.setDesignResolutionSize(375, 667, ResolutionPolicy.FIXED_WIDTH);
            this.height = view.getVisibleSize().height;
            this.node.getComponent(UITransform)!.setContentSize(375, this.height);
            this.node.setPosition(187.5, this.height / 2, 0);
            this.node.getComponent(Canvas)!.alignCanvasWithScreen = true;
            this.observer = new RuntimeObservation(this.node, this.state, tokens.uuid);
            if (NATIVE) {
                native.bridge.onNative = (event: string, value: string): void => {
                    if (event === 'back') this.act('back');
                    if (event === 'viewport' && this.observer) this.observer.viewport = JSON.parse(value);
                };
            }
            this.render();
            this.observer.start();
            if (NATIVE) native.bridge.sendToNative('ready');
        } catch (error) {
            console.error('MENU_RESOURCE_OR_SCENE_FAILURE', error);
            if (NATIVE) native.bridge.sendToNative('failure', String(error));
        }
    }

    onDestroy(): void { this.observer?.stop(); }

    private act(action: MenuAction): void {
        const before = JSON.stringify([this.state.best, this.state.sessionId, this.state.screen, this.state.dialogOpen]);
        const result = this.state.dispatch(action);
        if (result === 'leave') { if (NATIVE) native.bridge.sendToNative('leave'); return; }
        if (before !== JSON.stringify([this.state.best, this.state.sessionId, this.state.screen, this.state.dialogOpen])) this.render();
    }

    private box(parent: Node, name: string, x: number, top: number, width: number, height: number): Node {
        const node = new Node(name); node.layer = Layers.Enum.UI_2D; parent.addChild(node);
        const ui = node.addComponent(UITransform); ui.setContentSize(width, height);
        // All boxes use the Canvas coordinate space; descendants are positioned explicitly below.
        node.setPosition(x + width / 2 - 187.5, this.height / 2 - top - height / 2, 0);
        return node;
    }

    private round(parent: Node, name: string, x: number, top: number, w: number, h: number,
        radius: number, color: string, border?: string, alpha = 255): Node {
        const node = this.box(parent, name, x, top, w, h);
        const g = node.addComponent(Graphics); const fill = new Color(color); fill.a = alpha; g.fillColor = fill;
        const inset = border ? 0.5 : 0;
        g.roundRect(-w / 2 + inset, -h / 2 + inset, w - inset * 2, h - inset * 2, radius);
        g.fill();
        if (border) { g.lineWidth = 1; g.strokeColor = new Color(border); g.stroke(); }
        return node;
    }

    private text(parent: Node, name: string, copy: string, x: number, top: number,
        w: number, h: number, size: number, color: string, bold = false, tracking = 0): Node {
        const node = this.box(parent, name, x, top, w, h);
        const addLabel = (owner: Node, value: string): Label => {
            const label = owner.addComponent(Label); label.string = value; label.fontFamily = 'sans-serif';
            label.useSystemFont = true; label.fontSize = size; label.lineHeight = h;
            label.color = new Color(color); label.isBold = bold;
            label.horizontalAlign = Label.HorizontalAlign.CENTER; label.verticalAlign = Label.VerticalAlign.CENTER;
            label.enableWrapText = false; label.overflow = Label.Overflow.CLAMP;
            return label;
        };
        if (!tracking) { addLabel(node, copy); return node; }
        // System Label spacingX is BMFont-only in 3.8.8. Lay out measured system glyphs instead.
        const glyphs = Array.from(copy).map((ch, i) => {
            const glyph = new Node('glyph-' + i); glyph.layer = Layers.Enum.UI_2D; node.addChild(glyph);
            glyph.addComponent(UITransform).setContentSize(size * 2, h);
            const label = addLabel(glyph, ch); label.overflow = Label.Overflow.NONE; label.updateRenderData(true);
            return { glyph, width: glyph.getComponent(UITransform)!.width };
        });
        const width = glyphs.reduce((sum, entry) => sum + entry.width, 0) + tracking * (glyphs.length - 1);
        let cursor = -width / 2;
        for (const entry of glyphs) { entry.glyph.setPosition(cursor + entry.width / 2, 0, 0); cursor += entry.width + tracking; }
        return node;
    }

    private button(parent: Node, name: string, copy: string, action: MenuAction,
        x: number, top: number, w: number, h: number, kind: 'primary' | 'secondary' | 'quiet',
        size: number, enabled = true): Node {
        const node = this.box(parent, name, x, top, w, h);
        const visual = new Node('visual'); visual.layer = Layers.Enum.UI_2D; node.addChild(visual);
        visual.addComponent(UITransform).setContentSize(w, h);
        if (kind !== 'quiet') {
            const art = new Node('sprite'); art.layer = Layers.Enum.UI_2D; visual.addChild(art);
            // Source border 32 pixels -> displayed border 16 UI units, without altering PNG bytes.
            art.addComponent(UITransform).setContentSize(w * 2, h * 2); art.setScale(0.5, 0.5, 1);
            const sprite = art.addComponent(Sprite); sprite.type = Sprite.Type.SLICED;
            sprite.sizeMode = Sprite.SizeMode.CUSTOM; sprite.trim = false;
            sprite.spriteFrame = kind === 'primary' ? this.primary : this.secondary;
        }
        const labelNode = new Node('label'); labelNode.layer = Layers.Enum.UI_2D; visual.addChild(labelNode);
        labelNode.addComponent(UITransform).setContentSize(w - 32, h);
        const label = labelNode.addComponent(Label); label.string = copy; label.fontFamily = 'sans-serif';
        label.fontSize = size; label.lineHeight = h; label.isBold = true;
        label.color = new Color(kind === 'quiet' ? this.tokens.colors.muted : this.tokens.colors.ink);
        label.horizontalAlign = Label.HorizontalAlign.CENTER; label.verticalAlign = Label.VerticalAlign.CENTER;
        label.enableWrapText = false; label.overflow = Label.Overflow.CLAMP;
        if (kind === 'quiet') { label.isUnderline = true; label.underlineHeight = 1; }
        if (name === 'new-game') {
            label.string = 'New game';
            const arrow = new Node('arrow'); arrow.layer = Layers.Enum.UI_2D; visual.addChild(arrow);
            arrow.addComponent(UITransform).setContentSize(24, h);
            arrow.setPosition(w / 2 - (this.tokens.layout.displaySliceUnits + 13 + size / 2), 0, 0);
            const a = arrow.addComponent(Label); a.string = '→'; a.fontSize = size; a.lineHeight = h;
            a.isBold = true; a.color = new Color(this.tokens.colors.ink); a.overflow = Label.Overflow.CLAMP;
            a.horizontalAlign = Label.HorizontalAlign.CENTER; a.verticalAlign = Label.VerticalAlign.CENTER;
        }
        const button = node.addComponent(Button); button.transition = Button.Transition.NONE; button.interactable = enabled;
        if (!enabled) node.addComponent(UIOpacity).opacity = Math.round(255 * this.tokens.states.disabledOpacity);
        node.on(Node.EventType.TOUCH_START, () => { if (button.interactable) visual.setPosition(0, -this.tokens.states.pressedTranslateY, 0); });
        const release = (): void => { visual.setPosition(0, 0, 0); };
        node.on(Node.EventType.TOUCH_END, release); node.on(Node.EventType.TOUCH_CANCEL, release);
        node.on(Button.EventType.CLICK, () => this.act(action));
        return node;
    }

    private render(): void {
        if (this.content) { this.content.active = false; this.content.destroy(); }
        const root = this.content = new Node('Content'); root.layer = Layers.Enum.UI_2D; this.node.addChild(root);
        const c = this.tokens.colors, f = this.tokens.font.sizes, l = this.tokens.layout;
        const compact = this.height <= l.compactMaxHeight, top = compact ? l.topCompact : l.topRegular;
        const width = Math.min(l.contentMaxWidth, 375 - l.sideInset * 2), left = (375 - width) / 2;
        this.round(root, 'background', 0, 0, 375, this.height, 0, c.background);
        if (this.state.screen === 'menu') {
            this.text(root, 'eyebrow', 'A LITTLE EVERY DAY', left, top, width, 13.125, f.eyebrow, c.muted, true, 2.5);
            const titleTop = top + 30.125;
            this.text(root, 'title', '2048', left, titleTop, width, 92, f.title, c.ink, true, -6);
            this.text(root, 'spark', '✦', 275, titleTop - 3, 22, 22, 22, '#d69c22');
            this.text(root, 'tagline', 'Make room for your next move.', left, titleTop + 106, width, 24, f.tagline, c.muted);
            const scoreTop = titleTop + 154;
            this.round(root, 'score-card', 130.5, scoreTop, 114, 75.5, 16, c.card, c.border);
            this.text(root, 'score-caption', 'YOUR BEST', 143.5, scoreTop + 12.625, 88, 11.25, f.scoreCaption, c.muted, true, 1.4);
            this.text(root, 'best', String(this.state.best), 143.5, scoreTop + 26.875, 88, 36, f.score, c.ink, true);
            const navTop = scoreTop + 75.5 + (compact ? l.scoreGapCompact : l.scoreGapRegular);
            this.button(root, 'continue', 'Continue', 'continue', left, navTop, width, l.mainButtonHeight, 'secondary', f.button, this.state.sessionId !== null);
            this.button(root, 'new-game', 'New game', 'new-game', left, navTop + 80, width, l.mainButtonHeight, 'primary', f.button);
            this.button(root, 'reset-best', 'Reset best score', 'ask-reset', left, navTop + 160, width, l.quietButtonHeight, 'quiet', f.quietButton);
            this.text(root, 'footer', 'Swipe. Combine. Keep going.', left, this.height - l.bottomInset - 16.8, width, 16.8, f.footer, c.footer);
        } else {
            this.text(root, 'eyebrow', 'YOUR NEXT MOVE', left, top, width, 13.125, f.eyebrow, c.muted, true, 2.5);
            this.text(root, 'session-title', 'Let’s begin.', left, top + 29.125, width, 31.875, f.heading, c.ink, true, -0.5);
            const boardTop = top + 99;
            this.round(root, 'board', 77.5, boardTop, 220, 210, 18, c.border);
            for (let i = 0; i < 4; i++) {
                const x = 89.5 + i % 2 * 103, y = boardTop + 12 + Math.floor(i / 2) * 98;
                this.round(root, 'tile-' + i, x, y, 93, 88, 8, '#f5efdf');
                if (i < 2) this.text(root, 'tile-value-' + i, '2', x, y, 93, 88, f.boardTile, c.ink, true);
            }
            this.text(root, 'session-copy', 'Session started.', left, boardTop + 232, width, 24, f.tagline, c.muted);
            this.button(root, 'menu-back', 'Menu', 'menu', left, boardTop + 280, width, l.mainButtonHeight, 'secondary', f.button);
            this.text(root, 'footer', 'Every move is a new beginning.', left, this.height - l.bottomInset - 16.8, width, 16.8, f.footer, c.footer);
        }
        if (this.state.dialogOpen) this.dialog(root);
    }

    private dialog(root: Node): void {
        const c = this.tokens.colors, f = this.tokens.font.sizes, l = this.tokens.layout;
        const shade = this.round(root, 'modal-backdrop', 0, 0, 375, this.height, 0, c.ink,
            undefined, Math.round(255 * this.tokens.states.modalBackdropOpacity));
        shade.addComponent(BlockInputEvents);
        const w = Math.min(l.dialogWidth, 375 - l.sideInset * 2), h = 297.125;
        const left = (375 - w) / 2, top = (this.height - h) / 2;
        const panel = this.round(root, 'dialog-panel', left, top, w, h, 24, c.card, c.border);
        panel.addComponent(BlockInputEvents);
        this.round(root, 'dialog-mark', 163.5, top + 28.625, 48, 48, 24, c.dialogMark);
        this.text(root, 'dialog-mark-label', '↺', 163.5, top + 28.625, 48, 48, 28, c.ink);
        this.text(root, 'reset-title', 'A fresh start?', left + 20.625, top + 92.625, w - 41.25, 31.875, f.heading, c.ink, true, -0.5);
        this.text(root, 'reset-explanation', 'Your best score will return to zero.', left + 20.625, top + 140.5, w - 41.25, 24, f.dialogCopy, c.muted);
        this.text(root, 'reset-detail', this.state.sessionId === null ? 'You can start a new session next.' : 'Your session will stay available.',
            left + 20.625, top + 164.5, w - 41.25, 24, f.dialogCopy, c.muted);
        const bw = (w - 41.25 - l.dialogButtonGap) / 2;
        this.button(root, 'cancel', 'Cancel', 'cancel', left + 20.625, top + 212.5, bw, l.mainButtonHeight, 'secondary', f.dialogButton);
        this.button(root, 'confirm-reset', 'Reset', 'reset', left + 20.625 + bw + l.dialogButtonGap, top + 212.5, bw, l.mainButtonHeight, 'primary', f.dialogButton);
    }
}
