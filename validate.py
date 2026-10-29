"""Storyboard checks. Runs BEFORE rendering. If anything fails, the video is not made
and the reason goes back to Notion, so nothing off-brand or off-fact reaches the queue."""
import re

SCREENS = {'bookings', 'diary', 'messages', 'share'}
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
    (r'\bapp store\b|\biphone app\b|\bios app\b', 'App Store claim'),
    (r'\btestimonial|\breview(s|ed)? from\b', 'testimonials'),
    (r'\bthousands?\b|\bhundreds?\b|\b\d+\s*(cleaners|customers|clients|bookings|users)\b', 'user numbers'),
    (r'\bsave (you )?money\b|\bearn (more|money)\b|\bmore money\b|\bboost (your )?income\b|£', 'money saved/earned'),
    (r'\bno (more )?chasing\b|\bchase payments?\b|\bpayment chasing\b', 'no-chasing claim'),
    (r'does your (accounts|tax|books)|files? your tax|tax return for you', 'does-your-tax claim'),
    (r'gwithva\.com', 'wrong web address'),
    (r'\brevolution|\bgame[- ]chang|\bseamless\b|\bgroundbreaking\b', 'hype words'),
    (r'\bsocial (platform|network)\b', 'social platform'),
]
FREE_OK = re.compile(r'\bfree (to sign up|cleaner account|account|slots?)\b|\bsign up (for )?free\b', re.I)

LIMITS = {  # max characters
    'hook.line': 26, 'hook.punch': 22, 'pileup.keyword': 20, 'pileup.block': 16, 'notif.title': 18, 'notif.body': 46,
    'reveal.tagline': 44, 'caption': 22, 'statement.line': 20, 'statement.kicker': 28, 'payoff.line': 18,
    'cta.button': 30, 'cta.sub': 44, 'card.title': 22, 'card.who': 14, 'card.time': 13, 'msg': 64, 'client': 16,
    'entry.title': 22,
}


def _claims(text, where, errs):
    t = (text or '')
    for pat, why in BANNED_CLAIMS:
        if re.search(pat, t, re.I): errs.append(f'{where}: "{t}" breaks the Fact Sheet ({why})')
    if re.search(r'\bfree\b', t, re.I) and not FREE_OK.search(t):
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
    unknown = set(types) - {'hook', 'pileup', 'reveal', 'app', 'statement', 'payoff', 'cta'}
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
            elif scr == 'share':
                r = s.get('recent') or {}
                for k, lim in (('title', 'card.title'), ('who', 'card.who'), ('time', 'card.time')):
                    if r.get(k): _len(r.get(k), lim, w, errs)
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
    if (spec.get('music') or {}).get('mood', 'warm') not in ('warm', 'bright', 'driving'): errs.append('music.mood must be warm, bright or driving')
    return errs
