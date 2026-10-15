import { Button, director, Director, Graphics, Label, native, Node, profiler, Sprite, sys, UITransform, UIOpacity, view } from 'cc';
import { DEBUG, NATIVE } from 'cc/env';
import type { MenuState } from './MenuState';

// Debug-only, one-way observations after an actual drawn frame. No state-setting endpoint.
export class RuntimeObservation {
    private frame = 0;
    private lastSaved = 0;
    viewport: unknown = null;
    constructor(private root: Node, private state: MenuState, private tokensId: string) {}

    start(): void {
        if (DEBUG && NATIVE) director.on(Director.EVENT_AFTER_DRAW, this.capture, this);
    }
    stop(): void { director.off(Director.EVENT_AFTER_DRAW, this.capture, this); }

    private capture(): void {
        ++this.frame;
        if (Date.now() - this.lastSaved < 200) return;
        this.lastSaved = Date.now();
        const size = view.getVisibleSize();
        const nodes: unknown[] = [];
        const visit = (node: Node, parentPath: string, parentOpacity: number): void => {
            if (!node.activeInHierarchy) return;
            const path = parentPath + '/' + node.name;
            const opacity = parentOpacity * (node.getComponent(UIOpacity)?.opacity ?? 255) / 255;
            const ui = node.getComponent(UITransform);
            const label = node.getComponent(Label);
            const sprite = node.getComponent(Sprite);
            const button = node.getComponent(Button);
            const graphics = node.getComponent(Graphics);
            if (ui) {
                const r = ui.getBoundingBoxToWorld();
                nodes.push({ path, name: node.name, uuid: node.uuid, opacity,
                    rect: { x: r.x, y: size.height - r.y - r.height, width: r.width, height: r.height },
                    label: label ? { text: label.string, fontSize: label.fontSize, lineHeight: label.lineHeight,
                        fontFamily: label.fontFamily, bold: label.isBold, overflow: label.overflow,
                        color: label.color.toHEX('#rrggbb') } : null,
                    graphics: graphics ? { fill: graphics.fillColor.toHEX('#rrggbbaa') } : null,
                    sprite: sprite ? { uuid: sprite.spriteFrame?.uuid, type: sprite.type, color: sprite.color.toHEX('#rrggbbaa'),
                        insets: sprite.spriteFrame ? [sprite.spriteFrame.insetLeft, sprite.spriteFrame.insetTop,
                            sprite.spriteFrame.insetRight, sprite.spriteFrame.insetBottom] : null,
                        original: sprite.spriteFrame?.originalSize } : null,
                    button: button ? { enabled: button.enabled, interactable: button.interactable } : null });
            }
            for (const child of node.children) visit(child, path, opacity);
        };
        visit(this.root, '', 1);
        native.bridge.sendToNative('observation', JSON.stringify({
            capturedAt: Date.now(), frame: this.frame, scene: director.getScene()?.name,
            sceneUuid: director.getScene()?.uuid,
            state: { best: this.state.best, sessionId: this.state.sessionId,
                screen: this.state.screen, dialogOpen: this.state.dialogOpen },
            viewport: this.viewport, visible: size, frameSize: view.getFrameSize(),
            scale: { x: view.getScaleX(), y: view.getScaleY() },
            safeArea: sys.getSafeAreaRect(false), tokensUuid: this.tokensId,
            profilerVisible: profiler.isShowingStats(), nodes,
        }));
    }
}
