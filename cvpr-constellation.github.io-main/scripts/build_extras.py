#!/usr/bin/env python3
"""Optional data refreshers for the constellation.

1. Presentation-type flags (oral/highlight) merged into papers.json:
     curl -o virtual.json https://cvpr.thecvf.com/static/virtual/data/cvpr-2026-orals-posters.json
     python scripts/build_extras.py flags virtual.json
   Adds/updates the 6th element of each papers.json record:
   0 = poster, 1 = highlight, 2 = oral (3 reserved for awards once announced).

2. Workshops list (embedded as `const WS=...` in index.html):
     curl -o workshops.html https://cvpr.thecvf.com/Conferences/2026/Workshops
     python scripts/build_extras.py workshops workshops.html
   Prints the WS constant to stdout — paste it over the existing one.
"""
import html as H, json, re, sys


def flags(virtual_path):
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    virt = json.load(open(virtual_path))["results"]
    flag = {}
    for r in virt:
        dec = r.get("decision") or ""
        f = 2 if "Oral" in dec else 1 if "Highlight" in dec else 0 if "Poster" in dec else None
        if f is None:
            continue
        n = norm(r.get("name") or "")
        if n:
            flag[n] = max(flag.get(n, 0), f)
    papers = json.load(open("papers.json", encoding="utf-8"))
    out = [[p[0], p[1], p[2], p[3], p[4], flag.get(norm(p[0]), 0)] for p in papers]
    json.dump(out, open("papers.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    import collections
    print("flag distribution:", collections.Counter(p[5] for p in out).most_common())


def workshops(html_path):
    h = open(html_path, encoding="utf-8", errors="replace").read()
    cur, cats, catmap, out = None, [], {}, []
    for t in re.split(r"(<h3>.*?</h3>)", h):
        m = re.match(r"<h3>(.*?)</h3>", t)
        if m:
            cur = H.unescape(m.group(1).strip())
            continue
        if cur is None:
            continue
        for row in re.findall(r"<tr.*?</tr>", t, re.S):
            a = re.search(r'<a href="(https?://[^"]+)" target="_blank">(.*?)</a>', row, re.S)
            if not a:
                continue
            day = re.search(r"<a href='[^']*'>([A-Z][a-z]{2} [AP]M[^<]*)</a>", row)
            title = H.unescape(re.sub(r"\s+", " ", a.group(2)).strip())
            if cur not in catmap:
                catmap[cur] = len(cats)
                cats.append(cur)
            out.append([title, a.group(1), catmap[cur], day.group(1).strip() if day else ""])
    print("const WS=" + json.dumps({"cats": cats, "list": out},
          ensure_ascii=False, separators=(",", ":")) + ";")
    print(f"// {len(cats)} categories, {len(out)} workshops", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("flags", "workshops"):
        sys.exit(__doc__)
    (flags if sys.argv[1] == "flags" else workshops)(sys.argv[2])
