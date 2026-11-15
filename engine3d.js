/* ORONORTE · The engine, live. WebGL2 renderer: galaxy, faceted POLARIS, the Founder's mind,
   agents as glass worlds, a ledger that stacks gold, bloom and a holographic HUD. No libraries.
   Falls back to the 2D canvas version when WebGL2 is not available. */
(function () {
  const box = document.getElementById('orrery'), cv = document.getElementById('orc');
  const gl = cv && cv.getContext('webgl2', {antialias: true, alpha: false, powerPreference: 'high-performance'});
  if (!gl) { if (window.make2DOrrery) window.oEngine = window.make2DOrrery(); return; }
  const hud = document.createElement('canvas'); hud.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none';
  box.insertBefore(hud, cv.nextSibling); const hx = hud.getContext('2d');
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- math ----------
  const M = {
    persp(f, a, n, fr) { const t = 1 / Math.tan(f / 2), nf = 1 / (n - fr); return [t / a, 0, 0, 0, 0, t, 0, 0, 0, 0, (fr + n) * nf, -1, 0, 0, 2 * fr * n * nf, 0]; },
    look(e, c, u) { let z = norm(sub(e, c)), x = norm(cross(u, z)), y = cross(z, x);
      return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1]; },
    mul(a, b) { const o = new Array(16); for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k]; o[i * 4 + j] = s; } return o; },
    trs(p, ry, s, rx) { const c = Math.cos(ry), n = Math.sin(ry), cx = Math.cos(rx || 0), sx = Math.sin(rx || 0);
      const m = M.mul([c, 0, -n, 0, 0, 1, 0, 0, n, 0, c, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, cx, sx, 0, 0, -sx, cx, 0, 0, 0, 0, 1]);
      for (let i = 0; i < 12; i++) m[i] *= s; m[12] = p[0]; m[13] = p[1]; m[14] = p[2]; return m; },
    xf(m, p) { const x = p[0], y = p[1], z = p[2], w = m[3] * x + m[7] * y + m[11] * z + m[15];
      return [(m[0] * x + m[4] * y + m[8] * z + m[12]) / w, (m[1] * x + m[5] * y + m[9] * z + m[13]) / w, (m[2] * x + m[6] * y + m[10] * z + m[14]) / w, w]; }
  };
  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; } function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; } function norm(a) { const l = Math.hypot(...a) || 1; return a.map(v => v / l); }

  // ---------- GL helpers ----------
  function sh(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; }
  function prog(vs, fs) { const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, '#version 300 es\nprecision highp float;\n' + vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, '#version 300 es\nprecision highp float;\n' + fs));
    gl.linkProgram(p); if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p)); const u = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const a = gl.getActiveUniform(p, i); u[a.name] = gl.getUniformLocation(p, a.name); } return {p, u}; }
  function vao(attrs, dynamic) { const v = gl.createVertexArray(); gl.bindVertexArray(v); const bufs = [];
    attrs.forEach(([loc, data, size]) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, dynamic ? gl.DYNAMIC_DRAW : gl.STATIC_DRAW);
      gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0); bufs.push(b); });
    gl.bindVertexArray(null); return {v, bufs, n: attrs[0][1].length / attrs[0][2]}; }
  function update(o, i, data) { gl.bindBuffer(gl.ARRAY_BUFFER, o.bufs[i]); gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW); }

  // ---------- shaders ----------
  const SKY = prog(`layout(location=0) in vec2 p; out vec2 uv; void main(){ uv=p*.5+.5; gl_Position=vec4(p,0.,1.); }`,
   `in vec2 uv; out vec4 o; uniform float t; uniform vec2 off; uniform float asp;
    float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
    float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<6;i++){v+=a*n(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}
    void main(){ vec2 q=(uv-.5)*vec2(asp,1.)*1.6+off; float a=fbm(q*1.3+vec2(t*.01,0.)); float b=fbm(q*2.1-vec2(0.,t*.008)+a);
      vec3 c=vec3(.008,.010,.022);
      c+=vec3(.30,.12,.46)*pow(smoothstep(.36,1.,fbm(q*1.1+b)),1.4)*1.25;
      c+=vec3(.03,.22,.30)*pow(smoothstep(.40,1.,fbm(q*1.6-b+3.)),1.6)*1.15;
      c+=vec3(.42,.30,.10)*pow(smoothstep(.62,1.,b),2.)*.45;
      float v=length(uv-.5); c*=1.-v*v*1.1; o=vec4(c,1.); }`);
  const PTS = prog(`layout(location=0) in vec3 p; layout(location=1) in vec4 col; layout(location=2) in float sz;
    uniform mat4 vp, m; uniform float k, t; out vec4 vc;
    void main(){ vec4 w=m*vec4(p,1.); gl_Position=vp*w; gl_PointSize=clamp(sz*k/gl_Position.w,1.,220.); vc=col; vc.a*=.75+.25*sin(t*1.7+p.x*31.+p.z*17.); }`,
   `in vec4 vc; out vec4 o; void main(){ vec2 d=gl_PointCoord-.5; float r=dot(d,d)*4.; float a=exp(-r*4.)+exp(-r*40.)*.6; o=vec4(vc.rgb*a*vc.a,1.); }`);
  const LIN = prog(`layout(location=0) in vec3 p; layout(location=1) in float a; uniform mat4 vp, m; out float va; void main(){ va=a; gl_Position=vp*m*vec4(p,1.); }`,
   `in float va; uniform vec4 c; out vec4 o; void main(){ o=vec4(c.rgb*c.a*va,1.); }`);
  const MESH = prog(`layout(location=0) in vec3 p; layout(location=1) in vec3 nn; uniform mat4 vp, m; out vec3 wp, wn;
    void main(){ vec4 w=m*vec4(p,1.); wp=w.xyz; wn=normalize(mat3(m)*nn); gl_Position=vp*w; }`,
   `in vec3 wp, wn; out vec4 o; uniform vec3 eye, base, emis; uniform float metal, rough, rim;
    void main(){ vec3 n=normalize(wn), v=normalize(eye-wp); if(dot(n,v)<0.) n=-n;
      vec3 L1=normalize(vec3(-.5,.9,.4)), L2=normalize(vec3(.7,.2,-.6));
      float d=max(dot(n,L1),0.)*.9+max(dot(n,L2),0.)*.35+.08;
      float sp=pow(max(dot(n,normalize(L1+v)),0.),mix(90.,12.,rough))*1.6+pow(max(dot(n,normalize(L2+v)),0.),40.)*.5;
      vec3 r=reflect(-v,n); vec3 env=mix(vec3(.05,.04,.08),vec3(1.,.86,.55),smoothstep(-.2,.9,r.y))+vec3(.2,.3,.6)*smoothstep(.3,1.,-r.z)*.3;
      float fr=pow(1.-max(dot(n,v),0.),3.);
      vec3 col=base*d*(1.-metal*.6)+mix(vec3(1.),base,metal)*sp+env*base*metal*.55+vec3(1.,.85,.5)*fr*rim+emis;
      o=vec4(col,1.); }`);
  const BRIGHT = prog(`layout(location=0) in vec2 p; out vec2 uv; void main(){ uv=p*.5+.5; gl_Position=vec4(p,0.,1.); }`,
   `in vec2 uv; uniform sampler2D s; out vec4 o; void main(){ vec3 c=texture(s,uv).rgb; float l=max(max(c.r,c.g),c.b); o=vec4(c*smoothstep(.45,1.,l),1.); }`);
  const BLUR = prog(`layout(location=0) in vec2 p; out vec2 uv; void main(){ uv=p*.5+.5; gl_Position=vec4(p,0.,1.); }`,
   `in vec2 uv; uniform sampler2D s; uniform vec2 dir; out vec4 o; void main(){ vec3 c=texture(s,uv).rgb*.2270;
     c+=(texture(s,uv+dir*1.3846).rgb+texture(s,uv-dir*1.3846).rgb)*.3162; c+=(texture(s,uv+dir*3.2308).rgb+texture(s,uv-dir*3.2308).rgb)*.0702; o=vec4(c,1.); }`);
  const COMP = prog(`layout(location=0) in vec2 p; out vec2 uv; void main(){ uv=p*.5+.5; gl_Position=vec4(p,0.,1.); }`,
   `in vec2 uv; uniform sampler2D s, b1, b2; uniform float t; out vec4 o;
    void main(){ vec2 d=(uv-.5); float ca=.0016*length(d)*2.;
      vec3 c=vec3(texture(s,uv+d*ca).r,texture(s,uv).g,texture(s,uv-d*ca).b);
      c+=texture(b1,uv).rgb*1.15+texture(b2,uv).rgb*.9;
      c=c/(1.+c*.18); c=pow(c,vec3(.95));
      float g=fract(sin(dot(uv*vec2(1920.,1080.)+t,vec2(12.9898,78.233)))*43758.5453); c+=(g-.5)*.012;
      c*=1.-dot(d,d)*.55; o=vec4(c,1.); }`);

  // ---------- geometry ----------
  const quad = vao([[0, new Float32Array([-1, -1, 3, -1, -1, 3]), 2]]);
  function points(arr) { const P = [], C = [], S = []; arr.forEach(a => { P.push(...a.p); C.push(...a.c); S.push(a.s); });
    return vao([[0, new Float32Array(P), 3], [1, new Float32Array(C), 4], [2, new Float32Array(S), 1]], true); }
  const rnd = Math.random;
  // star shell
  const shell = points(Array.from({length: 2600}, () => { const u = rnd() * 2 - 1, th = rnd() * 6.283, r = 18 + rnd() * 10, q = Math.sqrt(1 - u * u), w = rnd();
    return {p: [r * q * Math.cos(th), r * u, r * q * Math.sin(th)], c: w < .8 ? [.95, .92, .85, .5 + rnd() * .5] : w < .9 ? [.7, .75, 1, .8] : [1, .85, .6, .9], s: .9 + rnd() * 1.6}; }));
  // galaxy: three arms, a bright core
  const gal = points(Array.from({length: 26000}, (_, i) => { const arm = i % 3, d = Math.pow(rnd(), .55) * 6, a = arm * 2.094 + d * 1.1 + (rnd() - .5) * .7 * (1.3 - d / 6);
    const y = (rnd() - .5) * .25 * Math.exp(-d * .4), core = d < 1.1, w = rnd();
    const c = core ? [1, .9, .7, .6] : w < .55 ? [.95, .9, .82, .35] : w < .8 ? [.65, .58, 1, .4] : [.5, .85, 1, .4];
    return {p: [d * Math.cos(a), y, d * Math.sin(a)], c, s: core ? 2.2 + rnd() * 2 : .7 + rnd() * 1.3}; }));
  // meshes
  function mesh(P, N) { return vao([[0, new Float32Array(P), 3], [1, new Float32Array(N), 3]]); }
  function icosphere(det) { const t = (1 + Math.sqrt(5)) / 2; let V = [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]].map(norm);
    let F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]];
    for (let k = 0; k < det; k++) { const cache = {}, mid = (a, b) => { const key = a < b ? a + '_' + b : b + '_' + a; if (cache[key] == null) { V.push(norm(V[a].map((v, i) => (v + V[b][i]) / 2))); cache[key] = V.length - 1; } return cache[key]; };
      F = F.flatMap(([a, b, c]) => { const ab = mid(a, b), bc = mid(b, c), ca = mid(c, a); return [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]; }); }
    const P = [], N = []; F.forEach(f => f.forEach(i => { P.push(...V[i]); N.push(...V[i]); })); return mesh(P, N); }
  const sphere = icosphere(3);
  // faceted north star
  const star = (() => { const L = .62, LZ = .3, W = .12, tips = [[0, L, 0], [0, -L, 0], [L, 0, 0], [-L, 0, 0], [0, 0, LZ], [0, 0, -LZ]], wa = [];
    for (const a of [-1, 1]) for (const b of [-1, 1]) for (const c of [-1, 1]) wa.push([a * W, b * W, c * W]);
    const P = [], N = []; tips.forEach(tp => { const k = tp.findIndex(v => v !== 0), sg = Math.sign(tp[k]), ws = wa.filter(w => Math.sign(w[k]) === sg), o = [0, 1, 2].filter(i => i !== k);
      ws.sort((A, B) => Math.atan2(A[o[1]], A[o[0]]) - Math.atan2(B[o[1]], B[o[0]]));
      for (let i = 0; i < 4; i++) { const a = tp, b = ws[i], c = ws[(i + 1) % 4]; let n = norm(cross(sub(b, a), sub(c, a))); if (dot(n, a) < 0) n = n.map(v => -v); P.push(...a, ...b, ...c); N.push(...n, ...n, ...n); } });
    return mesh(P, N); })();
  const coin = (() => { const P = [], N = [], R = 1, H = .28, S = 28; for (let i = 0; i < S; i++) { const a = i / S * 6.283, b = (i + 1) / S * 6.283, ca = Math.cos(a), sa = Math.sin(a), cb = Math.cos(b), sb = Math.sin(b);
      P.push(0, H, 0, R * ca, H, R * sa, R * cb, H, R * sb); N.push(0, 1, 0, 0, 1, 0, 0, 1, 0);
      P.push(R * ca, 0, R * sa, R * cb, 0, R * sb, R * cb, H, R * sb, R * ca, 0, R * sa, R * cb, H, R * sb, R * ca, H, R * sa); N.push(ca, 0, sa, cb, 0, sb, cb, 0, sb, ca, 0, sa, cb, 0, sb, ca, 0, sa);
      P.push(0, 0, 0, R * cb, 0, R * sb, R * ca, 0, R * sa); N.push(0, -1, 0, 0, -1, 0, 0, -1, 0); } return mesh(P, N); })();
  function loop(r, seg, tilt, ticks) { const P = [], A = []; for (let i = 0; i < seg; i++) { const a = i / seg * 6.283, b = (i + 1) / seg * 6.283;
      P.push(r * Math.cos(a), r * Math.sin(a) * (tilt || 0), r * Math.sin(a), r * Math.cos(b), r * Math.sin(b) * (tilt || 0), r * Math.sin(b)); A.push(1, 1);
      if (ticks && i % ticks === 0) { P.push(r * Math.cos(a), 0, r * Math.sin(a), (r + .06) * Math.cos(a), 0, (r + .06) * Math.sin(a)); A.push(1, .2); } }
    return vao([[0, new Float32Array(P), 3], [1, new Float32Array(A), 1]]); }
  const orbit = loop(2.2, 180), ringS = loop(1, 64), hudRing = loop(1, 120, 0, 5), padRing = loop(1, 96);
  const floor = (() => { const P = [], A = []; const R = 6; for (let i = -12; i <= 12; i++) for (let s = -1; s <= 1; s += 2) { const v = i * .5;
      for (let j = -12; j < 12; j++) { const u0 = j * .5, u1 = (j + 1) * .5, fa = p => Math.max(0, 1 - Math.hypot(p[0], p[2]) / R);
        const a = s < 0 ? [v, 0, u0] : [u0, 0, v], b = s < 0 ? [v, 0, u1] : [u1, 0, v]; P.push(...a, ...b); A.push(fa(a), fa(b)); } }
    return vao([[0, new Float32Array(P), 3], [1, new Float32Array(A), 1]]); })();
  // Founder: folded light brain
  const brain = (() => { const P = [], A = [], seg = (pts) => { for (let i = 0; i < pts.length - 1; i++) { P.push(...pts[i], ...pts[i + 1]); A.push(1, 1); } };
    const at = (sd, u, v) => [sd * (.04 + .42 * Math.sin(u) * Math.cos(v * .92)), .32 * Math.cos(u) * Math.cos(v * .92) * (Math.cos(u) < 0 ? .7 : 1), .55 * Math.sin(v)];
    for (const sd of [-1, 1]) { for (let j = 0; j < 15; j++) { const u0 = .14 + j * .165, pts = []; for (let v = -1.38; v <= 1.381; v += .045) pts.push(at(sd, u0 + .09 * Math.sin(v * 9 + j * 1.9) * Math.sin(u0 * 2), v)); seg(pts); }
      for (let k = 0; k < 7; k++) { const v0 = -1.2 + k * .4, pts = []; for (let u = .08; u <= 2.55; u += .05) pts.push(at(sd, u, v0 + .07 * Math.sin(u * 10 + k))); seg(pts); } }
    return vao([[0, new Float32Array(P), 3], [1, new Float32Array(A), 1]]); })();
  const dynPts = points([{p: [0, 0, 0], c: [0, 0, 0, 0], s: 0}]), dynLin = vao([[0, new Float32Array(6), 3], [1, new Float32Array(2), 1]], true);

  // ---------- render targets ----------
  let W = 0, H = 0, dpr = 1, fb = {};
  function tex(w, h) { const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE); return t; }
  function target(w, h, depth) { const f = gl.createFramebuffer(), t = tex(w, h); gl.bindFramebuffer(gl.FRAMEBUFFER, f); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    if (depth) { const r = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, r); gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT24, w, h); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, r); }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); return {f, t, w, h}; }
  function resize() { dpr = Math.min(devicePixelRatio || 1, 2); const w = Math.round(cv.clientWidth * dpr), h = Math.round(cv.clientHeight * dpr); if (w === W && h === H) return;
    W = w; H = h; cv.width = W; cv.height = H; hud.width = W; hud.height = H; hx.setTransform(dpr, 0, 0, dpr, 0, 0);
    fb = {scene: target(W, H, true), a: target(W >> 1, H >> 1), b: target(W >> 1, H >> 1), c: target(W >> 2, H >> 2), d: target(W >> 2, H >> 2)}; }

  // ---------- the company ----------
  const RING = ['atlas', 'vega', 'orion', 'sirius', 'lyra', 'nova'];
  const N = {polaris: [0, 0, 0], founder: [0, 1.9, 0], ledger: [0, -1.55, 0]};
  const MONEY = [29, 400, 24, 29, 300, 49, 29, 150];
  const stacks = [0, 1, 2, 3, 4, 5, 6].map(i => ({o: i === 6 ? [0, 0] : [Math.cos(i * 1.0472 + .3) * .3, Math.sin(i * 1.0472 + .3) * .3], n: i === 6 ? 9 : 3 + (i * 2) % 5}));
  const S = {yaw: .6, pitch: .32, vy: 0, vp: 0, dist: 7.4};
  let t = 0, last = 0, focus = 'polaris', hover = null, drag = null, moved = 0, packets = [], floats = [], sparks = [], total = 1240, mi = 0, running = true, VP = null, eye = null;
  const born = {at: 7, done: false, flash: 0};
  if ('IntersectionObserver' in window) new IntersectionObserver(es => es.forEach(e => running = e.isIntersecting)).observe(box);
  function layout() { RING.forEach((k, i) => { const a = i / RING.length * 6.283 + t * .04; N[k] = [2.2 * Math.cos(a), .22 * Math.sin(a * 2 + t * .4), 2.2 * Math.sin(a)]; });
    const v = N.vega, ca = t * .8; N.vega2 = [v[0] + .5 * Math.cos(ca), v[1] + .12, v[2] + .5 * Math.sin(ca)]; }
  function edges() { const e = [['atlas', 'vega', 0], ['vega', 'orion', 0], ['sirius', 'orion', 0], ['vega', 'lyra', 0], ['orion', 'ledger', 1], ['vega', 'ledger', 1], ['nova', 'ledger', 0], ['polaris', 'founder', 2], ...RING.map(k => ['polaris', k, 0])];
    if (born.done) e.push(['vega', 'vega2', 0], ['vega2', 'ledger', 1]); return e; }
  function arc(a, b, u) { const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + .7, (a[2] + b[2]) / 2], k = 1 - u;
    return [0, 1, 2].map(i => k * k * a[i] + 2 * k * u * m[i] + u * u * b[i]); }
  const COL = {0: [1, .84, .48], 1: [.45, 1, .72], 2: [.62, .74, 1]};

  function proj(p) { const q = M.xf(VP, p); return {x: (q[0] * .5 + .5) * W / dpr, y: (1 - (q[1] * .5 + .5)) * H / dpr, w: q[3], vis: q[3] > 0 && q[2] < 1}; }

  function frame() {
    requestAnimationFrame(frame); const now = performance.now(), dt = last ? Math.min(.05, (now - last) / 1000) : .016; last = now; if (!running) return; resize();
    t += RM ? 0 : dt;
    if (!drag) { S.yaw += S.vy + (RM ? 0 : .0012); S.pitch += S.vp; S.vy *= .94; S.vp *= .9; }
    S.pitch = Math.max(.05, Math.min(1.0, S.pitch));
    layout(); if (!born.done && t > born.at) { born.done = true; born.flash = 1; } born.flash = Math.max(0, born.flash - .003);
    const D = S.dist * Math.max(1, 1.2 / (W / H)); eye = [D * Math.cos(S.pitch) * Math.sin(S.yaw), D * Math.sin(S.pitch) + .2, D * Math.cos(S.pitch) * Math.cos(S.yaw)];
    VP = M.mul(M.persp(.72, W / H, .1, 200), M.look(eye, [0, .1, 0], [0, 1, 0]));
    if (!RM && Math.random() < .25) { const pool = edges().filter(e => focus === 'polaris' || e[0] === focus || e[1] === focus || (focus === 'vega' && e[0] === 'vega2')); packets.push({e: pool[Math.random() * pool.length | 0], u: 0, v: .004 + Math.random() * .005}); }

    gl.bindFramebuffer(gl.FRAMEBUFFER, fb.scene.f); gl.viewport(0, 0, W, H); gl.disable(gl.DEPTH_TEST); gl.disable(gl.BLEND);
    // sky
    gl.useProgram(SKY.p); gl.uniform1f(SKY.u.t, t); gl.uniform2f(SKY.u.off, S.yaw * .35, S.pitch * .3); gl.uniform1f(SKY.u.asp, W / H); gl.bindVertexArray(quad.v); gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
    // stars + galaxy (far away, slow)
    gl.useProgram(PTS.p); gl.uniformMatrix4fv(PTS.u.vp, false, VP); gl.uniform1f(PTS.u.k, H * .03); gl.uniform1f(PTS.u.t, t);
    gl.uniformMatrix4fv(PTS.u.m, false, M.trs([0, 0, 0], t * .002, 1)); gl.bindVertexArray(shell.v); gl.drawArrays(gl.POINTS, 0, shell.n);
    gl.uniform1f(PTS.u.k, H * .035); gl.uniformMatrix4fv(PTS.u.m, false, M.trs([-10, 6, -34], t * .012, .85, 1.25)); gl.bindVertexArray(gal.v); gl.drawArrays(gl.POINTS, 0, gal.n);
    // floor grid + orbit + HUD rings
    gl.useProgram(LIN.p); gl.uniformMatrix4fv(LIN.u.vp, false, VP);
    const line = (o, m, c, mode) => { gl.uniformMatrix4fv(LIN.u.m, false, m); gl.uniform4fv(LIN.u.c, c); gl.bindVertexArray(o.v); gl.drawArrays(mode || gl.LINES, 0, o.n); };
    line(floor, M.trs([0, -1.75, 0], 0, 1), [.85, .7, .4, .10]);
    line(orbit, M.trs([0, 0, 0], 0, 1), [1, .82, .45, .28]);
    line(hudRing, M.trs([0, 0, 0], -t * .1, 1.05), [1, .85, .5, .35]);
    line(hudRing, M.trs([0, 0, 0], t * .06, 1.35, .25), [.6, .75, 1, .16]);
    line(padRing, M.trs([0, -1.55, 0], 0, .62), [.45, 1, .72, .5]);
    line(padRing, M.trs([0, -1.55, 0], t * .2, .78), [.45, 1, .72, .2]);
    line(padRing, M.trs([0, -1.55, 0], 0, .95), [.45, 1, .72, .1]);
    // edges and packets (dynamic)
    const LP = [], LA = []; let ec = [];
    for (const [a, b, k] of edges()) { const on = focus === 'polaris' || a === focus || b === focus; for (let u = 0; u < 1; u += .05) { LP.push(...arc(N[a], N[b], u), ...arc(N[a], N[b], u + .05)); LA.push(on ? .35 : .08, on ? .35 : .08); } ec.push(k); }
    update(dynLin, 0, new Float32Array(LP)); update(dynLin, 1, new Float32Array(LA)); dynLin.n = LP.length / 3;
    line(dynLin, M.trs([0, 0, 0], 0, 1), [1, .86, .55, .5]);
    // founder brain
    line(brain, M.trs(N.founder, t * .2, 1), [.62, .74, 1, .55 + .1 * Math.sin(t * 2)]);
    // agent rings
    for (const k of RING) line(ringS, M.trs(N[k], t * .3, .34, .5), [1, .84, .5, focus === k ? .7 : .3]);
    if (born.done) line(ringS, M.trs(N.vega2, t * .5, .2 * Math.min(1, (t - born.at) / 1.5), .5), [1, .84, .5, .5]);

    // solid objects with depth
    gl.enable(gl.DEPTH_TEST); gl.disable(gl.BLEND); gl.clear(gl.DEPTH_BUFFER_BIT);
    gl.useProgram(MESH.p); gl.uniformMatrix4fv(MESH.u.vp, false, VP); gl.uniform3fv(MESH.u.eye, eye);
    const solid = (o, m, base, emis, metal, rough, rim) => { gl.uniformMatrix4fv(MESH.u.m, false, m); gl.uniform3fv(MESH.u.base, base); gl.uniform3fv(MESH.u.emis, emis); gl.uniform1f(MESH.u.metal, metal); gl.uniform1f(MESH.u.rough, rough); gl.uniform1f(MESH.u.rim, rim); gl.bindVertexArray(o.v); gl.drawArrays(gl.TRIANGLES, 0, o.n); };
    solid(star, M.trs([0, 0, 0], t * .35, 1 + .02 * Math.sin(t * 2), .32), [1, .78, .36], [.18, .12, .03], .95, .25, 1.2);
    for (const k of RING) { const hot = focus === k || hover === k; solid(sphere, M.trs(N[k], t * .2, hot ? .17 : .145), [.32, .25, .14], hot ? [.16, .11, .04] : [.05, .035, .015], .95, .18, 2.6); }
    if (born.done) solid(sphere, M.trs(N.vega2, 0, .1 * Math.min(1, (t - born.at) / 1.5)), [.95, .8, .45], [.25 + born.flash * .6, .18 + born.flash * .4, .05], .8, .3, 1.4);
    // ledger: pad + stacks
    solid(coin, M.trs([0, -1.6, 0], 0, .62).map((v, i) => i === 5 ? v * .12 : v), [.12, .14, .16], [.02, .07, .05], .9, .2, .6);
    for (const s of stacks) for (let i = 0; i < s.n; i++) solid(coin, M.trs([s.o[0], -1.55 + i * .04, s.o[1]], i * .3, .095).map((v, j) => j === 5 ? v * 1.45 : v), [1, .8, .38], i === s.n - 1 ? [.12, .08, .02] : [0, 0, 0], .95, .3, .8);

    // glows, packets, sparks (additive, depth-tested)
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE); gl.depthMask(false);
    const G = [];
    G.push({p: [0, 0, 0], c: [1, .82, .45, .9], s: 34}, {p: [0, 0, 0], c: [1, .95, .8, .9], s: 9});
    G.push({p: N.founder, c: [.55, .66, 1, .45], s: 26});
    G.push({p: N.ledger, c: [.4, 1, .7, .35], s: 24});
    for (const k of RING) G.push({p: N[k], c: [1, .8, .45, focus === k ? .7 : .4], s: focus === k ? 12 : 9});
    if (born.done) G.push({p: N.vega2, c: [1, .85, .5, .5 + born.flash], s: 6 + born.flash * 40});
    packets = packets.filter(pk => { pk.u += pk.v; if (pk.u < 1) return true; const [, b, k] = pk.e;
      if (b === 'ledger' && k === 1) { const amt = MONEY[mi++ % MONEY.length]; total += amt; const st = stacks.slice().sort((A, B) => A.n - B.n)[0];
        if (st.n < 14) st.n++; else stacks.forEach(s => s.n = Math.max(3, s.n - 6)); floats.push({p: [st.o[0], -1.55 + st.n * .04 + .25, st.o[1]], amt, life: 1}); }
      if (b === 'founder') for (let i = 0; i < 8; i++) sparks.push({p: [(Math.random() - .5) * .8, (Math.random() - .3) * .5, (Math.random() - .5) * 1.1], life: 1});
      return false; });
    for (const pk of packets) { const [a, b, k] = pk.e, c = COL[k]; for (let j = 0; j < 9; j++) { const u = Math.max(0, pk.u - j * .012); G.push({p: arc(N[a], N[b], u), c: [...c, .9 - j * .09], s: 4.2 - j * .35}); } }
    sparks = sparks.filter(s => (s.life -= .015) > 0); for (const s of sparks) G.push({p: [N.founder[0] + s.p[0], N.founder[1] + s.p[1], N.founder[2] + s.p[2]], c: [1, .9, .6, s.life], s: 3});
    const P = [], C = [], Z = []; G.forEach(g => { P.push(...g.p); C.push(...g.c); Z.push(g.s); });
    update(dynPts, 0, new Float32Array(P)); update(dynPts, 1, new Float32Array(C)); update(dynPts, 2, new Float32Array(Z));
    gl.useProgram(PTS.p); gl.uniformMatrix4fv(PTS.u.vp, false, VP); gl.uniformMatrix4fv(PTS.u.m, false, M.trs([0, 0, 0], 0, 1)); gl.uniform1f(PTS.u.k, H * .026);
    gl.bindVertexArray(dynPts.v); gl.drawArrays(gl.POINTS, 0, G.length); gl.depthMask(true); gl.disable(gl.DEPTH_TEST);

    // bloom
    gl.disable(gl.BLEND); const pass = (pr, dst, src, set) => { gl.bindFramebuffer(gl.FRAMEBUFFER, dst ? dst.f : null); gl.viewport(0, 0, dst ? dst.w : W, dst ? dst.h : H); gl.useProgram(pr.p); set && set(pr); gl.bindVertexArray(quad.v); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, src); gl.uniform1i(pr.u.s, 0); gl.drawArrays(gl.TRIANGLES, 0, 3); };
    pass(BRIGHT, fb.a, fb.scene.t);
    pass(BLUR, fb.b, fb.a.t, p => gl.uniform2f(p.u.dir, 1 / fb.a.w, 0)); pass(BLUR, fb.a, fb.b.t, p => gl.uniform2f(p.u.dir, 0, 1 / fb.a.h));
    pass(BLUR, fb.c, fb.a.t, p => gl.uniform2f(p.u.dir, 2 / fb.a.w, 0)); pass(BLUR, fb.d, fb.c.t, p => gl.uniform2f(p.u.dir, 0, 2 / fb.c.h));
    pass(BLUR, fb.c, fb.d.t, p => gl.uniform2f(p.u.dir, 3 / fb.c.w, 0)); pass(BLUR, fb.d, fb.c.t, p => gl.uniform2f(p.u.dir, 0, 3 / fb.c.h));
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, W, H); gl.useProgram(COMP.p); gl.bindVertexArray(quad.v);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, fb.scene.t); gl.uniform1i(COMP.u.s, 0);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, fb.a.t); gl.uniform1i(COMP.u.b1, 1);
    gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, fb.d.t); gl.uniform1i(COMP.u.b2, 2); gl.uniform1f(COMP.u.t, t);
    gl.drawArrays(gl.TRIANGLES, 0, 3); gl.activeTexture(gl.TEXTURE0);

    drawHud();
  }

  // ---------- holographic HUD ----------
  function lbl(k) { const L = T[lang]; return k === 'founder' ? L.n_founder : k === 'ledger' ? L.n_ledger : k === 'vega2' ? 'VEGA·II' : k.toUpperCase(); }
  function drawHud() {
    const w = W / dpr, h = H / dpr, L = T[lang]; hx.clearRect(0, 0, w, h);
    hx.textBaseline = 'middle';
    const small = w < 520;
    const tag = (k, sub, col, side) => { const q = proj(N[k]); if (!q.vis) return; const hot = focus === k || hover === k, dir = side || (q.x > w / 2 ? 1 : -1);
      if (small) { hx.textAlign = 'center'; hx.font = '600 8px Inter, sans-serif'; hx.letterSpacing = '2px'; hx.fillStyle = hot ? 'rgba(255,240,190,1)' : `rgba(${col === '233,194,90' ? '236,228,210' : col},.9)`; hx.fillText(lbl(k), q.x, q.y + (k === 'founder' ? 34 : 18)); return; }
      const off = k === 'polaris' ? 58 : 22, x1 = q.x + dir * off, y1 = q.y - off, x2 = x1 + dir * 26;
      hx.strokeStyle = `rgba(${col},${hot ? .9 : .45})`; hx.lineWidth = 1; hx.beginPath(); hx.moveTo(q.x + dir * (k === 'polaris' ? 30 : 8), q.y - (k === 'polaris' ? 30 : 8)); hx.lineTo(x1, y1); hx.lineTo(x2, y1); hx.stroke();
      hx.font = `600 ${k === 'polaris' ? 12 : 10}px Inter, sans-serif`; hx.letterSpacing = k === 'polaris' ? '5px' : '3.5px'; hx.textAlign = dir > 0 ? 'left' : 'right';
      hx.fillStyle = hot ? 'rgba(255,240,190,1)' : 'rgba(236,228,210,.92)'; hx.fillText(lbl(k), x2 + dir * 6, y1 - 6);
      if (sub) { hx.font = '400 9px "JetBrains Mono", monospace'; hx.letterSpacing = '1px'; hx.fillStyle = `rgba(${col},.75)`; hx.fillText(sub, x2 + dir * 6, y1 + 8); }
      N[k + '_q'] = q; };
    { const q = proj([0, 0, 0]); if (q.vis) { hx.textAlign = 'center'; hx.font = '600 12px Inter, sans-serif'; hx.letterSpacing = '6px'; hx.fillStyle = 'rgba(255,240,190,.98)'; hx.fillText('POLARIS', q.x + 3, q.y + (w < 520 ? -44 : 74));
      hx.font = '400 9px "JetBrains Mono", monospace'; hx.letterSpacing = '1.5px'; hx.fillStyle = 'rgba(233,194,90,.8)'; if (w >= 520) hx.fillText(L.cast.polaris[0].toUpperCase(), q.x, q.y + 90); } }
    tag('founder', '', '160,185,255', 1);
    for (const k of RING) tag(k, L.cast[k][0].toUpperCase(), '233,194,90');
    if (born.done) { const q = proj(N.vega2); if (q.vis) { N.vega2_q = q; if (born.flash > 0) { hx.globalAlpha = Math.min(1, born.flash * 2.5); hx.font = '600 10px Inter, sans-serif'; hx.letterSpacing = '3px'; hx.textAlign = 'center';
      hx.fillStyle = '#FFF0B8'; const bx = Math.max(140, Math.min(w - 140, q.x)); hx.fillText(L.e_child, bx, q.y - 30); hx.globalAlpha = 1; } } }
    // selected reticle
    const sq = focus === 'polaris' ? proj([0, 0, 0]) : proj(N[focus]); if (sq.vis) { const r = (focus === 'polaris' ? 60 : 22) + Math.sin(t * 3) * 2, a = t * .6;
      hx.strokeStyle = 'rgba(255,226,150,.85)'; hx.lineWidth = 1.2; for (let i = 0; i < 4; i++) { hx.beginPath(); hx.arc(sq.x, sq.y, r, a + i * 1.5708, a + i * 1.5708 + .5); hx.stroke(); } }
    // ledger readout
    const lq = proj([0, -1.75, 0]); if (lq.vis) { hx.textAlign = 'center'; hx.font = '600 10px Inter, sans-serif'; hx.letterSpacing = '3.5px'; hx.fillStyle = 'rgba(158,230,192,.95)';
      hx.fillText(`${lbl('ledger')} · $${total.toLocaleString('en-US')}`, lq.x, lq.y + 34); hx.font = '400 9px "JetBrains Mono", monospace'; hx.letterSpacing = '1px'; hx.fillStyle = 'rgba(142,136,120,.95)'; hx.fillText(L.e_sample.toUpperCase(), lq.x, lq.y + 50); }
    floats = floats.filter(f => (f.life -= .012) > 0).slice(-3);
    for (const f of floats) { f.p[1] += .006; const q = proj(f.p); if (!q.vis) continue; hx.globalAlpha = Math.min(1, f.life * 1.6); hx.textAlign = 'center'; hx.font = '500 13px "JetBrains Mono", monospace'; hx.letterSpacing = '0px'; hx.fillStyle = '#9EE6C0'; hx.fillText(`+$${f.amt}`, q.x, q.y); hx.globalAlpha = 1; }
    // corner telemetry
    hx.textAlign = 'left'; hx.font = '400 9px "JetBrains Mono", monospace'; hx.letterSpacing = '1.5px'; hx.fillStyle = 'rgba(233,194,90,.55)';
    hx.fillText(`SYNDICATE · ${RING.length + (born.done ? 1 : 0) + 1} AGENTS · CYCLE ${String(Math.floor(t / 4) + 1).padStart(4, '0')}`, 22, 22);
    hx.fillText(`TASKS IN FLIGHT · ${String(packets.length).padStart(2, '0')}`, 22, 38);
  }

  // ---------- interaction ----------
  function hit(e) { const r = cv.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top; let best = null, bd = 1e9;
    const cand = {polaris: proj([0, 0, 0]), founder: proj(N.founder)}; RING.forEach(k => cand[k] = proj(N[k])); if (born.done) cand.vega2 = proj(N.vega2);
    for (const k in cand) { const q = cand[k]; if (!q.vis) continue; const d = Math.hypot(q.x - px, q.y - py), lim = k === 'polaris' ? 60 : 30; if (d < lim && d < bd) { bd = d; best = k; } } return best; }
  box.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY}; moved = 0; box.classList.add('drag'); box.setPointerCapture(e.pointerId); });
  box.addEventListener('pointermove', e => { if (drag) { const dx = e.clientX - drag.x, dy = e.clientY - drag.y; moved += Math.abs(dx) + Math.abs(dy);
      S.yaw -= dx * .006; S.pitch += dy * .004; S.vy = -dx * .0008; S.vp = dy * .0004; drag = {x: e.clientX, y: e.clientY}; }
    else { hover = hit(e); box.style.cursor = hover ? 'pointer' : 'grab'; } });
  box.addEventListener('pointerup', e => { box.classList.remove('drag'); if (moved < 6) { let k = hit(e); if (k === 'vega2') k = 'vega'; if (k === 'founder') k = 'polaris'; if (k) selectAgent(k); } drag = null; });
  box.addEventListener('pointerleave', () => { hover = null; });
  cv.addEventListener('webglcontextlost', e => { e.preventDefault(); running = false; });

  try { resize(); frame(); } catch (err) { console.warn('3D engine fell back to 2D:', err); hud.remove(); const c2 = cv.cloneNode(); cv.replaceWith(c2); if (window.make2DOrrery) window.oEngine = window.make2DOrrery(); return; }
  window.oEngine = {focus: k => { focus = k; packets = []; }};
})();
