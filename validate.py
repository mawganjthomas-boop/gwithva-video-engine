"""Storyboard checks. Runs BEFORE rendering. If anything fails, the video is not made
and the reason goes back to Notion, so nothing off-brand or off-fact reaches the queue."""
import re

SCREENS = {'bookings', 'diary', 'messages', 'share', 'expenses', 'overview', 'invoice', 'export', 'jobs'}
FACT_SCENES = {'number', 'compare', 'timeline', 'checklist', 'countdown', 'scam', 'mythfact', 'qa'}
NOTIF_KINDS = {'msg', 'call', 'bell', 'cal', 'note', 'email'}

# Words that can never appear in scenes that talk about Gwithva (from the Fact Sheet NEVER CLAIM list).
BANNED_CLAIMS = [
    (r'\bvett?ed\b|\bverified\b|\bbackground[- ]check|\bdbs\b|\binsur(ed|ance)\b|\bid[- ]check', 'trust/check claims'),
    (r'\btrusted\b|\bapproved cleaners?\b|\bchecked cleaners?\b', 'trust claims'),
    (r'\bguarantee', 'guarantee'), (r'\baward', 'award'), (r'\brated\b|\bratings?\b', 'ratings'),
    (r'\bcommission\b|\bservice fee\b|\bbooking fee\b|%|\bpercent', 'fees/commission'),
    (r'\bno fees?\b|\bfee[- ]free\b|\bno lead fees?\b', '"no fees" claim'),
    (r'\binstant(ly)?\b', 'instant-booking claim'),
    (r'\brecurring\b|\breminders?\b', 'feature not built'),
    (r'\bapp store (rating|review)s?\b|\b(top|#1|number one) (rated )?app\b', 'App Store rating claim'),
    (r'\btestimonial|\breview(s|ed)? from\b', 'testimonials'),
    (r'\bthousands?\b|\bhundreds?\b|\b\d+\s*(cleaners|customers|clients|bookings|users)\b', 'user numbers'),
    (r'\bsave (you )?money\b|\bearn (more|money)\b|\bmore money\b|\bboost (your )?income\b|£', 'money saved/earned'),
    (r'\bno (more )?chasing\b|\bchase payments?\b|\bpayment chasing\b', 'no-chasing claim'),
    (r'does your (accounts|tax|books)|files? your tax|tax return for you', 'does-your-tax claim'),
    (r'gwithva\.com', 'wrong web address'),
    (r'\brevolution|\bgame[- ]chang|\bseamless\b|\bgroundbreaking\b', 'hype words'),
    (r'\bsocial (platform|network)\b', 'social platform'),
]
# "free" is only a problem when it is about money (free bookings, free trial, totally free...).
# Diary talk ("Friday morning is free", "free days") is fine.
FREE_BAD = re.compile(r'\b(100%|totally|completely|always|forever|absolutely|100 percent) free\b|\bfree (bookings?|leads?|jobs?|customers?|clients?|money|cash|trial|forever|for life|for customers|for clients|of charge|commission|fees?|plan|month|work|to use|to book)\b|\bfree for (everyone|customers|clients|life|ever)\b|\bfor free\b', re.I)
FREE_OK = re.compile(r'\bfree (to sign up|to download|cleaner account|account|slots?|app|on the app store|on google play|days?|dates?|time|times|hours?|evenings?|mornings?|afternoons?|weekends?|week|gaps?|spaces?|spots?)\b|\b(any|got|have|has|a|your) free\b|\bsign up (for )?free\b|\b(download|get) (gwithva |the app |it )?free\b', re.I)

LIMITS = {  # max characters
    'hook.line': 26, 'hook.punch': 22, 'pileup.keyword': 20, 'pileup.block': 16, 'notif.title': 18, 'notif.body': 46,
    'reveal.tagline': 44, 'caption': 22, 'statement.line': 20, 'statement.kicker': 28, 'payoff.line': 18,
    'cta.button': 30, 'cta.sub': 44, 'card.title': 22, 'card.who': 14, 'card.time': 13, 'msg': 64, 'client': 16,
    'entry.title': 22, 'reveal.bridge': 40, 'fact.big': 8, 'fact.line': 26, 'fact.text': 95, 'fact.item': 24, 'row.title': 28, 'row.sub': 28,
}


def _claims(text, where, errs, pound_ok=False):
    t = (text or '')
    if pound_ok: t = t.replace('£', '')
    for pat, why in BANNED_CLAIMS:
        if re.search(pat, t, re.I): errs.append(f'{where}: "{t}" breaks the Fact Sheet ({why})')
    if FREE_BAD.search(t) and not FREE_OK.search(t):
        errs.append(f'{where}: "{t}" uses "free" outside "free to sign up"/"free cleaner account"')


def _len(text, key, where, errs):
    if text is None or str(text).strip() == '': errs.append(f'{where}: empty'); return
    if len(str(text)) > LIMITS[key]: errs.append(f'{where}: "{text}" is {len(str(text))} chars (max {LIMITS[key]})')


def validate(spec):
    errs = []
    sc = spec.get('scenes') or []
    if not isinstance(sc, list) or len(sc) < 5: return ['storyboard needs at least 5 scenes']
    types = [s.get('type') for s in sc]
    if types[0] != 'hook': errs.append('first scene must be "hook"')
    if types[-1] != 'cta': errs.append('last scene must be "cta"')
    if types.count('reveal') != 1: errs.append('exactly one "reveal" scene is required')
    if types.count('pileup') > 1: errs.append('at most one "pileup" scene')
    if types.count('statement') > 2: errs.append('at most two "statement" scenes')
    if types.count('payoff') > 1: errs.append('at most one "payoff" scene')
    apps = [i for i, t in enumerate(types) if t == 'app']
    if len(apps) < 2 or len(apps) > 4: errs.append('use 2 to 4 "app" scenes')
    elif apps != list(range(apps[0], apps[0] + len(apps))): errs.append('"app" scenes must be next to each other')
    if 'reveal' in types and apps and types.index('reveal') > apps[0]: errs.append('"reveal" must come before the app scenes')
    if sum(1 for t in types if t in FACT_SCENES) > 3: errs.append('at most three fact scenes (number, compare, timeline, checklist, countdown, scam, mythfact, qa)')
    unknown = set(types) - {'hook', 'pileup', 'reveal', 'app', 'statement', 'payoff', 'cta'} - FACT_SCENES
    if unknown: errs.append(f'unknown scene types: {sorted(unknown)}')
    seen = set()
    for i, s in enumerate(sc):
        w = f'scene {i + 1} ({s.get("type")})'; ty = s.get('type')
        if ty == 'hook':
            ls = s.get('lines') or []
            if not 1 <= len(ls) <= 2: errs.append(f'{w}: 1-2 lines')
            for l in ls: _len(l, 'hook.line', w, errs)
            _len(s.get('punch'), 'hook.punch', w, errs)
            if s.get('style') not in (None, 'statement', 'pov'): errs.append(f'{w}: style must be statement or pov')
        elif ty == 'pileup':
            for k in s.get('keywords') or []: _len(k, 'pileup.keyword', w, errs)
            if not 3 <= len(s.get('keywords') or []) <= 5: errs.append(f'{w}: 3-5 keywords')
            for b in s.get('blocks') or []: _len(b, 'pileup.block', w, errs)
            if not 8 <= len(s.get('blocks') or []) <= 12: errs.append(f'{w}: 8-12 calendar blocks')
            ns = s.get('notifications') or []
            if not 7 <= len(ns) <= 11: errs.append(f'{w}: 7-11 notifications')
            for n in ns:
                if n.get('kind') not in NOTIF_KINDS: errs.append(f'{w}: notification kind must be one of {sorted(NOTIF_KINDS)}')
                _len(n.get('title'), 'notif.title', w, errs); _len(n.get('body'), 'notif.body', w, errs)
                if re.search(r'\b(bank details|sort code|password|pin)\b', n.get('body', ''), re.I): errs.append(f'{w}: avoid scam-looking messages ("{n.get("body")}")')
        elif ty == 'reveal':
            _len(s.get('tagline'), 'reveal.tagline', w, errs); _claims(s.get('tagline'), w, errs)
            if s.get('bridge'): _len(s['bridge'], 'reveal.bridge', w, errs); _claims(s['bridge'], w, errs)
        elif ty == 'app':
            scr = s.get('screen')
            if scr not in SCREENS: errs.append(f'{w}: screen must be one of {sorted(SCREENS)}'); continue
            if scr in seen: errs.append(f'{w}: screen "{scr}" used twice')
            seen.add(scr)
            cap = s.get('caption') or []
            if len(cap) != 2: errs.append(f'{w}: caption must be exactly 2 short lines')
            for c in cap: _len(c, 'caption', w, errs); _claims(c, w, errs)
            if scr == 'bookings':
                cards = s.get('cards') or []
                if len(cards) != 4: errs.append(f'{w}: exactly 4 booking cards')
                if sum(1 for c in cards if c.get('status') == 'request') != 1: errs.append(f'{w}: exactly one card with status "request"')
                for c in cards:
                    _len(c.get('title'), 'card.title', w, errs); _len(c.get('who'), 'card.who', w, errs); _len(c.get('time'), 'card.time', w, errs)
                    if not re.fullmatch(r'(MON|TUE|WED|THU|FRI|SAT|SUN)', str(c.get('day', ''))): errs.append(f'{w}: day must be MON..SUN')
                    if not re.fullmatch(r'[1-9]|[12]\d|3[01]', str(c.get('date', ''))): errs.append(f'{w}: date must be 1-31')
                    _claims(c.get('title'), w, errs)
            elif scr == 'diary':
                e = s.get('entry') or {}
                _len(e.get('title'), 'entry.title', w, errs); _len(e.get('who'), 'card.who', w, errs); _len(e.get('time'), 'card.time', w, errs)
            elif scr == 'messages':
                _len(s.get('client'), 'client', w, errs)
                ms = s.get('messages') or []
                if len(ms) != 3: errs.append(f'{w}: exactly 3 messages')
                if sum(1 for m in ms if m.get('from') == 'me') != 1: errs.append(f'{w}: exactly one message from "me" (the cleaner)')
                for m in ms:
                    _len(m.get('text'), 'msg', w, errs)
                    if re.search(r'\d{5,}|@|https?://', m.get('text', '')): errs.append(f'{w}: no phone numbers, emails or links in messages')
            elif scr in ('expenses', 'jobs'):
                for r in (s.get('items') or []) + [s.get('added') or {}]:
                    _len(r.get('title'), 'row.title', w, errs)
                if not s.get('added'): errs.append(f'{w}: needs an "added" row (the one the viewer sees being added)')
            elif scr == 'invoice':
                _len(s.get('client'), 'client', w, errs); _len(s.get('item'), 'row.title', w, errs)
            elif scr == 'share':
                r = s.get('recent') or {}
                for k, lim in (('title', 'card.title'), ('who', 'card.who'), ('time', 'card.time')):
                    if r.get(k): _len(r.get(k), lim, w, errs)
        elif ty in FACT_SCENES:
            texts = []
            if ty == 'number':
                _len(s.get('big'), 'fact.big', w, errs); texts += [s.get('big')] + list(s.get('lines') or [])
                for l in s.get('lines') or []: _len(l, 'fact.line', w, errs)
            elif ty == 'compare':
                for k in ('a', 'b'):
                    r = s.get(k) or {}; _len(r.get('label'), 'fact.line', w, errs); texts += [r.get('label'), r.get('value')]
                texts += [s.get('title'), s.get('verdict')]
            elif ty == 'timeline':
                pts = s.get('points') or []
                if not 2 <= len(pts) <= 5: errs.append(f'{w}: 2-5 points')
                for p in pts: _len(p.get('date'), 'fact.item', w, errs); texts += [p.get('date'), p.get('label')]
                texts.append(s.get('title'))
            elif ty == 'checklist':
                its = s.get('items') or []
                if not 2 <= len(its) <= 4: errs.append(f'{w}: 2-4 items')
                for i2 in its: _len(i2, 'fact.item', w, errs)
                texts += its + [s.get('title')]
            elif ty == 'countdown':
                if not re.fullmatch(r'[1-9]|[12]\d|3[01]', str(s.get('day', ''))): errs.append(f'{w}: day must be 1-31')
                texts += [s.get('label'), s.get('kicker'), s.get('month')]
            elif ty == 'scam':
                texts += [s.get('stamp')]
            elif ty == 'mythfact':
                _len(s.get('myth'), 'fact.text', w, errs); _len(s.get('fact'), 'fact.text', w, errs); texts += [s.get('myth'), s.get('fact')]
            elif ty == 'qa':
                ps = s.get('pairs') or []
                if not 1 <= len(ps) <= 2: errs.append(f'{w}: 1-2 question and answer pairs')
                for p in ps: _len(p.get('q'), 'fact.text', w, errs); _len(p.get('a'), 'fact.text', w, errs); texts += [p.get('q'), p.get('a')]
            for x in texts:
                if x: _claims(x, w, errs, pound_ok=True)
        elif ty == 'statement':
            ls = s.get('lines') or []
            if not 1 <= len(ls) <= 3: errs.append(f'{w}: 1-3 lines')
            for l in ls: _len(l, 'statement.line', w, errs); _claims(l, w, errs)
            if s.get('kicker'): _len(s['kicker'], 'statement.kicker', w, errs); _claims(s['kicker'], w, errs)
            if s.get('bg') not in (None, 'peach', 'teal', 'cream'): errs.append(f'{w}: bg must be peach, teal or cream')
        elif ty == 'payoff':
            ls = s.get('lines') or []
            if len(ls) != 2: errs.append(f'{w}: exactly 2 lines')
            for l in ls: _len(l, 'payoff.line', w, errs); _claims(l, w, errs)
        elif ty == 'cta':
            _len(s.get('button'), 'cta.button', w, errs); _claims(s.get('button'), w, errs)
            if s.get('sub'): _len(s['sub'], 'cta.sub', w, errs); _claims(s['sub'], w, errs)
    if (spec.get('music') or {}).get('mood', 'warm') not in ('warm', 'bright', 'driving', 'bounce'): errs.append('music.mood must be warm, bright, driving or bounce')
    return errs


# ---------------------------------------------------------------------------------------------------------
# v2 "blocks" engine: any structure, so the checks are about truth, readability and platform rules,
# not scene order. Every piece of text (on screen, in speech bubbles and in the voiceover) is checked.
BLOCK_KINDS = {'text', 'character', 'prop', 'bubble', 'notifs', 'checklist', 'counter', 'logo', 'cta', 'arrow', 'circle',
               'burst', 'image', 'app'}
CAST = {'kerra', 'jago', 'amira', 'dev', 'tamsin', 'ollie', 'grace'}
BLOCK_LIMITS = {'text': 90, 'bubble': 70, 'checklist.item': 28, 'voice.line': 160, 'cta.button': 30, 'cta.sub': 44}


def _block_texts(b):
    k = b.get('kind', 'text')
    if k == 'text': return [b.get('text')]
    if k == 'bubble': return [b.get('text')]
    if k == 'checklist': return list(b.get('items') or [])
    if k == 'notifs': return [n.get('body') for n in b.get('items') or []]
    if k == 'cta': return [b.get('button'), b.get('sub')]
    if k == 'app': return list(b.get('caption') or [])
    return []


APP_SCREENS = {'bookings', 'diary', 'messages', 'share', 'expenses', 'overview', 'invoice', 'export', 'jobs'}
BUBBLE_ALIASES = {'think': 'think', 'thought': 'think', 'speech': 'speech', 'say': 'speech', 'talk': 'speech', 'message': 'text', 'sms': 'text'}


def normalise_blocks(spec):
    """Fix small agent slips instead of failing the whole video. Returns notes."""
    notes = []
    allsc = list(enumerate(spec.get('scenes') or [])) + [(f'hook {j + 2} ', h) for j, h in enumerate(spec.get('hooks') or []) if isinstance(h, dict)]
    for i, s in allsc:
        i = i if isinstance(i, str) else i  # label

        keep = []
        for b in s.get('blocks') or []:
            k = b.get('kind', 'text')
            if k in BUBBLE_ALIASES:
                b['kind'] = 'bubble'
                b.setdefault('style', BUBBLE_ALIASES[k])
                notes.append(f'scene {i if isinstance(i, str) else i + 1}: block kind "{k}" changed to a {BUBBLE_ALIASES[k]} bubble')
            elif k == 'image' and str(b.get('src', '')).startswith('screen:') and str(b.get('src'))[7:] in APP_SCREENS and b.get('frame', 'phone') == 'phone':
                # a live, animated app screen with sample data looks far better than a static screenshot
                scr = str(b['src'])[7:]
                for key in ('src', 'frame', 'zoom', 'clip'): b.pop(key, None)
                b['kind'] = 'app'; b['screen'] = scr
                notes.append(f'scene {i if isinstance(i, str) else i + 1}: screenshot of {scr} swapped for the live app screen')
            elif k == 'logo' and any(x.get('kind') == 'cta' for x in s.get('blocks') or []):
                notes.append(f'scene {i if isinstance(i, str) else i + 1}: logo dropped (the end card already shows it)'); continue
            elif k not in BLOCK_KINDS:
                notes.append(f'scene {i if isinstance(i, str) else i + 1}: unknown block kind "{k}" left out'); continue
            keep.append(b)
        s['blocks'] = keep
    return notes


def validate_blocks(spec):
    errs = []
    sc = spec.get('scenes') or []
    if not isinstance(sc, list) or not 3 <= len(sc) <= 14: return ['a blocks storyboard needs 3 to 14 scenes']
    total = sum(float(s.get('dur') or 2.5) for s in sc)
    if not 6 <= total <= 45: errs.append(f'total length {total:.1f}s: keep it between 6 and 45 seconds')
    kinds_all = []
    for i, s in enumerate(sc):
        w = f'scene {i + 1}'
        d = float(s.get('dur') or 2.5)
        if not .8 <= d <= 8: errs.append(f'{w}: dur {d}s must be 0.8 to 8 seconds')
        bl = s.get('blocks') or []
        if not bl: errs.append(f'{w}: needs at least one block')
        if len(bl) > 12: errs.append(f'{w}: at most 12 blocks')
        for b in bl:
            k = b.get('kind', 'text'); kinds_all.append(k)
            if k not in BLOCK_KINDS: errs.append(f'{w}: unknown block kind "{k}"'); continue
            if k == 'character' and b.get('who') not in CAST: errs.append(f'{w}: character "{b.get("who")}" must be one of {sorted(CAST)}')
            if k == 'text' and len(str(b.get('text') or '')) > BLOCK_LIMITS['text']: errs.append(f'{w}: text "{str(b.get("text"))[:40]}..." is over {BLOCK_LIMITS["text"]} characters')
            if k == 'bubble' and len(str(b.get('text') or '')) > BLOCK_LIMITS['bubble']: errs.append(f'{w}: speech bubble over {BLOCK_LIMITS["bubble"]} characters')
            if k == 'checklist':
                for it in b.get('items') or []:
                    if len(it) > BLOCK_LIMITS['checklist.item']: errs.append(f'{w}: checklist item "{it}" over {BLOCK_LIMITS["checklist.item"]} characters')
            if k == 'cta':
                _len(b.get('button'), 'cta.button', w, errs)
                if b.get('sub'): _len(b['sub'], 'cta.sub', w, errs)
            if k == 'app' and b.get('screen') not in SCREENS: errs.append(f'{w}: app screen must be one of {sorted(SCREENS)}')
            if k == 'notifs':
                for n in b.get('items') or []:
                    _len(n.get('title'), 'notif.title', w, errs); _len(n.get('body'), 'notif.body', w, errs)
                    if re.search(r'\b(bank details|sort code|password|pin)\b', n.get('body', ''), re.I): errs.append(f'{w}: avoid scam-looking messages')
            # truth: anything said about Gwithva. Speech by customers/cleaners in a story can mention prices etc. only
            # when b["story"] is true (in-character talk that is not a Gwithva claim, e.g. "Can you do Friday?").
            for x in _block_texts(b):
                if x and not b.get('story'): _claims(str(x).replace('*', ''), w, errs)
                if x and re.search(r'!', str(x)) and k in ('text', 'cta'): errs.append(f'{w}: no exclamation marks in on-screen text ("{x}")')
    for ln in (spec.get('voice') or {}).get('lines') or []:
        t = ln.get('text') or ''
        if len(t) > BLOCK_LIMITS['voice.line']: errs.append(f'voice line "{t[:40]}..." is over {BLOCK_LIMITS["voice.line"]} characters; split it')
        if not ln.get('story'): _claims(t, 'voiceover', errs)
        if not isinstance(ln.get('scene'), int) or not 1 <= ln['scene'] <= len(sc): errs.append(f'voice line "{t[:30]}": scene must be a scene number 1-{len(sc)}')
    # platform craft rules
    first = sc[0].get('blocks') or []
    if not any(float(b.get('t') or 0) <= .2 for b in first): errs.append('scene 1: something must move in the first half-second (a block with t 0 to 0.2)')
    last = sc[-1].get('blocks') or []
    if not any(b.get('kind') == 'cta' for b in last): errs.append('the last scene must hold the end card (a "cta" block)')
    if 'logo' not in kinds_all and 'cta' not in kinds_all: errs.append('show the Gwithva logo at least once')
    if (spec.get('music') or {}).get('mood', 'bright') not in ('warm', 'bright', 'driving', 'bounce', 'cartoon'): errs.append('music.mood must be warm, bright, driving, bounce or cartoon')
    return errs
