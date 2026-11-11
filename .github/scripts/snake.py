import json, os, sys, random, urllib.request

USER = os.environ.get("GITHUB_USER", "JIMENEZ45")
CELL, GAP = 12, 4
PADX, PADY = 78, 64
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
    width = PADX * 2 + W * STEP - GAP
    height = PADY * 2 + 7 * STEP - GAP

    def pos(c, r):
        return PADX + c * STEP, PADY + r * STEP

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
    # al terminar, la serpiente va al hoyo de salida (borde derecho)
    exit_cell = (W - 1, 3)
    length = min(len(foods) + 1, MAX_LEN)
    seg = bfs(cur, exit_cell, set(path[-length:])) or bfs(cur, exit_cell, set()) or []
    path.extend(seg)
    n = len(path)
    t_exit = (n - 1) * DT
    L = min(len(foods) + 1, MAX_LEN)
    D = t_exit + L * DT + 3.0
    T = t_exit

    def pc(t):
        return t / D * 100

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


    # portales grandes: entrada (izquierda, cian) y salida (derecha, rosa)
    def hole(cell, color, color2, o, c_end, name):
        x, y = pos(*cell)
        cx, cy = x + CELL / 2, y + CELL / 2
        css.append(f"@keyframes {name}{{0%,{pc(o):.3f}%{{opacity:0;transform:scale(0)}}{pc(o + .8):.3f}%{{opacity:1;transform:scale(1)}}"
                   f"{pc(c_end):.3f}%{{opacity:1;transform:scale(1)}}{pc(c_end + .8):.3f}%{{opacity:0;transform:scale(0)}}100%{{opacity:0}}}}")
        rings = ""
        for k, (rx, ry, dash, sp) in enumerate([(62, 46, "26 18", 9), (50, 37, "14 16", 6), (38, 28, "30 10", 8), (27, 20, "10 12", 4)]):
            col = color if k % 2 == 0 else color2
            rings += (f'<ellipse class="sp" style="animation-duration:{sp}s;animation-direction:{"normal" if k % 2 == 0 else "reverse"}" '
                      f'rx="{rx}" ry="{ry}" fill="none" stroke="{col}" stroke-width="{3.2 - k * .5:.1f}" stroke-dasharray="{dash}" stroke-linecap="round"/>')
        return (f'<g transform="translate({cx},{cy})"><g class="h" style="animation:{name} {D:.2f}s linear infinite" opacity="0">'
                f'<ellipse rx="78" ry="58" fill="url(#gl{name})"/>{rings}<ellipse rx="19" ry="13" fill="#000"/></g></g>')

    defs = "".join(f'<radialGradient id="gl{n}"><stop offset="0" stop-color="#000"/><stop offset=".5" stop-color="#1a0b2e" stop-opacity=".9"/>'
                   f'<stop offset=".8" stop-color="{c}" stop-opacity=".45"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>'
                   for n, c in (("ha", "#f472b6"), ("hb", "#38bdf8")))
    random.seed(11)
    stars = "".join(f'<circle cx="{random.uniform(0, width):.0f}" cy="{random.uniform(0, height):.0f}" r="{random.choice([.6, .9, 1.2])}" fill="#fff" '
                    f'style="animation:tw {random.uniform(2, 5):.1f}s ease-in-out {random.uniform(0, 3):.1f}s infinite"/>' for _ in range(90))
    css.append("@keyframes tw{0%,100%{opacity:.1}50%{opacity:.9}}")
    holes = (hole(exit_cell, "#f472b6", "#c084fc", max(0, t_exit - 1.4), t_exit + (L - 1) * DT + .8, "ha")
             + hole((0, 3), "#38bdf8", "#818cf8", 0, 3.0, "hb"))

    # serpiente (segmento 0 = cabeza)
    segs = []
    for i in range(L - 1, -1, -1):
        t = 1 - i / max(L - 1, 1)
        # cuándo aparece: al comerse el i-ésimo alimento
        appear = 0 if i == 0 else foods[i - 1][3]
        a = pc(appear)
        e = pc(t_exit)
        e2 = pc(t_exit + 0.35)
        if i == 0:
            vis = (f"@keyframes v0{{0%{{opacity:0;transform:scale(.2)}}{pc(.7):.3f}%{{opacity:1;transform:scale(1)}}"
                   f"{e:.3f}%{{opacity:1;transform:scale(1)}}{e2:.3f}%{{opacity:0;transform:scale(.1) rotate(200deg)}}100%{{opacity:0}}}}")
        else:
            vis = (f"@keyframes v{i}{{0%,{a:.3f}%{{opacity:0;transform:scale(.2)}}{a + .01:.3f}%{{opacity:1;transform:scale(1)}}"
                   f"{e:.3f}%{{opacity:1;transform:scale(1)}}{e2:.3f}%{{opacity:0;transform:scale(.1) rotate(200deg)}}100%{{opacity:0}}}}")
        css.append(vis)
        size = CELL if i else CELL + 2
        off = (CELL - size) / 2
        rx = 5 if i == 0 else 4
        body = (f'<rect x="{off}" y="{off}" width="{size}" height="{size}" rx="{rx}" fill="{hsl_lerp(t)}"/>')
        if i == 0:
            body += '<circle cx="4" cy="4" r="1.6" fill="#0d1117"/><circle cx="9" cy="4" r="1.6" fill="#0d1117"/>'
        segs.append(
            f'<g style="animation:mv {D:.2f}s linear {i * DT:.2f}s infinite backwards">'
            f'<g class="b" style="animation:v{i} {D:.2f}s linear {i * DT:.2f}s infinite backwards" opacity="0">{body}</g></g>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
           f'<style>.f,.b,.h{{transform-box:fill-box;transform-origin:center}}.sp{{transform-box:fill-box;transform-origin:center;animation:sp 8s linear infinite}}@keyframes sp{{to{{transform:rotate(360deg)}}}}{"".join(css)}</style>'
           + f'<defs>{defs}<radialGradient id="bgg" cx=".5" cy=".5" r=".8"><stop offset="0" stop-color="#1b1033"/><stop offset="1" stop-color="#05070d"/></radialGradient></defs>'
           + f'<rect width="{width}" height="{height}" rx="14" fill="url(#bgg)"/>' + stars + "".join(rects) + holes + "".join(segs) + "</svg>")
    os.makedirs("dist", exist_ok=True)
    open("dist/snake.svg", "w").write(svg)
    open("dist/snake-dark.svg", "w").write(svg)
    print("ok", len(svg), "bytes;", len(foods), "alimentos;", L, "segmentos;", f"{D:.1f}s")


main()
