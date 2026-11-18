# 从 Obsidian 笔记的 Timeline / ROUND 属性生成 calendar.ics
# 规则与「IN calendar.md」的 dataviewjs 一致：
#   - 读取 ·Timeline / timeline，格式如 11/16出願>；11/27出願◎
#   - ROUND 为 0 / 00 / 000 的笔记跳过
#   - 7 月及以后算 2026 年，1–6 月算 2027 年
#   - 事件名：aliases 第一个（没有则用文件名）·标签
# 用法：python3 gen_ics.py <vault 或笔记文件夹> <输出 .ics>
import sys, os, re, glob, hashlib, datetime
import yaml

vault, out = sys.argv[1], sys.argv[2]

def year_of(m):
    return 2026 if m >= 7 else 2027

def get(d, *keys):
    low = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        v = low.get(k.lower())
        if v not in (None, ""):
            return v
    return None

events = []
for path in glob.glob(os.path.join(vault, "**/*.md"), recursive=True):
    rel = os.path.relpath(path, vault)
    if rel.split(os.sep)[0].startswith(".") or "*history" in rel:
        continue
    txt = open(path, encoding="utf-8").read()
    if not txt.startswith("---"):
        continue
    end = txt.find("\n---", 3)
    if end < 0:
        continue
    try:
        fm = yaml.safe_load(txt[3:end]) or {}
    except Exception:
        continue
    if not isinstance(fm, dict):
        continue
    t = get(fm, "·Timeline", "timeline")
    if t is None:
        continue
    rnd = get(fm, "·ROUND", "round")
    if isinstance(rnd, list):
        rnd = ", ".join(map(str, rnd))
    rnd = str(rnd).strip() if rnd is not None else ""
    if re.fullmatch(r"0+", rnd):
        continue
    if isinstance(t, list):
        t = "；".join(map(str, t))
    t = str(t)
    fname = os.path.splitext(os.path.basename(path))[0]
    al = fm.get("aliases")
    if isinstance(al, str):
        al = [al]
    name = al[0] if al else fname
    for m in re.finditer(r"(\d{1,2})\s*/\s*(\d{1,2})\s*([^；;，,\n]*)", t):
        mo, d = int(m[1]), int(m[2])
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            continue
        events.append((year_of(mo), mo, d, m[3].strip(), str(name), fname))

def esc(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//bam//IN calendar//ZH",
     "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:大学院出願",
     "X-WR-TIMEZONE:Asia/Tokyo", "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
     "X-PUBLISHED-TTL:PT1H"]
seen = set()
for y, mo, d, label, name, fname in sorted(events):
    try:
        day = datetime.date(y, mo, d)
    except ValueError:
        continue
    uid = hashlib.sha1(f"{fname}|{y}-{mo}-{d}|{label}".encode()).hexdigest()[:20]
    if uid in seen:
        continue
    seen.add(uid)
    L += ["BEGIN:VEVENT", f"UID:{uid}@in-calendar", f"DTSTAMP:{now}",
          f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
          f"DTEND;VALUE=DATE:{day + datetime.timedelta(days=1):%Y%m%d}",
          f"SUMMARY:{esc(name + '·' + label)}", f"DESCRIPTION:{esc(fname)}",
          "TRANSP:TRANSPARENT", "END:VEVENT"]
L.append("END:VCALENDAR")
with open(out, "w", encoding="utf-8", newline="") as f:
    f.write("\r\n".join(L) + "\r\n")
print(len(seen), "events")
