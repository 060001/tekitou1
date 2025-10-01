import sys, os, tempfile
log_path = os.path.join(tempfile.gettempdir(), "valorant_picker.log")
sys.stdout = open(log_path, "w", encoding="utf-8", buffering=1)
sys.stderr = sys.stdout
import os
import json
import time
import threading
import tempfile
import webview
import urllib.request
import pathlib
import hashlib
from valclient.client import Client
from valclient.exceptions import PhaseError

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

BASE_DIR = os.path.dirname(__file__)
TEMP_DIR = tempfile.gettempdir()
AGENTS_JSON = os.path.join(TEMP_DIR, "agents.json")
LAST_AGENT_FILE = os.path.join(TEMP_DIR, "valorant_picker_last_agent.json")
AGENTS_API = "https://valorant-api.com/v1/agents"
VALID_REGIONS = ["na", "eu", "latam", "br", "ap", "kr", "pbe"]
REGION_MAP = {
    "europe": "eu", "north america": "na", "asia pacific": "ap",
    "latin america": "latam", "brazil": "br", "korea": "kr",
    "pbe": "pbe", "eu": "eu", "na": "na", "ap": "ap",
    "latam": "latam", "br": "br", "kr": "kr"
}

class API:
    def __init__(self):
        self.running = False
        self.client = None
        self.agents = []
        self._last_status = ""
        self._status_lock = threading.Lock()
        self.last_agent_uuid = self._load_last_agent()
    def minimize_window(self):
        try:
            import webview as _wv
            if _wv.windows:
                _wv.windows[0].minimize()
                return "minimized"
            return "no_window"
        except Exception as e:
            self.log("minimize error:", e)
            return "minimize error"
    def close_window(self):
        try:
            import webview as _wv
            if _wv.windows:
                _wv.windows[0].destroy()
                time.sleep(0.1)
                os._exit(0)
            return "closed"
        except Exception as e:
            self.log("close error:", e)
            return "close error"
    def resize_window(self, width, height=None):
        try:
            import webview as _wv
            if _wv.windows:
                if height is None:
                    _wv.windows[0].resize(width, _wv.windows[0].height)
                else:
                    _wv.windows[0].resize(int(width), int(height))
                return "resized"
            return "no_window"
        except Exception as e:
            self.log("resize error:", e)
            return "resize error"
    def connect_auto_region(self):
        import urllib.request as _ur, json as _json
        country_to_region = {
            'jp': 'ap', 'sg': 'ap', 'kr': 'kr', 'br': 'br',
            'us': 'na', 'ca': 'na', 'mx': 'na', 'cl': 'latam',
            'ar': 'latam', 'fr': 'eu', 'de': 'eu', 'gb': 'eu',
            'it': 'eu', 'es': 'eu',
        }
        selected_region = "ap"
        try:
            with _ur.urlopen("https://ipapi.co/json/") as response:
                data = _json.load(response)
                c = str(data.get("country", "")).lower()
                selected_region = country_to_region.get(c, "ap")
        except Exception as e:
            self.log("auto_region_ipapi error:", e)
        try:
            self.client = Client(region=selected_region)
            self.client.activate()
            self._set_status(f"Connected (region: {selected_region})")
            return f"Connected (region: {selected_region})"
        except Exception as e:
            msg = "Valorantを起動して下さい"
            self._set_status(msg)
            self.log("connect_auto_region error:", e)
            return msg
    def log(self, *a): print("[DEBUG]", *a, flush=True)
    def _set_status(self, msg):
        with self._status_lock:
            self._last_status = str(msg)
    def get_status(self):
        with self._status_lock:
            return self._last_status
    def _save_last_agent(self, uuid):
        try:
            with open(LAST_AGENT_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_agent_uuid": uuid}, f)
            self.last_agent_uuid = uuid
            return True
        except Exception as e:
            self.log("save last agent error:", e)
            return False
    def _load_last_agent(self):
        try:
            if os.path.exists(LAST_AGENT_FILE):
                with open(LAST_AGENT_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("last_agent_uuid") or ""
        except Exception as e:
            self.log("load last agent error:", e)
        return ""
    def get_last_agent(self):
        return self.last_agent_uuid or ""
    def set_last_agent(self, uuid):
        return self._save_last_agent(uuid or "")
    def get_agents(self):
        try:
            import urllib.request as _ur
            with _ur.urlopen(AGENTS_API) as resp:
                j = json.load(resp)
                self.agents = [
                    {"displayName": i["displayName"], "uuid": i["uuid"]}
                    for i in j.get("data", []) if i.get("isPlayableCharacter")
                ]
            with open(AGENTS_JSON, "w", encoding="utf-8") as f:
                json.dump(self.agents, f, ensure_ascii=False, indent=2)
            self.log(f"agents.json updated at: {AGENTS_JSON}")
            self._set_status("agents.json 更新しました")
        except Exception as e:
            self.log("Failed to load agents:", e)
            try:
                if os.path.exists(AGENTS_JSON):
                    with open(AGENTS_JSON, encoding="utf-8") as f:
                        self.agents = json.load(f)
                else:
                    self.agents = []
            except Exception:
                self.agents = []
        return self.agents
    def start(self, region, agent_arg):
        if self.running:
            self._set_status("Already running")
            return "Already running"
        region = (region or "").strip().lower()
        if not region:
            if not self.client:
                auto_msg = self.connect_auto_region()
                if "Connected" not in auto_msg:
                    return auto_msg
        else:
            rg = REGION_MAP.get(region, region)
            if rg not in VALID_REGIONS:
                self._set_status("無効なリージョン")
                return f"無効なリージョンです: {region} → {VALID_REGIONS}"
            try:
                self.client = Client(region=rg)
                self.client.activate()
            except Exception as e:
                self.log("Cannot connect to client:", e)
                self._set_status("Valorantを起動 & ログインしてください")
                return "Valorantを起動 & ログインしてください"
        uuid = (agent_arg or "").strip()
        if not uuid and self.last_agent_uuid:
            uuid = self.last_agent_uuid
        if uuid:
            found = next(
                (a["uuid"] for a in self.agents
                 if a.get("uuid") == uuid or (a.get("displayName","").lower() == uuid.lower())),
                None
            )
            if found:
                uuid = found
        if not uuid:
            self._set_status("エージェント未選択")
            return "エージェント未選択"
        self._save_last_agent(uuid)
        self.running = True
        threading.Thread(target=self._loop, args=(uuid,), daemon=True).start()
        self._set_status("Started")
        return "Waiting..."
    def _loop(self, uuid):
        seen = set()
        self._set_status("Waiting for PREGAME...")
        while self.running:
            try:
                session = self.client.session_fetch()
                s = session.get("loopState")
                self.log("State:", s)
                if s == "PREGAME":
                    t0 = time.time(); ready = False
                    while time.time() - t0 < 30 and self.running:
                        try:
                            self.client.pregame_fetch_player()
                            ready = True
                            break
                        except PhaseError:
                            time.sleep(0.5)
                        except Exception as e:
                            self.log("pregame_fetch_player unexpected error:", repr(e))
                            time.sleep(0.5)
                    if not ready:
                        self._set_status("pregame情報取得失敗")
                        time.sleep(1); continue
                    player = self.client.pregame_fetch_player()
                    mid = player.get("MatchID") or player.get("matchId")
                    if not mid:
                        self._set_status("MatchID取得失敗"); time.sleep(1); continue
                    if mid in seen:
                        self._set_status("既処理マッチ、待機中"); time.sleep(1); continue
                    self._set_status("Attempting pick")
                    self.log("Attempting pick for match:", mid, "uuid:", uuid)
                    success = False
                    for i in range(6):
                        if not self.running: break
                        try:
                            self.client.pregame_select_character(uuid)
                            time.sleep(0.2)
                            self.client.pregame_lock_character(uuid)
                            self._set_status("Picked!")
                            seen.add(mid)
                            success = True
                            self.log("Pick succeeded on try", i+1)
                            break
                        except Exception as e:
                            self.log(f"Pick {i+1} error:", repr(e))
                            self._set_status(f"試行中 {i+1}/6 - {str(e)[:60]}")
                            time.sleep(0.7)
                    self._set_status("成功" if success else "ピック失敗")
                time.sleep(1)
            except Exception as e:
                self.log("Loop error:", repr(e))
                self._set_status("ループエラー")
                time.sleep(1)
        self._set_status("Stopped")
    def force_pick(self, uuid):
        try:
            if not self.client:
                self.log("force_pick: client not connected")
                return "client_not_connected"
            self.log("force_pick: selecting", uuid)
            try:
                self.client.pregame_select_character(uuid)
                time.sleep(0.2)
                self.client.pregame_lock_character(uuid)
                self._set_status("force pick succeeded")
                self.log("force_pick: succeeded")
                return "ok"
            except Exception as e:
                self.log("force_pick error:", repr(e))
                self._set_status(f"force_pick error: {e}")
                return f"error: {e}"
        except Exception as e:
            self.log("force_pick unexpected:", e)
            return f"unexpected: {e}"
    def stop(self):
        if not self.running:
            self._set_status("Not running")
            return "Not running"
        self.running = False
        self._set_status("Stop")
        return "Stopped"
    def dodge(self):
        if not self.client:
            self._set_status("未接続")
            return "未接続"
        try:
            session = self.client.session_fetch()
            st = session.get("loopState")
        except Exception as e:
            self.log("Dodge session error:", e)
            self._set_status("状態取得失敗")
            return "状態取得失敗"
        if st == "PREGAME":
            try:
                self.client.pregame_quit_match()
                self._set_status("Successfully dodged")
                return "Successfully dodged"
            except Exception as e:
                self.log("Dodge error:", e)
                self._set_status("Dodge失敗")
                return "Dodge失敗"
        self._set_status("Agent選択画面ではありません")
        return "Agent選択画面ではありません"
    def fetchSessionState(self):
        if not self.client:
            return "NOT_CONNECTED"
        try:
            session = self.client.session_fetch()
            return session.get("loopState") or ""
        except Exception as e:
            self.log("fetchSessionState error:", e)
            return "ERROR"
    def get_all_players(self):
        if not self.client:
            return []
        try:
            session = self.client.session_fetch()
            session_state = session.get("loopState")
        except Exception as e:
            self.log("session_fetch error:", e)
            return []
        players = []
        try:
            if session_state == "INGAME":
                match = self.client.coregame_fetch_match()
                players = match.get("Players", [])
            elif session_state == "PREGAME":
                match = self.client.pregame_fetch_match()
                ally = match.get("AllyTeam", {}).get("Players", [])
                enemy = match.get("EnemyTeam", {}).get("Players", [])
                players = ally + enemy
            else:
                return []
        except Exception as e:
            self.log("match fetch error:", e)
            return []
        subjects, mapped = [], []
        for idx, p in enumerate(players, 1):
            subj = p.get("Subject")
            subjects.append(subj)
            mapped.append({
                "subject": subj,
                "characterId": p.get("CharacterID"),
                "teamId": p.get("TeamID") or p.get("TeamId"),
                "fillerName": p.get("fillerName") or f"Player{idx}",
                "incognito": p.get("PlayerIdentity", {}).get("Incognito", False)
            })
        resolved, result = [], []
        try:
            if subjects:
                res = self.client.put(endpoint="/name-service/v2/players", endpoint_type="pd", json_data=subjects)
                if isinstance(res, list) and len(res) == len(subjects):
                    resolved = [{"GameName": r.get("GameName"), "TagLine": r.get("TagLine")} for r in res]
                else:
                    resolved = [None]*len(subjects)
        except Exception as e:
            self.log("name resolve error:", e)
            resolved = [None]*len(subjects)
        for i, m in enumerate(mapped):
            ni = resolved[i] if i < len(resolved) else None
            full = f"{ni['GameName']}#{ni['TagLine']}" if ni and ni.get("GameName") else m.get("fillerName") or "Unknown"
            agent_name = next((a["displayName"] for a in self.agents if a.get("uuid")==m.get("characterId")), m.get("fillerName") or "Unknown")
            tid = m.get("teamId", "")
            side = "Attacker" if str(tid).lower()=="red" else "Defender" if str(tid).lower()=="blue" else "Unknown"
            result.append({"subject": m["subject"], "name": full, "agent": agent_name, "side": side, "incognito": m["incognito"]})
        return result
    def get_all_players_rank(self):
        players = self.get_all_players()
        if not players:
            return []
        try:
            content = self.client.fetch_content()
            seasonID = None
            for s in content.get("Seasons", []):
                if s.get("Type") == "act" and s.get("IsActive"):
                    seasonID = s.get("ID")
                    break
        except Exception as e:
            self.log("fetch_content error:", e)
            seasonID = None
        result = []
        for p in players:
            out = {"subject": p.get("subject"), "name": p.get("name"), "agent": p.get("agent"), "side": p.get("side"), "incognito": p.get("incognito")}
            out.update({"rank": "N/a", "rr": 0, "peakrank": "N/a", "wr": "N/a", "kd": "N/a", "hs": "N/a", "totalGames": "N/a"})
            subj = p.get("subject")
            try:
                mmr = self.client.fetch_mmr(subj)
                qskills = mmr.get("QueueSkills", {}).get("competitive", {})
                seasonal = qskills.get("SeasonalInfoBySeasonID") or {}
                peak = 0
                for sid, sdata in seasonal.items():
                    wins_by_tier = sdata.get("WinsByTier") or {}
                    if wins_by_tier:
                        try:
                            max_tier = max(int(t) for t in wins_by_tier.keys())
                            if max_tier > peak:
                                peak = max_tier
                        except:
                            pass
                if peak:
                    out["peakrank"] = str(peak)
                if seasonID and seasonID in seasonal:
                    cur = seasonal.get(seasonID, {})
                    try:
                        c_tier = cur.get("CompetitiveTier")
                        c_rr = cur.get("RankedRating") or cur.get("RankedRating")
                        wins = cur.get("NumberOfWinsWithPlacements") or cur.get("NumberOfWins") or 0
                        total = cur.get("NumberOfGames") or 0
                        out["rank"] = str(c_tier) if c_tier is not None else out["rank"]
                        try:
                            out["rr"] = int(c_rr) if c_rr is not None else out["rr"]
                        except:
                            out["rr"] = out["rr"]
                        out["totalGames"] = total
                        try:
                            wr = int(wins / total * 100) if total else 100
                            out["wr"] = wr
                        except:
                            out["wr"] = "N/a"
                    except Exception as e:
                        self.log("season parse error:", e, subj)
                else:
                    out["rank"] = out.get("rank", "N/a")
            except Exception as e:
                self.log("fetch_mmr error:", e, subj)
            try:
                lastComp = self.client.fetch(endpoint=f"/mmr/v1/players/{subj}/competitiveupdates?startIndex=0&endIndex=1&queue=competitive", endpoint_type="pd")
                matches = lastComp.get("Matches") or []
                if matches:
                    matchId = matches[0].get("MatchID")
                    if matchId:
                        md = self.client.fetch_match_details(matchId)
                        total_hits = 0
                        total_headshots = 0
                        kills = 0
                        deaths = 0
                        for Round in md.get("roundResults", []):
                            for currentPlayer in Round.get("playerStats", []):
                                if currentPlayer.get("subject") == subj:
                                    for hits in currentPlayer.get("damage", []):
                                        total_hits += int(hits.get("legshots", 0))
                                        total_hits += int(hits.get("bodyshots", 0))
                                        total_hits += int(hits.get("headshots", 0))
                                        total_headshots += int(hits.get("headshots", 0))
                        for tp in md.get("players", []):
                            if tp.get("subject") == subj:
                                kills = int(tp.get("stats", {}).get("kills", 0))
                                deaths = int(tp.get("stats", {}).get("deaths", 0))
                                break
                        try:
                            out["hs"] = round((total_headshots / total_hits) * 100, 1) if total_hits else "N/a"
                        except:
                            out["hs"] = "N/a"
                        try:
                            if deaths == 0 and kills > 0:
                                out["kd"] = kills
                            elif deaths == 0 and kills == 0:
                                out["kd"] = 0
                            else:
                                out["kd"] = round(kills / deaths, 2)
                        except:
                            out["kd"] = "N/a"
            except Exception as e:
                self.log("last match fetch error:", e, subj)
            if isinstance(out.get("rank"), int):
                out["rank"] = str(out["rank"])
            result.append(out)
        return result

def calc_file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None

def fetch_url_hash_and_data(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            if resp.status != 200:
                return None, None
            data = resp.read()
            return hashlib.sha256(data).hexdigest(), data
    except Exception as e:
        print("DEBUG: url fetch/hash failed", e)
        return None, None

def update_fastpickui_if_needed(local_path, url):
    local_hash = calc_file_hash(local_path) if os.path.exists(local_path) else None
    remote_hash, remote_data = fetch_url_hash_and_data(url)
    if remote_data is None:
        return False
    if local_hash != remote_hash:
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
        except Exception as e:
            print("DEBUG: remove old fastpickui.html failed", e)
        try:
            with open(local_path, "wb") as f:
                f.write(remote_data)
            print("DEBUG: fastpickui.html downloaded/updated.")
            return True
        except Exception as e:
            print("DEBUG: save fastpickui.html failed:", e)
            return False
    return False

def main():
    RAW_URL = "https://raw.githubusercontent.com/060001/tekitou1/refs/heads/main/fastpickui.html"
    temp_html_path = os.path.join(TEMP_DIR, "fastpickui.html")
    update_fastpickui_if_needed(temp_html_path, RAW_URL)
    def download_ui(url, dst, timeout=10):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(dst, "wb") as f:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                f.write(resp.read())
            try:
                with open(dst, "r", encoding="utf-8", errors="ignore") as rf:
                    head = rf.read(512).lower()
                    if "<html" not in head and "<!doctype" not in head:
                        pass
            except Exception:
                pass
            return True
        except Exception as e:
            print("DEBUG: download failed:", e)
            return False
    if os.path.exists(temp_html_path):
        ok = True
        skipped_download = True
    else:
        skipped_download = False
        ok = download_ui(RAW_URL, temp_html_path)
        if not ok:
            alt_urls = [
                "https://raw.githubusercontent.com/060001/tekitou1/refs/heads/main/fastpickui.html",
                "https://raw.githubusercontent.com/060001/tekitou1/main/fastpickui.html",
                "https://raw.githubusercontent.com/060001/tekitou1/master/fastpickui.html",
            ]
            tried = set([RAW_URL])
            for alt in alt_urls:
                if alt in tried:
                    continue
                tried.add(alt)
                if download_ui(alt, temp_html_path):
                    ok = True
                    break
    if os.path.exists(temp_html_path):
        target_uri = pathlib.Path(temp_html_path).resolve().as_uri()
    else:
        local_index = resource_path("index.html")
        if os.path.exists(local_index):
            try:
                with open(local_index, "rb") as rf, open(temp_html_path, "wb") as wf:
                    wf.write(rf.read())
                target_uri = pathlib.Path(temp_html_path).resolve().as_uri()
            except Exception as e:
                target_uri = pathlib.Path(local_index).resolve().as_uri()
        else:
            input("続行するには何かキーを押してください...")
            return
    api = API()
    api.get_agents()
    serve_root = pathlib.Path(TEMP_DIR).resolve()
    start_file = "fastpickui.html"
    start_path = serve_root / start_file
    if not start_path.exists():
        local_index = resource_path("index.html")
        if os.path.exists(local_index):
            try:
                with open(local_index, "rb") as rf, open(start_path, "wb") as wf:
                    wf.write(rf.read())
            except Exception:
                pass
    try:
        with open(start_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        modified = False
        new_lines = []
        for idx, line in enumerate(lines):
            new_lines.append(line)
            if 'appendLog("自動接続:' in line and "setStatus(" not in line:
                new_lines.append("        setStatus(result);\n")
                modified = True
            if "DOMContentLoaded" in line and "loadAgents" in line and "// AUTO-RETRY-PATCH" not in "".join(lines[idx:idx+5]):
                inject_code = """
document.addEventListener('DOMContentLoaded', ()=>{
  try{ const sb=document.getElementById('startBtn'); if(sb) sb.disabled=true; }catch(e){}
  async function retryConnectLoop(){
    appendLog("再接続試行中");
    const ok = await ensureApi();
    if(!ok){ setTimeout(retryConnectLoop,1000); return; }
    try{
      const res = await window.pywebview.api.connect_auto_region();
      appendLog("再接続: "+res);
      setStatus(res);
      if(typeof res==='string' && res.includes("Connected")){
        try{ const sb=document.getElementById('startBtn'); if(sb) sb.disabled=false; }catch(e){}
        return;
      }
    }catch(e){}
    setTimeout(retryConnectLoop,1000);
  }
  retryConnectLoop();
});
"""
                new_lines.append(inject_code)
                modified = True
        if modified:
            with open(start_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
    except Exception:
        pass
    try:
        os.chdir(str(serve_root))
    except Exception:
        pass
    try:
        window = webview.create_window(
            "Valorant Picker",
            str(start_path),
            js_api=api,
            width=420,
            height=480,
            resizable=False,
            frameless=True,
            easy_drag=False
        )
        webview.start(http_server=True)
    except Exception:
        try:
            import traceback; traceback.print_exc()
        except Exception:
            pass
        input("エラーが発生しました。内容を確認して何かキーを押すと終了します...")

if __name__ == "__main__":
    main()
