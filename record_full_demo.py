#!/usr/bin/env python3
"""
NIDAR RescueSwarm - Automated Full-Mission Screen Recorder & Director
=====================================================================
Records the complete autonomous mission from pre-flight boot to landing
for official competition and judge submission.

Features:
- Records full screen at 1080p (30 FPS) with H.264 MP4 encoding.
- Automated Mission Director: Focuses primarily on the Mission Control Centre window,
  while seamlessly switching to Gazebo 3D, RViz2 AI detection, QGroundControl, and
  Terminal output during key mission phases to provide judges with 360° technical proof.
- Automatically handles startup, auto-starts simulation, waits for mission completion,
  and gracefully finalizes the MP4 video container.
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime

# Xlib for window management
import Xlib
import Xlib.display
import Xlib.X
import Xlib.protocol.event

ROOT = Path(__file__).resolve().parent
RECORDINGS_DIR = ROOT / "simulation" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class WindowManager:
    """Finds, activates, and raises windows on X11 display."""
    def __init__(self):
        try:
            self.disp = Xlib.display.Display()
            self.root = self.disp.screen().root
            self.atom_client_list = self.disp.intern_atom('_NET_CLIENT_LIST')
            self.atom_name = self.disp.intern_atom('_NET_WM_NAME')
            self.atom_active = self.disp.intern_atom('_NET_ACTIVE_WINDOW')
            self.ok = True
        except Exception as e:
            print(f"[DIRECTOR] Warning: Could not connect to X11 Display ({e})", flush=True)
            self.ok = False

    def find_window(self, keywords: list):
        """Finds window ID matching any of the given keywords in title or class."""
        if not self.ok:
            return None, ""
        try:
            prop = self.root.get_full_property(self.atom_client_list, Xlib.X.AnyPropertyType)
            if not prop:
                return None, ""
            for wid in prop.value:
                try:
                    w = self.disp.create_resource_object('window', wid)
                    name_prop = w.get_full_property(self.atom_name, Xlib.X.AnyPropertyType)
                    name = (name_prop.value.decode('utf-8', errors='ignore') if name_prop else w.get_wm_name()) or ""
                    cls_prop = w.get_wm_class() or ()
                    combined = (name + " " + " ".join(cls_prop)).lower()
                    for kw in keywords:
                        if kw.lower() in combined:
                            return wid, name
                except Exception:
                    continue
        except Exception:
            pass
        return None, ""

    def activate_window(self, wid: int, name: str = ""):
        """Raises and gives focus to the target window."""
        if not self.ok or wid is None:
            return False
        try:
            data = [2, 0, 0, 0, 0] # 2 = pager / user interaction
            ev = Xlib.protocol.event.ClientMessage(
                window=wid,
                client_type=self.atom_active,
                data=(32, data)
            )
            self.root.send_event(ev, event_mask=Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask)

            w = self.disp.create_resource_object('window', wid)
            w.configure(stack_mode=Xlib.X.Above)
            self.disp.sync()
            return True
        except Exception:
            return False

    def focus(self, category: str):
        """Focuses window by logical category name."""
        mapping = {
            "control_centre": ["mission control", "nidar rescueswarm"],
            "gazebo": ["gazebo sim", "ogrewindow"],
            "qgc": ["qgroundcontrol"],
            "rviz": ["rviz", "rviz2"],
            "terminal": ["nidar_rescueswarm", "terminal", "tp:"],
        }
        kws = mapping.get(category, [category])
        wid, name = self.find_window(kws)
        if wid:
            self.activate_window(wid, name)
            return True
        return False


def start_screen_recorder(output_file: Path) -> subprocess.Popen:
    """Launches high-quality 1080p 30fps GStreamer screen capture pipeline."""
    cmd = [
        "gst-launch-1.0", "-e",
        "ximagesrc", "use-damage=0",
        "!", "video/x-raw,framerate=30/1",
        "!", "videoscale",
        "!", "video/x-raw,width=1920,height=1080",
        "!", "videoconvert",
        "!", "x264enc", "tune=zerolatency", "speed-preset=ultrafast", "bitrate=5000",
        "!", "mp4mux",
        "!", "filesink", f"location={output_file}"
    ]
    log_file = open(RECORDINGS_DIR / "recorder.log", "w")
    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    return proc


def stop_screen_recorder(proc: subprocess.Popen):
    """Gracefully terminates GStreamer to ensure MP4 container moov headers are finalized."""
    if proc.poll() is None:
        print("[RECORDER] Finalizing MP4 recording container (sending EOS)...", flush=True)
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            print("[RECORDER] Timeout waiting for EOS. Forcing termination...", flush=True)
            proc.terminate()
            proc.wait(timeout=5)
    print("[RECORDER] Screen recording finalized cleanly.", flush=True)


def window_director_loop(stop_event: threading.Event):
    """Background thread managing window focus choreography."""
    wm = WindowManager()
    start_time = time.monotonic()
    last_tour_time = start_time + 40.0

    print("[DIRECTOR] Initializing pre-flight window showcase...", flush=True)
    time.sleep(5)
    if stop_event.is_set(): return
    wm.focus("terminal")
    time.sleep(7)
    if stop_event.is_set(): return
    wm.focus("qgc")
    time.sleep(7)
    if stop_event.is_set(): return
    wm.focus("gazebo")
    time.sleep(7)
    if stop_event.is_set(): return

    # Primary focus: Mission Control Centre
    print("[DIRECTOR] Locking primary focus to NIDAR Mission Control Centre...", flush=True)
    wm.focus("control_centre")

    while not stop_event.is_set():
        now = time.monotonic()
        elapsed = now - start_time

        # Every 90 seconds, run an 8-second inspection tour of each subsystem
        if elapsed > 90.0 and (now - last_tour_time > 90.0):
            print(f"[DIRECTOR] [{int(elapsed)}s] Technical Inspection Tour for Judges...", flush=True)

            wm.focus("gazebo")
            for _ in range(8):
                if stop_event.is_set(): return
                time.sleep(1)

            wm.focus("rviz")
            for _ in range(8):
                if stop_event.is_set(): return
                time.sleep(1)

            wm.focus("qgc")
            for _ in range(8):
                if stop_event.is_set(): return
                time.sleep(1)

            wm.focus("terminal")
            for _ in range(8):
                if stop_event.is_set(): return
                time.sleep(1)

            # Return to Mission Control Centre
            print("[DIRECTOR] Returning focus to NIDAR Mission Control Centre...", flush=True)
            wm.focus("control_centre")
            last_tour_time = time.monotonic()

        time.sleep(1.0)


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_video = RECORDINGS_DIR / f"nidar_mission_judges_{timestamp}.mp4"
    symlink_video = RECORDINGS_DIR / "latest_mission_recording.mp4"

    print("====================================================================")
    print("      🛰 NIDAR RESCUESWARM // FULL MISSION RECORDER & DIRECTOR")
    print("====================================================================")
    print(f"Output Video File : {output_video}")
    print("Recording Specs   : 1080p HD @ 30 FPS (H.264 High-Bitrate MP4)")
    print("Focus Strategy    : ~75% Mission Control Centre (Core Tactical View)")
    print("                    + Periodic Inspection Tours of Gazebo, RViz, QGC & CMD")
    print("====================================================================")

    # 1. Start Screen Recorder
    print("\n[RECORDER] Initializing screen capture pipeline...", flush=True)
    rec_proc = start_screen_recorder(output_video)
    time.sleep(2)
    if rec_proc.poll() is not None:
        print("[ERROR] Failed to start GStreamer recording pipeline! Check recorder.log", file=sys.stderr)
        sys.exit(1)
    print("[RECORDER] Screen recording is LIVE.", flush=True)

    # 2. Start Director in background thread
    stop_event = threading.Event()
    director_thread = threading.Thread(target=window_director_loop, args=(stop_event,), daemon=True)
    director_thread.start()

    # 3. Launch Simulation in foreground terminal (so outputs stream directly to terminal window!)
    print("\n[SIMULATION] Starting NIDAR demo mission with RViz and Auto-Start enabled...", flush=True)
    sim_env = os.environ.copy()
    sim_env.update(
        RUN_RVIZ="1",
        AUTO_START="1",
        DETECTOR=os.environ.get("DETECTOR", "ssd"),
    )

    try:
        # Run demo script directly with terminal I/O (no pipe buffering)
        demo_proc = subprocess.Popen(
            ["./run_nidar_demo.sh"],
            cwd=ROOT,
            env=sim_env,
        )
        demo_proc.wait()

    except KeyboardInterrupt:
        print("\n[MAIN] User interrupted mission recording. Stopping cleanly...", flush=True)
    finally:
        # Stop director
        stop_event.set()

        # Stop screen recorder cleanly
        stop_screen_recorder(rec_proc)

        # Update symlink
        try:
            if symlink_video.is_symlink() or symlink_video.exists():
                symlink_video.unlink()
            symlink_video.symlink_to(output_video.name)
        except Exception:
            pass

        # Cleanup simulation processes
        subprocess.run(["./stop_nidar_demo.sh"], cwd=ROOT, check=False)

    # 4. Summary
    if output_video.exists():
        size_mb = output_video.stat().st_size / (1024 * 1024)
        print("\n====================================================================")
        print("          🎉 FULL MISSION RECORDING COMPLETED SUCCESSFULLY!")
        print("====================================================================")
        print(f"Recorded Video  : {output_video}")
        print(f"Latest Link     : {symlink_video}")
        print(f"File Size       : {size_mb:.2f} MB")
        print("Format          : 1080p HD, 30 FPS, H.264 / MP4 (Universal Playback)")
        print("\nYou can submit this video file directly to the competition judges!")
        print(f"To play: vlc {output_video}")
        print("====================================================================")
    else:
        print("[ERROR] Recorded file was not found!", file=sys.stderr)


if __name__ == "__main__":
    main()
