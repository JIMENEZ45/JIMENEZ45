import json, os, sys, random, urllib.request

USER = os.environ.get("GITHUB_USER", "JIMENEZ45")
CELL, GAP, PAD = 12, 4, 14
STEP = CELL + GAP
DT = 0.13          # segundos por casilla
LEVELS = ["#5eead4", "#38bdf8", "#818cf8", "#c084fc", "#f472b6"]  # nivel 0..4 (0 = vacío)
MAX_LEN = 30


def fetch_weeks():
    if "--demo" in sys.argv:
        random.seed(3)
        return [[random.choice([0, 0, 0, 0, 1, 2, 5, 9]) for _ in range(7)] for _ in range(53)]
    q = ('query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{'
         'weeks{contributionDays{contributionCount weekday}}}}}}')
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"u": USER}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"], "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    out = []
    for w in weeks:
        col = [0] * 7
        for d in w["contributionDays"]:
            col[d["weekday"]] = d["contributionCount"]
        out.append(col)
    return out


def level(c, mx):
    if c <= 0:
        return 0
    r = c / mx
    return 1 if r < .25 else 2 if r < .5 else 3 if r < .75 else 4


def hsl_lerp(t):
    # cola azul -> cabeza rosa
    h = 200 + (330 - 200) * t
    return f"hsl({h:.0f},85%,{62 - 6 * (1 - t):.0f}%)"


def main():
    weeks = fetch_weeks()
    W = len(weeks)
    mx = max(max(c) for c in weeks) or 1
    width = PAD * 2 + W * STEP - GAP
    height = PAD * 2 + 7 * STEP - GAP

    def pos(c, r):
        return PAD + c * STEP, PAD + r * STEP

    # comida: casillas con contribuciones; la serpiente va a buscarlas
    from collections import deque
    todo = {(c, r) for c in range(W) for r in range(7) if weeks[c][r] > 0}
    cur = (0, 3)
    path = [cur]
    foods = []  # (col,row,level,time)

    def bfs(src, goal, blocked):
        prev = {src: None}
        dq = deque([src])
        while dq:
            u = dq.popleft()
            if u == goal:
                break
            for dc, dr in ((1, 0), (0, 1), (0, -1), (-1, 0)):
                v = (u[0] + dc, u[1] + dr)
                if 0 <= v[0] < W and 0 <= v[1] < 7 and v not in prev and (v not in blocked or v == goal):
                    prev[v] = u
                    dq.append(v)
        if goal not in prev:
            return None
        out = []
        u = goal
        while u != src:
            out.append(u)
            u = prev[u]
        return out[::-1]

    if cur in todo:
        todo.discard(cur)
        foods.append((cur[0], cur[1], level(weeks[cur[0]][cur[1]], mx), 0.0))
    while todo:
        tgt = min(todo, key=lambda f: (abs(f[0] - cur[0]) + abs(f[1] - cur[1]), f[0]))
        length = min(len(foods) + 1, MAX_LEN)
        body = set(path[-length:])
        seg = bfs(cur, tgt, body) or bfs(cur, tgt, set())
        path.extend(seg)
        cur = tgt
        todo.discard(tgt)
        foods.append((tgt[0], tgt[1], level(weeks[tgt[0]][tgt[1]], mx), (len(path) - 1) * DT))
    n = len(path)
    T = n * DT
    L = min(len(foods) + 1, MAX_LEN)
    D = T + 2 + L * DT + 1.5

    css = []
    # movimiento compartido
    kf = []
    for i, (c, r) in enumerate(path):
        x, y = pos(c, r)
        kf.append(f"{i * DT / D * 100:.3f}%{{transform:translate({x}px,{y}px)}}")
    x, y = pos(*path[-1])
    kf.append(f"100%{{transform:translate({x}px,{y}px)}}")
    css.append("@keyframes mv{" + "".join(kf) + "}")

    rects = []
    # celdas
    for c in range(W):
        for r in range(7):
            x, y = pos(c, r)
            lv = level(weeks[c][r], mx)
            if lv == 0:
                rects.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="#8b949e" fill-opacity=".18"/>')
    for k, (c, r, lv, t) in enumerate(foods):
        x, y = pos(c, r)
        p = t / D * 100
        css.append(f"@keyframes f{k}{{0%,{p:.3f}%{{opacity:1;transform:scale(1)}}{p + .6:.3f}%{{opacity:0;transform:scale(.2)}}99.5%{{opacity:0}}100%{{opacity:1;transform:scale(1)}}}}")
        rects.append(f'<rect class="f" style="animation:f{k} {D:.2f}s linear infinite" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{LEVELS[lv]}"/>')

    # serpiente (segmento 0 = cabeza)
    segs = []
    for i in range(L - 1, -1, -1):
        t = 1 - i / max(L - 1, 1)
        # cuándo aparece: al comerse el i-ésimo alimento
        appear = 0 if i == 0 else foods[i - 1][3]
        a = appear / D * 100
        end = (T + 1) / D * 100
        css.append(f"@keyframes v{i}{{0%{{opacity:{1 if i == 0 else 0}}}{a:.3f}%{{opacity:{1 if i == 0 else 0}}}{a + .01:.3f}%{{opacity:1}}{end:.3f}%{{opacity:1}}{end + .5:.3f}%{{opacity:0}}100%{{opacity:0}}}}")
        size = CELL if i else CELL + 2
        off = (CELL - size) / 2
        rx = 5 if i == 0 else 4
        body = (f'<rect x="{off}" y="{off}" width="{size}" height="{size}" rx="{rx}" fill="{hsl_lerp(t)}"/>')
        if i == 0:
            body += '<circle cx="4" cy="4" r="1.6" fill="#0d1117"/><circle cx="9" cy="4" r="1.6" fill="#0d1117"/>'
        segs.append(
            f'<g style="animation:mv {D:.2f}s linear {i * DT:.2f}s infinite backwards">'
            f'<g style="animation:v{i} {D:.2f}s linear {i * DT:.2f}s infinite backwards" opacity="0">{body}</g></g>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
           f'<style>.f{{transform-box:fill-box;transform-origin:center}}{"".join(css)}</style>'
           + "".join(rects) + "".join(segs) + "</svg>")
    os.makedirs("dist", exist_ok=True)
    open("dist/snake.svg", "w").write(svg)
    open("dist/snake-dark.svg", "w").write(svg)
    print("ok", len(svg), "bytes;", len(foods), "alimentos;", L, "segmentos;", f"{D:.1f}s")


main()
