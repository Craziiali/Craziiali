/**
 * Craziiali — Shoot Planner Pushover Reminder
 *
 * Runs every hour, reads upcoming shoots from Firestore,
 * and fires a Pushover EMERGENCY alert (rings + repeats every 30s
 * until dismissed) when a shoot is ~1 hour away.
 *
 * Config (set once via Firebase CLI — never stored in code):
 *   firebase functions:config:set \
 *     pushover.token="YOUR_APP_TOKEN" \
 *     pushover.user="YOUR_USER_KEY" \
 *     pushover.site="https://your-site.com"
 */

const functions  = require('firebase-functions');
const { initializeApp }  = require('firebase-admin/app');
const { getFirestore }   = require('firebase-admin/firestore');
const https      = require('https');
const querystring = require('querystring');

initializeApp();

/* Named Firestore database (matches the client app) */
const db = getFirestore('invoice');

/* Saudi Arabia = UTC+3 (no DST) */
const TZ_OFFSET_MS = 3 * 60 * 60 * 1000;

/* ── Parse a shoot's date+time into a UTC timestamp ──────────── */
function parseShootUTC(dateStr, timeStr) {
  const dm = String(dateStr || '').match(/^(\d{4})[.\-\/](\d{1,2})[.\-\/](\d{1,2})$/);
  if (!dm) return null;
  const tm = String(timeStr || '').match(/^(\d{1,2}):(\d{2})$/);
  if (!tm) return null;
  /* Treat stored times as local Riyadh time, convert to UTC */
  return Date.UTC(+dm[1], +dm[2] - 1, +dm[3], +tm[1], +tm[2], 0) - TZ_OFFSET_MS;
}

/* ── Format HH:MM (24h) → "3:00 PM" ──────────────────────────── */
function fmt12(t) {
  const m = String(t || '').match(/^(\d{1,2}):(\d{2})$/);
  if (!m) return t;
  const h = +m[1], mn = +m[2];
  return (h % 12 || 12) + ':' + String(mn).padStart(2, '0') + ' ' + (h >= 12 ? 'PM' : 'AM');
}

/* ── Send Pushover emergency notification ────────────────────── */
function sendPushover(token, user, title, message, url) {
  return new Promise((resolve, reject) => {
    const body = querystring.stringify({
      token,
      user,
      title,
      message,
      priority : 2,     /* Emergency — repeats until dismissed */
      retry    : 30,    /* Ring again every 30 seconds         */
      expire   : 3600,  /* Keep trying for up to 1 hour        */
      sound    : 'siren',
      url      : url || '',
      url_title: 'Open Planner',
    });

    const options = {
      hostname: 'api.pushover.net',
      port    : 443,
      path    : '/1/messages.json',
      method  : 'POST',
      headers : {
        'Content-Type'  : 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(body),
      },
    };

    const req = https.request(options, (res) => {
      let raw = '';
      res.on('data', c => raw += c);
      res.on('end', () => {
        try {
          const json = JSON.parse(raw);
          if (json.status === 1) resolve(json);
          else reject(new Error('Pushover rejected: ' + raw));
        } catch(e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

/* ── Main scheduled function — runs every hour ───────────────── */
exports.checkShoots = functions.pubsub
  .schedule('every 60 minutes')
  .timeZone('Asia/Riyadh')
  .onRun(async () => {

    const cfg = functions.config().pushover || {};
    if (!cfg.token || !cfg.user) {
      functions.logger.error('Pushover config missing — run: firebase functions:config:set pushover.token="..." pushover.user="..."');
      return null;
    }

    const now        = Date.now();
    const windowMin  = now + (50 * 60 * 1000);  /* 50 min from now */
    const windowMax  = now + (70 * 60 * 1000);  /* 70 min from now */

    /* ── Read planner from Firestore ── */
    let projects = [];
    try {
      const snap = await db.collection('craziiali').doc('planner').get();
      const data = snap.exists ? snap.data() : null;
      projects = (data && data.data && data.data.projects) || [];
    } catch (e) {
      functions.logger.error('Firestore read failed', e);
      return null;
    }

    /* ── Read already-notified log (prevents duplicate alerts) ── */
    let notified = {};
    try {
      const ns = await db.collection('craziiali').doc('_pushover_log').get();
      if (ns.exists) notified = ns.data() || {};
    } catch (_) { /* non-fatal */ }

    const toFire    = [];
    const newLog    = {};

    for (const p of projects) {
      if (!p.date || !p.time) continue;
      if (p.status === 'done' || p.status === 'cancelled') continue;

      const shootUTC = parseShootUTC(p.date, p.time);
      if (!shootUTC) continue;

      /* Outside the 1-hour window? Skip. */
      if (shootUTC < windowMin || shootUTC > windowMax) continue;

      /* Already notified in the last 2 hours? Skip (dedup). */
      const lastAt = notified[String(p.id)];
      if (lastAt && (now - lastAt) < 2 * 60 * 60 * 1000) continue;

      toFire.push(p);
      newLog[String(p.id)] = now;
    }

    if (toFire.length === 0) {
      functions.logger.info('checkShoots: nothing due in 1 hour.');
      return null;
    }

    /* ── Fire one Pushover alert per upcoming shoot ── */
    const siteUrl = (cfg.site || '').replace(/\/$/, '') + '?view=planner';

    for (const p of toFire) {
      const eventTitle = [p.name, p.client].filter(Boolean).join(' · ') || 'Shoot';
      const lines = [
        `🎬 ${p.name || 'Shoot'} — ${fmt12(p.time)}`,
        p.client   ? `👤 ${p.client}`   : '',
        p.location ? `📍 ${p.location}` : '',
        p.notes    ? p.notes            : '',
      ].filter(Boolean);

      try {
        await sendPushover(cfg.token, cfg.user, '⏰ Shoot in 1 Hour', lines.join('\n'), siteUrl);
        functions.logger.info(`Pushover fired for: ${eventTitle}`);
      } catch (e) {
        functions.logger.error(`Pushover failed for: ${eventTitle}`, e);
      }
    }

    /* ── Update dedup log ── */
    if (Object.keys(newLog).length > 0) {
      await db.collection('craziiali').doc('_pushover_log').set(newLog, { merge: true });
    }

    return null;
  });
