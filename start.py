import os
import urllib.request
import subprocess
import time

def get_fastpicker_dir():
    appdata = os.getenv("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA not found")
    folder = os.path.join(appdata, "Fastpicker")
    os.makedirs(folder, exist_ok=True)
    return folder

def download_file(url, dest):
    raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    with urllib.request.urlopen(raw_url) as r, open(dest, "wb") as f:
        f.write(r.read())
    print(f"Downloaded {os.path.basename(dest)}")

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return None

def read_remote(url):
    try:
        raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        with urllib.request.urlopen(raw_url) as r:
            return r.read().decode("utf-8").strip()
    except:
        return None

def main():
    FASTPICKER_DIR = get_fastpicker_dir()
    APP_EXE_PATH = os.path.join(FASTPICKER_DIR, "app.exe")
    UPDATE_TXT_PATH = os.path.join(FASTPICKER_DIR, "update.txt")
    HTML_PATH = os.path.join(FASTPICKER_DIR, "fastpickui.html")

    REMOTE_APP_URL = "https://github.com/060001/tekitou1/blob/main/app.exe"
    REMOTE_UPDATE_URL = "https://github.com/060001/tekitou1/blob/main/update.txt"
    REMOTE_HTML_URL = "https://github.com/060001/tekitou1/blob/main/fastpickui.html"
    if not os.path.exists(APP_EXE_PATH) or not os.path.exists(UPDATE_TXT_PATH) or not os.path.exists(HTML_PATH):
        print("First time setup, downloading all files...")
        download_file(REMOTE_UPDATE_URL, UPDATE_TXT_PATH)
        download_file(REMOTE_APP_URL, APP_EXE_PATH)
        download_file(REMOTE_HTML_URL, HTML_PATH)
    else:
        print("Checking for updates...")
        local_update = read_file(UPDATE_TXT_PATH)
        remote_update = read_remote(REMOTE_UPDATE_URL)
        if local_update and remote_update and local_update != remote_update:
            print("Update.txt changed, updating app...")
            download_file(REMOTE_UPDATE_URL, UPDATE_TXT_PATH)
            download_file(REMOTE_APP_URL, APP_EXE_PATH)

        local_html = read_file(HTML_PATH)
        remote_html = read_remote(REMOTE_HTML_URL)
        if local_html and remote_html and local_html != remote_html:
            print("HTML changed, updating fastpickui.html...")
            download_file(REMOTE_HTML_URL, HTML_PATH)
        else:
            print("HTML up to date.")

    # app.exe 実行
    print(f"Starting {APP_EXE_PATH} ...")
    try:
        proc = subprocess.Popen([APP_EXE_PATH], cwd=FASTPICKER_DIR)

        # app.exe のプロセス監視
        while True:
            code = proc.poll()
            if code is not None:
                print(f"app.exe exited with code {code}. Closing start.py ...")
                break
            time.sleep(1)

    except Exception as e:
        print(f"Failed to start app.exe: {e}")
        input("Press Enter to exit.")

if __name__ == "__main__":
    main()
