"""
JamiiTek Website Status Middleware
====================================
Install this middleware on any Django client website managed by JamiiTek.

INSTALLATION:
1. Add to the client's settings.py:

    JAMIITEK_API_KEY = "your-api-key-from-panel"
    JAMIITEK_API_URL = "https://jamiitek.co.tz/api/site-status/"

    MIDDLEWARE = [
        ...
        'jamiitek_middleware.JamiiTekStatusMiddleware',
    ]

2. Copy this file into the root directory of the client's project
   (same folder as manage.py) and name it `jamiitek_middleware.py`.

NOTES:
- Status is cached for 5 minutes to avoid excessive API calls.
- If the API is unreachable, the site continues working (fail-open).
- Enabled features are accessible via: request.jamiitek_features
"""

import requests
import logging
from django.conf import settings
from django.http import HttpResponse
from django.core.cache import cache

logger = logging.getLogger(__name__)

SUSPENSION_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Website Suspended</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
  :root {{
    --red:#ff2244; --red2:#ff6680; --dark:#060810;
    --card:rgba(255,255,255,0.04); --border:rgba(255,34,68,0.15);
    --text:#f0f2ff; --muted:rgba(240,242,255,0.45);
    --mono:'DM Mono',monospace; --head:'Bebas Neue',cursive; --body:'Outfit',sans-serif;
  }}
  html,body {{ min-height:100vh; background:var(--dark); font-family:var(--body); color:var(--text); overflow-x:hidden; }}
  .bg-layer {{ position:fixed; inset:0; z-index:0; pointer-events:none; }}
  .bg-grid {{
    background-image:linear-gradient(rgba(255,34,68,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,34,68,0.04) 1px,transparent 1px);
    background-size:60px 60px; animation:grid-drift 20s linear infinite;
  }}
  @keyframes grid-drift {{ from{{background-position:0 0}} to{{background-position:60px 60px}} }}
  .bg-glow {{ background:radial-gradient(ellipse 80% 50% at 50% -10%,rgba(255,34,68,0.18) 0%,transparent 70%); }}
  .bg-scan {{
    background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.08) 3px,rgba(0,0,0,0.08) 4px);
    animation:scanlines 8s linear infinite;
  }}
  @keyframes scanlines {{ from{{background-position:0 0}} to{{background-position:0 100px}} }}
  .page {{ position:relative; z-index:1; min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:40px 20px; }}
  .lock-wrap {{ position:relative; margin-bottom:32px; }}
  .lock-ring {{
    width:100px; height:100px; border-radius:50%; border:2px solid rgba(255,34,68,0.3);
    display:flex; align-items:center; justify-content:center; position:relative;
    animation:pulse-ring 2.5s ease-in-out infinite;
  }}
  .lock-ring::before,.lock-ring::after {{ content:''; position:absolute; border-radius:50%; border:1px solid rgba(255,34,68,0.15); animation:expand-ring 2.5s ease-out infinite; }}
  .lock-ring::before {{ width:130px; height:130px; animation-delay:0.4s; }}
  .lock-ring::after  {{ width:160px; height:160px; animation-delay:0.8s; }}
  @keyframes pulse-ring {{
    0%,100% {{ box-shadow:0 0 0 0 rgba(255,34,68,0.3),inset 0 0 20px rgba(255,34,68,0.05); }}
    50%      {{ box-shadow:0 0 20px 4px rgba(255,34,68,0.25),inset 0 0 30px rgba(255,34,68,0.1); }}
  }}
  @keyframes expand-ring {{ 0%{{opacity:0.6;transform:scale(1)}} 100%{{opacity:0;transform:scale(1.15)}} }}
  .lock-icon {{ font-size:40px; line-height:1; filter:drop-shadow(0 0 12px rgba(255,34,68,0.8)); animation:icon-pulse 2.5s ease-in-out infinite; }}
  @keyframes icon-pulse {{
    0%,100% {{ filter:drop-shadow(0 0 12px rgba(255,34,68,0.8)); }}
    50%      {{ filter:drop-shadow(0 0 24px rgba(255,34,68,1.0)) drop-shadow(0 0 40px rgba(255,34,68,0.4)); }}
  }}
  .status-chip {{
    display:inline-flex; align-items:center; gap:8px; background:rgba(255,34,68,0.08);
    border:1px solid rgba(255,34,68,0.3); border-radius:100px; padding:6px 16px;
    font-family:var(--mono); font-size:11px; color:var(--red2); letter-spacing:2px;
    text-transform:uppercase; margin-bottom:20px;
  }}
  .status-dot {{ width:7px; height:7px; border-radius:50%; background:var(--red); box-shadow:0 0 8px var(--red); animation:blink 1.2s ease-in-out infinite; }}
  @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.2}} }}
  .heading {{ font-family:var(--head); font-size:clamp(56px,12vw,96px); line-height:0.9; letter-spacing:2px; text-align:center; color:var(--text); margin-bottom:6px; }}
  .heading .accent {{ color:var(--red); filter:drop-shadow(0 0 20px rgba(255,34,68,0.6)); }}
  .subheading {{ font-family:var(--head); font-size:clamp(18px,4vw,28px); color:var(--muted); letter-spacing:4px; text-align:center; margin-bottom:36px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:20px; padding:28px 32px; max-width:520px; width:100%; margin-bottom:28px; backdrop-filter:blur(10px); position:relative; overflow:hidden; }}
  .card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,rgba(255,34,68,0.4),transparent); }}
  .card-label {{ font-family:var(--mono); font-size:10px; color:var(--red2); letter-spacing:2px; text-transform:uppercase; margin-bottom:10px; display:flex; align-items:center; gap:6px; }}
  .card-label::before {{ content:''; width:16px; height:1px; background:var(--red); }}
  .card-message {{ font-size:15px; color:rgba(240,242,255,0.75); line-height:1.7; margin:0; }}
  .card-message strong {{ color:var(--text); font-weight:600; }}
  .info-section {{ max-width:520px; width:100%; display:flex; flex-direction:column; gap:10px; margin-bottom:32px; }}
  .info-row {{ display:flex; justify-content:space-between; align-items:center; padding:12px 16px; background:rgba(255,255,255,0.025); border:1px solid rgba(255,255,255,0.06); border-radius:10px; }}
  .info-key {{ font-family:var(--mono); font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; }}
  .info-val {{ font-size:13px; font-weight:600; color:var(--text); font-family:var(--mono); }}
  .info-val.red {{ color:var(--red); }}
  .cta-wrap {{ display:flex; gap:12px; flex-wrap:wrap; justify-content:center; margin-bottom:40px; }}
  .btn {{ display:inline-flex; align-items:center; gap:9px; padding:14px 28px; border-radius:12px; font-family:var(--body); font-size:14px; font-weight:600; text-decoration:none; transition:all 0.25s ease; }}
  .btn-primary {{ background:var(--red); color:#fff; box-shadow:0 4px 20px rgba(255,34,68,0.35); }}
  .btn-primary:hover {{ background:#ff3355; box-shadow:0 6px 30px rgba(255,34,68,0.55); transform:translateY(-2px); }}
  .btn-ghost {{ background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.12); color:var(--muted); }}
  .btn-ghost:hover {{ background:rgba(255,255,255,0.08); color:var(--text); transform:translateY(-1px); }}
  .footer {{ text-align:center; max-width:440px; border-top:1px solid rgba(255,255,255,0.06); padding-top:28px; }}
  .footer-brand {{ font-family:var(--head); font-size:20px; letter-spacing:2px; color:var(--text); margin-bottom:6px; }}
  .footer-brand span {{ color:var(--red); }}
  .footer-tagline {{ font-family:var(--mono); font-size:10px; color:var(--muted); letter-spacing:2px; text-transform:uppercase; margin-bottom:14px; }}
  .footer-links {{ display:flex; gap:20px; justify-content:center; flex-wrap:wrap; }}
  .footer-links a {{ font-size:12px; color:var(--muted); text-decoration:none; transition:color 0.2s; }}
  .footer-links a:hover {{ color:var(--text); }}
  @media(max-width:480px) {{
    .card {{ padding:20px 18px; }}
    .info-row {{ flex-direction:column; align-items:flex-start; gap:4px; }}
    .cta-wrap {{ flex-direction:column; align-items:stretch; }}
    .btn {{ justify-content:center; }}
    .footer-links {{ flex-direction:column; gap:10px; }}
  }}
</style>
</head>
<body>
<div class="bg-layer bg-grid"></div>
<div class="bg-layer bg-glow"></div>
<div class="bg-layer bg-scan"></div>
<div class="page">
  <div class="lock-wrap">
    <div class="lock-ring"><div class="lock-icon">&#128274;</div></div>
  </div>
  <div class="status-chip"><div class="status-dot"></div>Service Suspended</div>
  <h1 class="heading">WEBSITE<br><span class="accent">SUSPENDED</span></h1>
  <p class="subheading">Access Temporarily Restricted</p>
  <div class="card">
    <div class="card-label">Notice</div>
    <p class="card-message">{message}</p>
  </div>
  <div class="info-section">
    <div class="info-row"><span class="info-key">Status</span><span class="info-val red">&#9679; Suspended</span></div>
    <div class="info-row"><span class="info-key">Reason</span><span class="info-val">Hosting Payment Overdue</span></div>
    <div class="info-row"><span class="info-key">Restore Time</span><span class="info-val">Immediate upon payment</span></div>
  </div>
  <div class="cta-wrap">
    <a href="https://wa.me/255750910158?text=Hello,%20I%20would%20like%20to%20pay%20for%20my%20hosting" class="btn btn-primary" target="_blank">&#128172; Contact via WhatsApp</a>
    <a href="mailto:info@jamiitek.co.tz?subject=Hosting%20Payment" class="btn btn-ghost">&#9993; Send Email</a>
  </div>
  <div class="footer">
    <div class="footer-brand">Jamii<span>Tek</span></div>
    <div class="footer-tagline">Digital Solutions &middot; Tanzania</div>
    <div class="footer-links">
      <a href="https://jamiitek.co.tz">jamiitek.co.tz</a>
      <a href="mailto:info@jamiitek.co.tz">info@jamiitek.co.tz</a>
    </div>
  </div>
</div>
</body>
</html>"""

MAINTENANCE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Under Maintenance</title>
<style>
  *, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ display:flex; align-items:center; justify-content:center; min-height:100vh; background:#fffbeb; font-family:Arial,sans-serif; }}
  .container {{ text-align:center; background:white; padding:60px 50px; border-radius:16px; box-shadow:0 4px 30px rgba(0,0,0,0.08); max-width:500px; margin:20px; }}
  .icon {{ font-size:70px; margin-bottom:20px; }}
  h1 {{ color:#d97706; margin-bottom:15px; font-size:26px; }}
  p {{ color:#6b7280; line-height:1.7; font-size:15px; }}
  .footer {{ margin-top:35px; color:#d1d5db; font-size:12px; }}
</style>
</head>
<body>
<div class="container">
  <div class="icon">&#128295;</div>
  <h1>Under Maintenance</h1>
  <p>{message}</p>
  <div class="footer">Powered by JamiiTek</div>
</div>
</body>
</html>"""


class JamiiTekStatusMiddleware:
    """
    Checks the site's status from the JamiiTek management panel on every
    request and blocks access if the site is suspended or under maintenance.
    """

    CACHE_KEY = 'jamiitek_site_status'
    CACHE_TIMEOUT = 300  # 5 minutes
    BYPASS_PATHS = ['/admin/', '/api/', '/static/', '/media/']

    def __init__(self, get_response):
        self.get_response = get_response
        self.api_key = getattr(settings, 'JAMIITEK_API_KEY', None)
        self.api_url = getattr(
            settings, 'JAMIITEK_API_URL',
            'https://jamiitek.co.tz/api/site-status/'
        )

    def __call__(self, request):
        for path in self.BYPASS_PATHS:
            if request.path.startswith(path):
                return self.get_response(request)

        if not self.api_key:
            return self.get_response(request)

        status_data = self._get_status()

        if status_data:
            request.jamiitek_features = status_data.get('features', {})
            request.jamiitek_status = status_data.get('status', 'active')

            site_status = status_data.get('status', 'active')
            message = status_data.get(
                'suspension_message',
                'This website has been <strong>temporarily suspended</strong> due to an outstanding hosting payment. '
                'To restore access immediately, please contact <strong>JamiiTek Technologies</strong> and settle your pending balance.'
            )

            if site_status == 'suspended':
                html = SUSPENSION_HTML.format(message=message)
                return HttpResponse(html, status=503, content_type='text/html')

            elif site_status == 'maintenance':
                html = MAINTENANCE_HTML.format(message=message)
                return HttpResponse(html, status=503, content_type='text/html')

        return self.get_response(request)

    def _get_status(self):
        """Fetch site status from the JamiiTek API (cached for 5 minutes)."""
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return cached

        try:
            url = f"{self.api_url.rstrip('/')}/{self.api_key}/"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                cache.set(self.CACHE_KEY, data, self.CACHE_TIMEOUT)
                return data
        except Exception as e:
            logger.warning(f"JamiiTek: Could not reach status API: {e}")

        return None


def is_feature_enabled(request, feature_key):
    """
    Helper: check whether a specific feature is enabled for this site.

    Usage in views:
        from jamiitek_middleware import is_feature_enabled

        def my_view(request):
            if not is_feature_enabled(request, 'ecommerce'):
                return HttpResponse("This feature is not available.")
            ...

    Returns True by default if the feature is not listed (fail-open).
    """
    features = getattr(request, 'jamiitek_features', {})
    return features.get(feature_key, True)