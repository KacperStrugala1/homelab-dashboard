import json
import base64
import hashlib
import psutil
from functools import lru_cache
from datetime import timedelta
from urllib.parse import urlparse, quote_plus
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from .forms import CategoryForm, ServiceForm
from .models import Service, MediaPanel, SystemMetric, Category, ServiceStatus


NBA_SCORES_URL = "https://www.thesportsdb.com/api/v1/json/3/eventspastleague.php?id=4387"
CLEARBIT_COMPANY_SEARCH_URL = "https://autocomplete.clearbit.com/v1/companies/suggest?query={query}"
SERVICE_STATUS_CHECK_TIMEOUT = 3
SERVICE_STATUS_REFRESH_INTERVAL = timedelta(minutes=30)


def save_system_metrics():

    memory = psutil.virtual_memory()

    SystemMetric.objects.create(

        cpu_percent=psutil.cpu_percent(),

        ram_percent=memory.percent,

        disk_percent=psutil.disk_usage("/").percent
    )

def _normalize_service_query(service_name):
    return " ".join(part for part in service_name.replace("-", " ").split() if part).strip()

def get_system_stats():
    memory = psutil.virtual_memory()

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": memory.percent,
        "ram_used": round(memory.used / (1024 ** 3), 1),
        "ram_total": round(memory.total / (1024 ** 3), 1),
        "disk_percent": psutil.disk_usage("/").percent,
    }

def _service_search_queries(service_name):
    normalized_name = _normalize_service_query(service_name)
    compressed_name = normalized_name.replace(" ", "")
    words = [word for word in normalized_name.split() if word]
    generic_words = {
        "app",
        "dashboard",
        "service",
        "server",
        "panel",
        "home",
        "lab",
        "local",
        "media",
    }
    meaningful_words = [word for word in words if word.lower() not in generic_words]

    queries = [normalized_name, compressed_name]

    if meaningful_words:
        queries.append(" ".join(meaningful_words))
        queries.append(meaningful_words[0])

    if words and words[0].lower() not in {query.lower() for query in queries}:
        queries.append(words[0])

    return [query for query in queries if query]


@lru_cache(maxsize=256)
def _search_brand_domain(service_name):
    for query in _service_search_queries(service_name):
        try:
            search_url = CLEARBIT_COMPANY_SEARCH_URL.format(query=quote_plus(query))
            with urlopen(search_url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
            continue

        if not payload:
            continue

        normalized_query = _normalize_service_query(query).lower()
        compressed_query = normalized_query.replace(" ", "")

        for candidate in payload:
            candidate_name = _normalize_service_query(candidate.get("name", "")).lower()
            candidate_domain = (candidate.get("domain") or "").strip().lower()
            if not candidate_domain:
                continue

            if candidate_name == normalized_query or candidate_name.replace(" ", "") == compressed_query:
                return candidate_domain

        first_candidate = payload[0]
        first_domain = (first_candidate.get("domain") or "").strip().lower()
        if first_domain:
            return first_domain

    return None


def _favicon_url(service):
    if not service.url_name:
        return None

    parsed_url = urlparse(service.url_name if "://" in service.url_name else f"//{service.url_name}")
    hostname = parsed_url.hostname
    if not hostname:
        return None

    return f"https://www.google.com/s2/favicons?domain={hostname}&sz=64"


def _service_probe_urls(service):
    urls = []

    if service.url_name:
        raw_url = service.url_name.strip()
        parsed_url = urlparse(raw_url if "://" in raw_url else f"//{raw_url}")
        if parsed_url.scheme in {"http", "https"}:
            urls.append(raw_url)
        elif parsed_url.netloc:
            urls.extend([f"http://{parsed_url.netloc}", f"https://{parsed_url.netloc}"])
        elif raw_url:
            urls.extend([f"http://{raw_url}", f"https://{raw_url}"])

    if service.address and service.port:
        host = service.address.strip()
        port = str(service.port)
        if host:
            urls.extend([f"http://{host}:{port}", f"https://{host}:{port}"])

    unique_urls = []
    seen_urls = set()
    for url in urls:
        if url not in seen_urls:
            unique_urls.append(url)
            seen_urls.add(url)

    return unique_urls


def _probe_url_is_online(url):
    request = Request(url, method="HEAD")

    try:
        with urlopen(request, timeout=SERVICE_STATUS_CHECK_TIMEOUT) as response:
            return 200 <= getattr(response, "status", 200) < 400
    except HTTPError as error:
        if error.code in {405, 501}:
            try:
                with urlopen(Request(url, method="GET"), timeout=SERVICE_STATUS_CHECK_TIMEOUT) as response:
                    return 200 <= getattr(response, "status", 200) < 400
            except (URLError, HTTPError, TimeoutError, OSError):
                return False
        return 200 <= error.code < 400
    except (URLError, TimeoutError, OSError):
        return False


def _service_is_online(service):
    for url in _service_probe_urls(service):
        if _probe_url_is_online(url):
            return True

    return False


def _refresh_service_status_if_needed(service, now=None):
    now = now or timezone.now()
    if service.status_checked_at and now - service.status_checked_at < SERVICE_STATUS_REFRESH_INTERVAL:
        return service.is_online

    current_status = _service_is_online(service)
    service.is_online = current_status
    service.status_checked_at = now
    service.save(update_fields=["is_online", "status_checked_at"])
    ServiceStatus.objects.create(service=service, is_online=current_status)
    return current_status


def _fallback_logo_data_uri(service_name):
    initials = "".join(part[0] for part in service_name.split()[:2]).upper() or "?"
    color_hash = hashlib.sha256(service_name.encode("utf-8")).hexdigest()
    background = f"#{color_hash[:6]}"
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 64 64'>"
        f"<rect width='64' height='64' rx='16' fill='{background}'/>"
        f"<text x='32' y='39' text-anchor='middle' font-family='Arial, sans-serif' font-size='22' font-weight='700' fill='white'>{initials}</text>"
        "</svg>"
    )
    encoded_svg = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded_svg}"


def build_service_display(service):
    brand_domain = _search_brand_domain(service.name)
    brand_logo_url = f"https://logo.clearbit.com/{brand_domain}" if brand_domain else None
    favicon_url = _favicon_url(service)
    fallback_logo_url = _fallback_logo_data_uri(service.name)
    logo_url = brand_logo_url or favicon_url or fallback_logo_url
    live_is_online = _refresh_service_status_if_needed(service)
    return {
        "service": service,
        "logo_url": logo_url,
        "fallback_logo_url": fallback_logo_url,
        "logo_alt": f"{service.name} logo",
        "logo_is_data_uri": logo_url.startswith("data:image/svg+xml;base64,"),
        "is_online": live_is_online,
        "stored_is_online": service.is_online,
    }

def fetch_recent_nba_scores(limit=5):
    try:
        with urlopen(NBA_SCORES_URL, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
        return [], "Unable to load NBA scores right now."

    events = payload.get("events") or []
    scores = []

    for event in events[:limit]:
        home_score = event.get("intHomeScore")
        away_score = event.get("intAwayScore")
        if home_score is None or away_score is None:
            continue

        scores.append(
            {
                "date": event.get("dateEvent") or "",
                "status": event.get("strStatus") or "Final",
                "home_team": event.get("strHomeTeam") or "Home",
                "away_team": event.get("strAwayTeam") or "Away",
                "home_score": home_score,
                "away_score": away_score,
            }
        )

    return scores, None


def build_home_context(form=None, form_modal_open=False, category_form=None, category_modal_open=False):
    save_system_metrics()
    nba_scores, nba_scores_error = fetch_recent_nba_scores()
    metrics = list(SystemMetric.objects.order_by("-created_at")[:20])
    cpu = [m.cpu_percent for m in reversed(metrics)]
    ram = [m.ram_percent for m in reversed(metrics)]

    # Build display items with history, ordered by name
    service_items = []
    for service in Service.objects.select_related("category").order_by("name"):
        item = build_service_display(service)
        # Fetch last 10 checks newest-first, then reverse for left→right display
        recent = list(service.history.all()[:10])
        recent.reverse()
        uptime_pct = (
            round(sum(1 for h in recent if h.is_online) / len(recent) * 100)
            if recent else None
        )
        item["history"] = recent
        item["uptime_pct"] = uptime_pct
        service_items.append(item)

    # Group by category; uncategorised services go last
    groups_map = {}
    group_order = []
    uncategorised = []
    for item in service_items:
        cat = item["service"].category
        if cat is None:
            uncategorised.append(item)
        else:
            if cat.pk not in groups_map:
                groups_map[cat.pk] = {"name": cat.name, "items": []}
                group_order.append(groups_map[cat.pk])
            groups_map[cat.pk]["items"].append(item)
    if uncategorised:
        group_order.append({"name": None, "items": uncategorised})

    return {
        "category_groups": group_order,
        "media_panels": MediaPanel.objects.all(),
        "form": form or ServiceForm(),
        "form_modal_open": form_modal_open,
        "category_form": category_form or CategoryForm(),
        "category_modal_open": category_modal_open,
        "nba_scores": nba_scores,
        "nba_scores_error": nba_scores_error,
        "system_stats": get_system_stats(),
        "cpu_chart": cpu,
        "ram_chart": ram,
    }
    

class HomeView(View):
    template_name = "dashboard.html"

    def get(self, request):
        return render(request, self.template_name, build_home_context())

    def post(self, request):
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("homepage")
        return render(request, self.template_name, build_home_context(form=form, form_modal_open=True))


class CategoryView(View):
    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("homepage")
        return render(
            request,
            "dashboard.html",
            build_home_context(category_form=form, category_modal_open=True),
        )