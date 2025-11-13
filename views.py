import csv, io
from dateutil import parser
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from .models import Organization, EmissionRecord, Recommendation
from .forms import EmissionsUploadForm


def home(request):
    orgs = Organization.objects.all()
    return render(request, "carbonapp/dashboard.html", {"orgs": orgs})


@require_http_methods(["GET", "POST"])
def upload_emissions(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    if request.method == "POST":
        form = EmissionsUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES["file"]
            data = f.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(data))
            count = 0
            for row in reader:
                try:
                    date = parser.parse(row.get("date") or row.get("timestamp")).date()
                    value = float(row.get("value"))
                except Exception:
                    continue
                scope = row.get("scope", "scope1")
                activity = row.get("activity", "")
                EmissionRecord.objects.create(
                    organization=org,
                    timestamp=date,
                    value=value,
                    scope=scope,
                    activity=activity,
                )
                count += 1
            return HttpResponse(f"Imported {count} records for {org.name}")
    else:
        form = EmissionsUploadForm(initial={"organization": org.id})
    return render(request, "carbonapp/upload.html", {"form": form, "org": org})


def org_emissions_api(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    qs = EmissionRecord.objects.filter(organization=org)
    agg = qs.annotate(month=TruncMonth("timestamp")).values("month").annotate(total=Sum("value")).order_by("month")
    data = [{"month": x["month"].strftime("%Y-%m-%d"), "value": x["total"]} for x in agg]
    return JsonResponse({"data": data})


def recommendations_for_org(org):
    recs = []
    qs = org.records.values("scope").annotate(total=Sum("value"))
    totals = {x["scope"]: x["total"] for x in qs}
    if totals:
        max_scope = max(totals, key=totals.get)
        if max_scope == "scope2":
            recs.append({
                "title": "Switch to renewable electricity",
                "detail": "Adopt renewable sources to reduce Scope 2 emissions.",
                "estimated_reduction": round(totals[max_scope]*0.25,2)
            })
    recs.append({
        "title": "Energy efficiency audit",
        "detail": "Audit energy usage to identify savings.",
        "estimated_reduction": 0.1
    })
    return recs


def org_dashboard(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    recs = recommendations_for_org(org)
    saved_recs = org.recommendations.all()
    return render(request, "carbonapp/org_dashboard.html", {"org": org, "recs": recs, "saved_recs": saved_recs})

# --- Forecast & CSV export helpers (append to carbonapp/views.py) ---
import os
from joblib import load
import numpy as np
import pandas as pd
from datetime import datetime, date
from django.http import HttpResponse
from django.utils.encoding import smart_str

# MODEL_DIR where train_model saved joblibs (adjust if different)
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'ml_models')

def _make_future_features(start_date, periods):
    """
    Create month/year and cyclic features for next `periods` months starting after start_date.
    start_date: a date object - last known date in DB
    returns DataFrame with columns: month, year, month_sin, month_cos and a 'month_dt' column.
    """
    rows = []
    y = start_date.year
    m = start_date.month
    for i in range(1, periods + 1):
        mi = ((m + i - 1) % 12) + 1
        yi = y + ((m + i - 1) // 12)
        month_sin = np.sin(2 * np.pi * mi / 12)
        month_cos = np.cos(2 * np.pi * mi / 12)
        month_dt = date(yi, mi, 1)
        rows.append({"month": mi, "year": yi, "month_sin": month_sin, "month_cos": month_cos, "month_dt": month_dt})
    return pd.DataFrame(rows)

def forecast_org_points(org, periods=6):
    """
    Load model for org and return list of future points: [{"month":"YYYY-MM-DD","value":float}, ...]
    if model not found or insufficient data, returns [].
    """
    model_path = os.path.join(MODEL_DIR, f"org_{org.id}_ridge.joblib")
    if not os.path.exists(model_path):
        return []
    try:
        model = load(model_path)
    except Exception:
        return []

    last_rec = org.records.order_by('-timestamp').first()
    if not last_rec:
        return []

    last_date = last_rec.timestamp
    Xf = _make_future_features(last_date, periods)
    # Keep feature ordering consistent with training: month, year, month_sin, month_cos
    X = Xf[['month', 'year', 'month_sin', 'month_cos']].values
    preds = model.predict(X)
    points = []
    for md, p in zip(Xf['month_dt'], preds):
        points.append({"month": md.strftime("%Y-%m-%d"), "value": float(max(p, 0.0))})
    return points

def org_forecast_api(request, org_id):
    """API endpoint: returns future forecast points (6 months default)."""
    from django.shortcuts import get_object_or_404
    org = get_object_or_404(Organization, pk=org_id)
    periods = int(request.GET.get('periods', 6))
    pts = forecast_org_points(org, periods=periods)
    return JsonResponse({"data": pts})

def org_emissions_csv(request, org_id):
    """
    Return monthly aggregated emissions CSV for org.
    Columns: month (YYYY-MM-01), value
    """
    from django.shortcuts import get_object_or_404
    org = get_object_or_404(Organization, pk=org_id)
    qs = EmissionRecord.objects.filter(organization=org)
    agg = qs.annotate(month=TruncMonth('timestamp')).values('month').annotate(total=Sum('value')).order_by('month')
    # Build CSV
    rows = [("month", "value")]
    for x in agg:
        rows.append((x['month'].strftime("%Y-%m-01"), str(x['total'])))
    # Create response
    resp = HttpResponse(content_type='text/csv')
    filename = f"{org.name.replace(' ', '_')}_monthly_emissions.csv"
    resp['Content-Disposition'] = f'attachment; filename="{smart_str(filename)}"'
    for r in rows:
        resp.write(','.join(r) + '\n')
    return resp
