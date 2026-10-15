package com.cocos.game;

import android.app.Activity;
import android.content.pm.ApplicationInfo;
import android.os.Build;
import android.os.SystemClock;
import android.graphics.Insets;
import android.util.AtomicFile;
import android.util.Log;
import android.view.View;
import android.view.WindowInsets;
import com.cocos.lib.CocosHelper;
import com.cocos.lib.JsbBridge;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

// Routes real Activity events. Debug observations have no inbound test command or state setter.
public final class HarnessObservation {
    private static Activity activity;
    private static boolean ready;
    private static long backCount;
    private static long lastBack;
    private static String geometry = "{}";

    public static void attach(Activity owner) {
        activity = owner;
        ready = false;
        JsbBridge.setCallback((event, value) -> {
            if ("ready".equals(event)) { ready = true; viewport(); }
            else if ("leave".equals(event)) owner.runOnUiThread(() -> owner.moveTaskToBack(true));
            else if ("observation".equals(event)) save(owner, value);
            else if ("failure".equals(event)) Log.e("HarnessMenu", value);
        });
    }

    public static void detach(Activity owner) {
        if (activity == owner) { ready = false; activity = null; JsbBridge.setCallback(null); }
    }

    public static void back() {
        if (!ready || activity == null) return;
        long now = SystemClock.uptimeMillis();
        if (now - lastBack < 150) return;
        lastBack = now; backCount++;
        CocosHelper.runOnGameThread(() -> JsbBridge.sendToScript("back"));
    }

    public static void viewport() {
        Activity owner = activity;
        if (!ready || owner == null) return;
        owner.runOnUiThread(() -> {
            View decor = owner.getWindow().getDecorView();
            decor.post(() -> {
                try {
                    JSONObject v = new JSONObject();
                    v.put("width", decor.getWidth()); v.put("height", decor.getHeight());
                    v.put("fontScale", owner.getResources().getConfiguration().fontScale);
                    v.put("orientation", owner.getResources().getConfiguration().orientation);
                    v.put("densityDpi", owner.getResources().getDisplayMetrics().densityDpi);
                    if (Build.VERSION.SDK_INT >= 30 && decor.getRootWindowInsets() != null) {
                        WindowInsets wi = decor.getRootWindowInsets();
                        Insets i = wi.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout() | WindowInsets.Type.mandatorySystemGestures());
                        v.put("safeInsets", new JSONObject().put("left", i.left).put("top", i.top)
                            .put("right", i.right).put("bottom", i.bottom));
                    }
                    geometry = v.toString();
                    CocosHelper.runOnGameThread(() -> JsbBridge.sendToScript("viewport", geometry));
                } catch (Exception error) { Log.e("HarnessMenu", "viewport", error); }
            });
        });
    }

    private static void save(Activity owner, String value) {
        if ((owner.getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) == 0) return;
        AtomicFile file = new AtomicFile(new File(owner.getFilesDir(), "menu-observation.json"));
        FileOutputStream stream = null;
        try {
            JSONObject out = new JSONObject(value);
            out.put("package", owner.getPackageName()); out.put("pid", android.os.Process.myPid());
            out.put("nativeBackCount", backCount);
            stream = file.startWrite(); stream.write(out.toString().getBytes(StandardCharsets.UTF_8));
            file.finishWrite(stream);
        } catch (Exception error) {
            if (stream != null) file.failWrite(stream);
            Log.e("HarnessMenu", "observation", error);
        }
    }
}
