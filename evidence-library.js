
  const rm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // The second ticker half is a visual loop clone. Keep its links out of the
  // accessibility tree and keyboard order while retaining the animation.
  document.querySelectorAll('.ticker .half[aria-hidden="true"]')
    .forEach(el => { el.inert = true; });

  // scroll reveal, respectful of reduced-motion
  if(!rm && 'IntersectionObserver' in window){
    const io = new IntersectionObserver((entries)=>{
      entries.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); }});
    },{threshold:.14});
    document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach(el=>el.classList.add('in'));
  }

  // hero chart: the risk line draws, the flag plants, the record breaks, the lead counts
  (function(){
    const path = document.getElementById('riskPath');
    if(!path) return;
    const fill = document.getElementById('riskFill');
    const flag = document.getElementById('flagGroup');
    const rec = document.getElementById('recGroup');
    const brace = document.getElementById('braceGroup');
    const count = document.getElementById('leadCount');
    const L = path.getTotalLength();
    if(rm){
      [flag,rec,brace].forEach(g=>g.setAttribute('opacity','1'));
      fill.style.opacity = '1';
      count.textContent = '21.5 mo median diagnostic lead';
      return;
    }
    path.style.strokeDasharray = L;
    path.style.strokeDashoffset = L;
    function play(){
      path.style.transition = 'none';
      path.style.strokeDashoffset = L;
      [flag,rec,brace].forEach(g=>{ g.style.transition='none'; g.setAttribute('opacity','0'); });
      fill.style.transition = 'none'; fill.style.opacity = '0';
      requestAnimationFrame(()=>requestAnimationFrame(()=>{
        path.style.transition = 'stroke-dashoffset 2.6s cubic-bezier(.4,0,.2,1)';
        path.style.strokeDashoffset = '0';
        flag.style.transition = 'opacity .5s ease .7s';
        flag.setAttribute('opacity','1');
        rec.style.transition = 'opacity .5s ease 2.5s';
        rec.setAttribute('opacity','1');
        fill.style.transition = 'opacity 1s ease 2.2s';
        fill.style.opacity = '1';
        brace.style.transition = 'opacity .4s ease 2.7s';
        brace.setAttribute('opacity','1');
        const t0 = performance.now();
        (function tick(now){
          const p = Math.min(1,(now - t0 - 2700)/900);
          if(p >= 0){ count.textContent = Math.round(21*p) + (Math.round(21*p)===1?' month':' months') + ' of warning'; }
          if(p < 1) requestAnimationFrame(tick);
        })(t0);
      }));
    }
    let played = false;
    const io2 = new IntersectionObserver((es)=>{
      es.forEach(e=>{ if(e.isIntersecting && !played){ played = true; play(); io2.unobserve(e.target); setInterval(play, 11000); }});
    },{threshold:.4});
    io2.observe(path.closest('.terminal'));
  })();

  // lead bars grow on reveal
  (function(){
    const rows = document.querySelectorAll('#leads .bar');
    if(!rows.length) return;
    const grow = ()=>rows.forEach(b=>{ b.style.width = b.dataset.w + '%'; });
    if(rm || !('IntersectionObserver' in window)){ grow(); return; }
    const io4 = new IntersectionObserver((es)=>{
      es.forEach(e=>{ if(e.isIntersecting){ grow(); io4.unobserve(e.target); }});
    },{threshold:.35});
    io4.observe(document.getElementById('leads'));
  })();

  // one fetch helper for every live element: hard timeout, never throws past the caller
  function liveJSON(url, ms){
    const ctl = new AbortController();
    const t = setTimeout(()=>ctl.abort(), ms || 9000);
    return fetch(url,{mode:'cors',signal:ctl.signal})
      .then(r=>{ if(!r.ok) throw new Error('unreachable'); return r.json(); })
      .finally(()=>clearTimeout(t));
  }
  function fmtDate(iso){
    if(!iso) return '';
    const M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const d = new Date(iso + 'T00:00:00Z');
    return d.getUTCDate() + ' ' + M[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
  }

  // the pressure tape + layer chips: one 1KB read from the public pulse.
  // the baked states are a captured 9 Aug 2026 fallback. Live data replaces
  // them when available; an unavailable news read stays unavailable, not zero.
  (function(){
    const CLS = {CALM:'st-calm',WATCH:'st-watch',ALARM:'st-alarm',SHIFT:'st-shift'};
    function shortReg(t){
      return (t||'')
        .replace(/(\d+) (?:compound|structural) flag(s?)/, '$1 flag$2')
        .replace(/(\d+) institutions? watched/, '$1 watched')
        .toUpperCase();
    }
    function paint(b, v, key){
      if(!v) return;
      const base = b.classList.contains('badge') ? 'badge' : 'st';
      if(v.error){ b.textContent = 'NO READ'; b.className = base + ' st-reg'; b.title = v.error; return; }
      if(key === 'news' && !v.state){ b.textContent = 'NO READ'; b.className = base + ' st-reg'; b.title = 'news coverage unavailable; open the endpoint for per-institution errors'; return; }
      if(v.state){ b.textContent = v.state; b.className = base + ' ' + (CLS[v.state] || 'st-reg'); }
      else if(v.register){ b.textContent = shortReg(v.register); b.className = base + ' st-reg'; b.title = v.register; }
      if(v.stale){ b.title = ((b.title || '') + ' stale print, said in the payload').trim(); }
    }
    liveJSON('https://api.liquilens.in/api/public-signals/pulse').then(d=>{
      const L = d.layers || {};
      let alarms = 0, watches = 0, asof = '';
      Object.keys(L).forEach(k=>{
        const v = L[k] || {};
        if(v.as_of && v.as_of > asof) asof = v.as_of;
        if(v.state === 'ALARM') alarms++;
        if(v.state === 'WATCH') watches++;
      });
      document.querySelectorAll('[data-pulse]').forEach(a=>{
        const b = a.querySelector('.st'); if(b) paint(b, L[a.dataset.pulse], a.dataset.pulse);
      });
      document.querySelectorAll('[data-pulse-chip]').forEach(b=>paint(b, L[b.dataset.pulseChip], b.dataset.pulseChip));
      document.querySelectorAll('[data-pulse-asof]').forEach(t=>{
        t.textContent = 'the board is live · as of ' + fmtDate(asof);
      });
      const hero = document.getElementById('heroPulse');
      if(hero) hero.textContent = 'Board live · ' + alarms + ' layer' + (alarms === 1 ? '' : 's') +
        ' at ALARM · ' + watches + ' at WATCH · as of ' + fmtDate(asof) + ' · every US bank scored since 2004';
    }).catch(()=>{});
  })();

  // fetched once, consumed by the desk chip and the live desk panel
  const seiPublic = liveJSON('https://api.seiche.info/api/public');

  // live Seiche reading: fetched from the public API in your browser; never faked
  (function(){
    const val = document.getElementById('seiVal');
    if(!val) return;
    const regime = document.getElementById('seiRegime');
    const stamp = document.getElementById('seiStamp');
    const line = document.getElementById('seiLine');
    const proof = document.getElementById('seiProof');
    seiPublic
      .then(d=>{
        const c = d.conclusion || {};
        if(typeof c.value !== 'number') throw new Error('no reading');
        val.textContent = Math.round(c.value);
        if(c.regime){ regime.textContent = c.regime; regime.className = 'sei-regime ' + c.regime; regime.hidden = false; }
        stamp.textContent = 'live from api.seiche.info · ' + (d.generated_at||'').slice(0,16).replace('T',' ') + 'Z';
        line.textContent = 'The Seiche index, 0 to 100, over the US funding basin right now. ' + (c.tell_reading ? 'The Tell reads ' + (c.tell>0?'+':'') + Math.round(c.tell) + ': ' + c.tell_reading + '.' : '');
        const p = d.proof || {};
        if(typeof p.recall === 'number'){
          proof.innerHTML = 'Its own scoreboard, stated honestly: <b>recall ' + Math.round(p.recall*100) + '%</b> on ' + p.n_events + ' labelled events, median lead <b>' + Math.round(p.median_lead_d) + ' days</b>, caveats published beside every number.';
        }
      })
      .catch(()=>{
        stamp.textContent = 'the live board did not answer from here';
        val.textContent = '—';
        line.textContent = 'No number is shown rather than a stale one. The terminal itself is one click below, and it always carries its own as of stamp.';
      });
  })();

  // the live board: the public MFI Risk Board, rendered from the public API
  (function(){
    const table = document.getElementById('mfiTable');
    if(!table) return;
    const stamp = document.getElementById('boardStamp');
    const census = document.getElementById('boardCensus');
    const scroll = document.getElementById('boardScroll');
    const fallback = document.getElementById('boardFallback');
    const tape = document.getElementById('rbiTape');
    const tapeRows = document.getElementById('tapeRows');
    const API = 'https://api.liquilens.in/api';

    function spark(trend){
      if(!trend || trend.length < 2) return '<span class="asof">first vetted quarter</span>';
      const w = 92, h = 26, pad = 3;
      const vals = trend.map(t=>t.score);
      const lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
      const span = (hi - lo) || 1;
      const pts = vals.map((v,i)=>{
        const x = pad + i * (w - 2*pad) / (vals.length - 1);
        const y = h - pad - (v - lo) / span * (h - 2*pad);
        return [x.toFixed(1), y.toFixed(1)];
      });
      const d = 'M' + pts.map(p=>p.join(',')).join(' L');
      const last = pts[pts.length-1];
      const title = trend.map(t=>t.q + ' ' + t.score.toFixed(1)).join(' → ');
      return '<svg class="spark" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="Score trajectory ' + title + '"><title>' + title + '</title><path d="' + d + '"/><circle cx="' + last[0] + '" cy="' + last[1] + '" r="2.4"/></svg>';
    }

    Promise.all([
      liveJSON(API + '/universe/mfi-board'),
      liveJSON(API + '/universe/summary').catch(()=>null)
    ]).then(function(res){
      const board = res[0], summary = res[1];
      const rows = (board.rows || []).slice().sort((a,b)=>a.score - b.score);
      if(!rows.length) throw new Error('empty');
      const tb = table.querySelector('tbody');
      tb.innerHTML = rows.map(function(r){
        const g = (r.grade === 'AAA' || r.grade === 'AA') ? r.grade : 'other';
        const shift = r.basis_shift ? '<span class="dbasis" title="the latest filing discloses a different factor set than the prior one; the change is shown, not blended">Δ basis</span>' : '';
        return '<tr>' +
          '<td class="inst-name">' + r.name.replace(/ (Limited|Private Limited|Ltd\.?)$/,'') + shift + '</td>' +
          '<td><span class="grade ' + g + '">' + r.grade + '</span></td>' +
          '<td class="score">' + r.score.toFixed(1) + '</td>' +
          '<td>' + spark(r.trend) + '</td>' +
          '<td class="asof">' + r.quarter + ' · ' + r.age_months + ' mo · ' + (r.basis||[]).join(', ') + '</td>' +
        '</tr>';
      }).join('');
      scroll.hidden = false;
      fallback.hidden = true;
      const cov = board.coverage || {};
      const maxAge = Math.max.apply(null, rows.map(r=>r.age_months));
      let c = '';
      if(summary && summary.aggregates){ c += summary.aggregates.registered_count.toLocaleString('en-IN') + ' NBFCs on the RBI register · '; }
      c += (cov.registered_mfis || 95) + ' NBFC MFIs · ' + (cov.scored || rows.length) + ' scored · every filing within ' + maxAge + ' months';
      census.textContent = c;
      stamp.textContent = 'live from api.liquilens.in · the public scoring path';
    }).catch(function(){
      stamp.textContent = 'the public board did not answer from here';
    });

    liveJSON(API + '/economic/rbi-actions').then(function(d){
      const acts = (d.data || []).slice(0,5);
      if(!acts.length) return;
      tapeRows.innerHTML = acts.map(function(a){
        return '<a href="' + a.url + '" target="_blank" rel="noopener"><span class="d">' + (a.date ? fmtDate(a.date) : '') + '</span>' + a.title + '</a>';
      }).join('');
      tape.hidden = false;
    }).catch(function(){ /* the tape stays hidden rather than empty */ });
  })();

  // the failure radar: every licence type on one API-dated board
  (function(){
    const table = document.getElementById('radarTable');
    if(!table) return;
    const stamp = document.getElementById('radarStamp');
    const census = document.getElementById('radarCensus');
    const scroll = document.getElementById('radarScroll');
    const fallback = document.getElementById('radarFallback');
    const TYPE = {bank:'Bank', sfb:'SFB', ucb:'Co-op', nbfc:'NBFC', mfi:'MFI', hfc:'HFC'};
    const TIERS = ['red','orange','yellow','green'];

    // the API is ours, but the page should stay safe even if it ever is not
    function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
    function pd(x){ return (x*100).toFixed(2) + '%'; }
    function move(d){
      if(d == null) return '<span class="mv flat">first vintage</span>';
      const bp = Math.round(d*10000);
      if(bp === 0) return '<span class="mv flat">flat</span>';
      const cls = bp > 0 ? 'up' : 'down';
      const sign = bp > 0 ? '+' : '';
      return '<span class="mv ' + cls + '">' + sign + bp + 'bp</span>';
    }

    function marketState(m){
      m = m || {};
      const state = [];
      const observed = m.observation_at || m.as_of;
      const clock = observed ? 'observed ' + fmtDate(observed) : 'observation date unstated';
      if(m.future_dated === true) state.push('future-dated');
      else if(m.stale === true) state.push('stale');
      else if(m.stale === false) state.push('within API freshness policy');
      else state.push('freshness unstated');
      if(m.clock_authority === false) state.push('clock authority false');
      if(m.knowledge_authority === false) state.push('retrieval authority false');
      if(m.admission_authority === false) state.push('admission pending');
      if(m.tier_authority === false) state.push('context only');
      else if(m.tier_authority !== true) state.push('tier authority unstated');
      const reason = m.authority_reason ? ' · ' + m.authority_reason : '';
      const unavailable = typeof m.dd !== 'number' ? (m.not_computed || 'not computed') : '';
      const retrieval = m.retrieved_at ? ' · retrieved ' + m.retrieved_at : '';
      const liability = m.liability_available_at ? ' · liability available ' + m.liability_available_at : '';
      const title = clock + ' · ' + state.join(' · ') + retrieval + liability + reason;
      const visible = [clock].concat(state).concat(unavailable ? [unavailable] : []).join(' · ');
      const value = typeof m.dd === 'number' ? m.dd.toFixed(2) : 'n/a';
      return value + '<span class="asof" title="' + esc(title) + '"> · ' + esc(visible) + '</span>';
    }

    function marketLayerState(m){
      const parts = [];
      if(m.as_of) parts.push('latest market observation ' + fmtDate(m.as_of));
      else parts.push('market observation date unstated');
      if(m.retrieved_at) parts.push('retrieved ' + m.retrieved_at);
      if(typeof m.fresh_names === 'number') parts.push(m.fresh_names + ' fresh names');
      if(typeof m.unclocked_names === 'number') parts.push(m.unclocked_names + ' unclocked names');
      if(typeof m.age_days === 'number') parts.push(Math.round(m.age_days) + 'd old');
      if(m.future_dated === true) parts.push('future-dated');
      else if(m.stale === true) parts.push('stale');
      else if(m.stale === false) parts.push('within API freshness policy');
      else parts.push('freshness unstated');
      if(m.tier_authority === true) parts.push('pack gates passed; authority evaluated per name');
      else if(m.tier_authority === false) parts.push('context only');
      else parts.push('tier authority unstated');
      if(typeof m.tier_authorized_names === 'number') parts.push(m.tier_authorized_names + ' tier-authorized names');
      if(m.authority_reason) parts.push(m.authority_reason);
      return parts.join(' · ');
    }

    liveJSON('https://api.liquilens.in/api/failure-radar/board').then(function(b){
      const rows = (b.rows || []);
      if(!rows.length) throw new Error('empty');
      const tb = table.querySelector('tbody');
      tb.innerHTML = rows.slice(0, 12).map(function(r){
        const dd = marketState(r.market);
        const why = (r.signals_fired && r.signals_fired.length) ? r.signals_fired.join(', ') : 'no signals fired';
        const tier = TIERS.indexOf(r.tier) >= 0 ? r.tier : 'green';
        return '<tr>' +
          '<td class="inst-name">' + esc(String(r.name).replace(/ (Limited|Private Limited|Ltd\.?)$/,'')) + '</td>' +
          '<td><span class="itype">' + esc(TYPE[r.inst_type] || r.inst_type) + '</span></td>' +
          '<td><span class="tier ' + tier + '" title="' + esc(why) + '">' + esc(tier.toUpperCase()) + '</span></td>' +
          '<td class="score" style="text-align:right">' + pd(r.hazard.pd_12m) + '</td>' +
          '<td style="text-align:right">' + move(r.movement && r.movement.delta_pd_12m) + '</td>' +
          '<td class="score" style="text-align:right">' + dd + '</td>' +
        '</tr>';
      }).join('');
      scroll.hidden = false;
      fallback.hidden = true;
      const t = b.tiers || {};
      const parts = ['red','orange','yellow','green'].filter(k=>t[k]).map(k=>t[k] + ' ' + k);
      let c = rows.length + ' institutions scored · ' + parts.join(' · ');
      if(b.as_of){ c += ' · board as of ' + fmtDate(b.as_of); }
      c += ' · ' + marketLayerState(b.market_layer || {});
      census.textContent = c;
      stamp.textContent = 'public API response · clocks, freshness and tier authority printed from the payload';
    }).catch(function(){
      stamp.textContent = 'the public radar did not answer from here';
    });
  })();

  // the Seiche desk panel: plumbing prints, the pre stated forecast, crunch windows, scoreboard events
  (function(){
    const body = document.getElementById('seiBoardBody');
    if(!body) return;
    const stamp = document.getElementById('seiBoardStamp');
    const fb = document.getElementById('seiBoardFallback');
    Promise.all([
      liveJSON('https://api.seiche.info/api/gauge'),
      liveJSON('https://api.seiche.info/api/overview'),
      seiPublic.catch(()=>null)
    ]).then(function(res){
      const gauge = res[0], over = res[1], pub = res[2];

      const h = (over && over.headline) || {};
      const P = [
        ['SOFR', h.sofr_pct, '%'], ['EFFR', h.effr_pct, '%'], ['IORB', h.iorb_pct, '%'],
        ['Reserves', h.reserves_b, '$B'], ['ON RRP', h.rrp_b, '$B']
      ];
      document.getElementById('seiPlumb').innerHTML = P.map(function(p){
        const cell = p[1] || {};
        const v = typeof cell.value === 'number'
          ? (p[2] === '%' ? cell.value.toFixed(2) + '%'
             : cell.value < 10 ? cell.value.toFixed(1)
             : Math.round(cell.value).toLocaleString('en-US'))
          : '·';
        return '<div><span class="k">' + p[0] + (p[2] === '$B' ? ' $B' : '') + '</span><span class="v">' + v + '</span><span class="a">' + (cell.asof || '') + '</span></div>';
      }).join('');

      const t = gauge.next_turn || {};
      if(typeof t.forecast_bp === 'number'){
        document.getElementById('turnBp').textContent = (t.forecast_bp >= 0 ? '+' : '') + t.forecast_bp.toFixed(1) + ' bp';
        const band = t.band_bp || [];
        const dots = Array.from({length:5},(_,i)=>'<i class="' + (i < (t.severity||0) ? 'on' : '') + '"></i>').join('');
        document.getElementById('turnBand').innerHTML = (band.length === 2 ? 'band ' + band[0] + ' to +' + band[1] + ' bp · ' : '') + 'severity <span class="sevdots">' + dots + '</span> ' + (t.severity||0) + ' of 5';
        document.getElementById('turnNote').textContent = 'The repo rate turn expected at ' + (t.mode||'').replace(/_/g,' ') + ', ' + fmtDate(t.date) + '. Published before the date, sealed in the record, scored after. That is the whole method.';
      }

      const cw = gauge.crunch_windows || [];
      document.getElementById('seiCrunch').innerHTML = cw.slice(0,3).map(function(w){
        return '<li><span class="cd">' + fmtDate(w.date) + '</span><span class="cr">' + w.reason + '</span></li>';
      }).join('') || '<li><span class="cd">none</span><span class="cr">no dated pressure points on the calendar right now</span></li>';

      const eps = (pub && pub.proof && pub.proof.episodes) || [];
      if(eps.length > 1){
        const times = eps.map(e=>new Date(e.date).getTime());
        const t0 = Math.min.apply(null,times), t1 = Math.max.apply(null,times);
        document.getElementById('evLine').innerHTML = eps.map(function(e){
          const x = ((new Date(e.date).getTime() - t0) / (t1 - t0)) * 100;
          const oos = e.in_sample === false;
          const edge = x > 72 ? ' tip-left' : (x < 10 ? ' tip-right' : '');
          return '<span class="ev-dot' + (oos ? ' oos' : '') + edge + '" tabindex="0" style="left:' + x.toFixed(1) + '%"><span class="tip">' + e.episode.split('(')[0].trim() + (oos ? ' · held-out episode; construction-PIT' : '') + '</span></span>';
        }).join('');
        document.getElementById('evStart').textContent = new Date(t0).getUTCFullYear();
        document.getElementById('evEnd').textContent = new Date(t1).getUTCFullYear();
      }

      body.hidden = false;
      stamp.textContent = 'live from api.seiche.info · ' + (gauge.generated_at||'').slice(0,16).replace('T',' ') + 'Z';
    }).catch(function(){
      fb.hidden = false;
      stamp.textContent = 'the terminal did not answer from here';
    });
  })();

  // the ticker earns its keep: real prints appended when the data plane answers
  (function(){
    const halves = document.querySelectorAll('#tickerTrack .half');
    if(!halves.length) return;
    const API = 'https://api.liquilens.in/api/economic';
    Promise.all([liveJSON(API + '/fx').catch(()=>null), liveJSON(API + '/rates').catch(()=>null)]).then(function(res){
      const fx = ((res[0]||{}).data)||[], rates = ((res[1]||{}).data)||[];
      const pick = (arr, ind)=>{ const r = arr.find(x=>x.indicator===ind); return r ? r.value : null; };
      const items = [];
      const usdinr = pick(fx,'fx_USD_INR'); if(usdinr) items.push(['USD/INR', usdinr.toFixed(2)]);
      const eurinr = pick(fx,'fx_EUR_INR'); if(eurinr) items.push(['EUR/INR', eurinr.toFixed(2)]);
      const t10 = pick(rates,'DGS10'); if(t10) items.push(['US 10Y', t10.toFixed(2)+'%']);
      const hy = pick(rates,'BAMLH0A0HYM2'); if(hy) items.push(['US HY OAS', Math.round(hy*100)+' bp']);
      const vix = pick(rates,'VIXCLS'); if(vix) items.push(['VIX', vix.toFixed(1)]);
      if(!items.length) return;
      const html = items.map(i=>'<span>' + i[0] + ' <b class="live">' + i[1] + '</b></span>').join('') + '<span class="tag sei-print">live prints via our data plane</span>';
      halves.forEach(h=>{ h.insertAdjacentHTML('beforeend', html); });
    }).catch(function(){ /* the indicative rates stand alone */ });
  })();

  // LCR countdown — runs entirely client-side, nothing leaves the page
  (function(){
    const THRESHOLD = 5000; // ₹ crore, published planning threshold; classification still controls applicability
    const btn = document.getElementById('lcrRun');
    if(!btn) return;
    const out = document.getElementById('lcrOut');
    const head = document.getElementById('lcrHeadline');
    const sub = document.getElementById('lcrSub');
    const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    function run(){
      const a = parseFloat(document.getElementById('lcrAssets').value);
      const g = parseFloat(document.getElementById('lcrGrowth').value);
      if(!(a > 0)){ head.innerHTML = 'Enter your total assets to start.'; sub.textContent=''; out.hidden = false; return; }
      if(a >= THRESHOLD){
        head.innerHTML = 'You are at or above the published <b>₹5,000 crore asset threshold.</b>';
        sub.textContent = 'This planning screen is at or above the published ₹5,000 crore asset threshold. Confirm the entity’s RBI classification and applicable requirements.';
        out.hidden = false; return;
      }
      if(!(g > 0)){
        head.innerHTML = 'At flat or negative growth, you stay below the line.';
        sub.textContent = 'The countdown starts the day growth resumes. Most books do not stay flat for long.';
        out.hidden = false; return;
      }
      const months = Math.ceil(12 * Math.log(THRESHOLD / a) / Math.log(1 + g/100));
      const d = new Date(); d.setMonth(d.getMonth() + months);
      const when = MONTHS[d.getMonth()] + ' ' + d.getFullYear();
      const yrs = Math.floor(months/12), rem = months%12;
      const span = (yrs>0 ? yrs + (yrs===1?' year ':' years ') : '') + (rem>0 ? rem + (rem===1?' month':' months') : '').trim();
      head.innerHTML = 'At that pace you cross ₹5,000 crore around <b>' + when + '</b>.';
      sub.textContent = 'That is roughly ' + (span || months + ' months') + ' away. Use the estimate to plan early, then confirm the entity’s RBI classification and applicable requirements.';
      out.hidden = false;
    }
    btn.addEventListener('click', run);
    ['lcrAssets','lcrGrowth'].forEach(id=>document.getElementById(id).addEventListener('keydown',e=>{ if(e.key==='Enter') run(); }));
  })();


(function(){
  'use strict';
  var rm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // scroll playhead — one rAF, transform only
  (function(){
    var bar = document.getElementById('scrollProgress');
    if(!bar || rm) return;
    var raf = 0;
    function paint(){
      raf = 0;
      var doc = document.documentElement;
      var max = doc.scrollHeight - window.innerHeight;
      bar.style.setProperty('--sp', max > 0 ? Math.min(1, window.scrollY / max) : 0);
    }
    window.addEventListener('scroll', function(){ if(!raf) raf = requestAnimationFrame(paint); }, {passive:true});
    paint();
  })();

  // Warning horizon: visible evidence chapters drive the decorative stage.
  (function(){
    var sec = document.getElementById('leadtime');
    if(!sec || rm) return;
    var num = document.getElementById('tmNum');
    var phase = document.getElementById('tmPhase');
    var stepNo = document.getElementById('tmStep');
    var stage = sec.querySelector('.tminus__stage');
    var steps = Array.prototype.slice.call(sec.querySelectorAll('.tminus__chapter'));
    var marks = Array.prototype.slice.call(sec.querySelectorAll('.tminus__mark'));
    if(!num || !phase || !stepNo || !stage || steps.length !== marks.length) return;

    var current = null;
    function activate(step){
      if(!step || step === current) return;
      current = step;
      var index = steps.indexOf(step);
      var progress = Number(step.dataset.progress);

      steps.forEach(function(candidate){
        var active = candidate === step;
        candidate.classList.toggle('is-current', active);
        if(active) candidate.setAttribute('aria-current', 'step');
        else candidate.removeAttribute('aria-current');
      });
      marks.forEach(function(mark, markIndex){
        mark.classList.toggle('is-active', markIndex === index);
        mark.classList.toggle('is-passed', markIndex < index);
      });

      stage.classList.add('is-changing');
      num.textContent = step.dataset.month;
      phase.textContent = step.dataset.phase;
      stepNo.textContent = String(index + 1).padStart(2, '0');
      sec.style.setProperty('--tp', String(progress));
      requestAnimationFrame(function(){ stage.classList.remove('is-changing'); });
    }

    sec.setAttribute('data-enhanced', 'true');
    activate(steps[0]);
    var raf = 0;
    function sync(){
      raf = 0;
      var focus = window.innerHeight * .5;
      var nearest = steps[0], distance = Infinity;
      steps.forEach(function(step){
        var rect = step.getBoundingClientRect();
        var nextDistance = Math.abs((rect.top + rect.bottom) * .5 - focus);
        if(nextDistance < distance){ nearest = step; distance = nextDistance; }
      });
      activate(nearest);
    }
    function queue(){ if(!raf) raf = requestAnimationFrame(sync); }
    window.addEventListener('scroll', queue, {passive:true});
    window.addEventListener('resize', queue, {passive:true});
    sync();
  })();
})();
