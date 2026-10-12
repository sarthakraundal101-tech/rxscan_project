from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import RegisterForm, UploadForm
from .models import (Medicine, Prescription, PrescriptionItem, Profile, Verification,
                     is_pharmacist)
from .services import pipeline, safety


def pharmacist_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        return view(request, *args, **kwargs)
    return wrapper


def home(request):
    return redirect("dashboard")


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Profile.objects.get_or_create(user=user)
        login(request, user)
        return redirect("dashboard")
    return render(request, "scanner/register.html", {"form": form})


@login_required
def dashboard(request):
    scans = request.user.prescriptions.all()
    ctx = {
        "scans": scans[:8],
        "total": scans.count(),
        "verified": scans.filter(status="verified").count(),
        "pending": scans.filter(status__in=["pending_review", "ready"]).count(),
        "unreadable": scans.filter(status="unreadable").count(),
    }
    return render(request, "scanner/dashboard.html", ctx)


@login_required
def history(request):
    return render(request, "scanner/history.html", {"scans": request.user.prescriptions.all()})


@login_required
def upload(request):
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        rx = form.save(commit=False)
        rx.user = request.user
        rx.save()
        try:
            pipeline.process_prescription(rx, form.cleaned_data.get("manual_text", ""))
        except Exception as exc:  # keep the app usable if one image fails
            rx.status, rx.status_note = "unreadable", f"Processing failed: {exc}"
            rx.save()
        return redirect("result", pk=rx.pk)
    return render(request, "scanner/upload.html", {"form": form})


def _can_view(user, rx):
    return rx.user_id == user.id or user.is_staff or user.is_superuser


@login_required
def result(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)
    if not _can_view(request.user, rx):
        raise PermissionDenied
    items = rx.items.select_related("medicine")
    ctx = {"rx": rx, "items": items, "safety": safety.analyze(rx),
           "last_verification": rx.verifications.first()}
    return render(request, "scanner/result.html", ctx)


@login_required
def request_review(request, pk):
    rx = get_object_or_404(Prescription, pk=pk, user=request.user)
    if request.method == "POST" and rx.status == "ready":
        rx.status = "pending_review"
        rx.save()
        messages.success(request, "Sent to a pharmacist for verification.")
    return redirect("result", pk=pk)


@login_required
def medicines(request):
    q = request.GET.get("q", "").strip()
    qs = Medicine.objects.all()
    if q:
        qs = qs.filter(Q(generic_name__icontains=q) | Q(brand_names__icontains=q) | Q(therapeutic_class__icontains=q))
    return render(request, "scanner/medicines.html", {"medicines": qs, "q": q})


@login_required
def medicine_detail(request, pk):
    return render(request, "scanner/medicine_detail.html", {"m": get_object_or_404(Medicine, pk=pk)})


@pharmacist_required
def pharmacist_dashboard(request):
    queue = Prescription.objects.exclude(status__in=["verified", "unreadable"])
    low = PrescriptionItem.objects.filter(prescription__in=queue, verification_status="auto").filter(
        Q(medicine__isnull=True) | Q(confidence__lt=70)).values("prescription").distinct().count()
    ctx = {
        "queue": queue.order_by("status", "uploaded_at").select_related("user"),
        "pending": queue.filter(status="pending_review").count(),
        "verified": Prescription.objects.filter(status="verified").count(),
        "low": low,
        "recent": Prescription.objects.filter(status="verified").select_related("user")[:5],
    }
    return render(request, "scanner/pharmacist_dashboard.html", ctx)


@login_required
def review(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)
    if not _can_view(request.user, rx):
        raise PermissionDenied
    items = list(rx.items.select_related("medicine"))
    if request.method == "POST":
        changes = []
        for it in items:
            choice = request.POST.get(f"med_{it.id}", "")
            before = it.medicine.generic_name if it.medicine else "none"
            if choice:
                med = Medicine.objects.filter(pk=choice).first()
                it.medicine, it.verification_status = med, "verified"
            else:
                it.medicine, it.verification_status = None, "rejected"
            it.strength = request.POST.get(f"strength_{it.id}", it.strength).strip()
            it.frequency = request.POST.get(f"frequency_{it.id}", it.frequency).strip()
            it.duration = request.POST.get(f"duration_{it.id}", it.duration).strip()
            it.note = ""
            it.save()
            after = it.medicine.generic_name if it.medicine else "rejected"
            if before != after:
                changes.append(f"{it.detected_text}: {before} -> {after}")
        Verification.objects.create(
            prescription=rx, pharmacist=request.user,
            remarks=request.POST.get("remarks", "").strip(), corrections="\n".join(changes))
        rx.status = "verified"
        rx.save()
        messages.success(request, f"Prescription {rx.code} updated and verified.")
        return redirect("result", pk=rx.pk)
    return render(request, "scanner/review.html", {
        "rx": rx, "items": items, "all_medicines": Medicine.objects.all(), "safety": safety.analyze(rx)})
