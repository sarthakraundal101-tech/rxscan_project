"""REST API endpoints for mobile applications (Flutter, React Native, Android, iOS)."""
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .forms import _generate_prescription_graphic
from .models import Medicine, Prescription, PrescriptionItem, Profile
from .services import pipeline, safety


@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):
    """Mobile user login endpoint."""
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "").strip()
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "email": user.email,
            }
        })
    return Response({"success": False, "error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
@permission_classes([AllowAny])
def api_register(request):
    """Mobile user registration endpoint."""
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "").strip()
    first_name = request.data.get("first_name", "").strip()
    email = request.data.get("email", "").strip()

    if not username or not password:
        return Response({"success": False, "error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"success": False, "error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password, email=email, first_name=first_name)
    Profile.objects.get_or_create(user=user)
    login(request, user)
    return Response({
        "success": True,
        "message": "Account created successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "email": user.email,
        }
    }, status=status.HTTP_201_CREATED)


def _serialize_prescription(rx):
    items = []
    for it in rx.items.select_related("medicine").all():
        med = it.medicine
        items.append({
            "id": it.id,
            "detected_text": it.detected_text,
            "medicine_id": med.id if med else None,
            "generic_name": med.generic_name if med else "Unidentified",
            "therapeutic_class": med.therapeutic_class if med else "",
            "strength": it.strength,
            "frequency": it.frequency,
            "duration": it.duration,
            "confidence": it.confidence,
            "band": it.band,
            "band_label": it.band_label,
            "note": it.note,
            "uses": med.uses_list if med else [],
            "side_effects": med.side_effects_list if med else [],
            "contraindications": med.contraindications_list if med else [],
        })

    safety_data = safety.analyze(rx)
    interactions = [{
        "medicine_a": i.medicine_a.generic_name,
        "medicine_b": i.medicine_b.generic_name,
        "severity": i.severity,
        "description": i.description,
    } for i in safety_data["interactions"]]

    return {
        "id": rx.id,
        "code": rx.code,
        "filename": rx.filename,
        "image_url": rx.display_url,
        "status": rx.status,
        "status_display": rx.get_status_display(),
        "uploaded_at": rx.uploaded_at.isoformat(),
        "ocr_confidence": rx.ocr_confidence,
        "quality_notes": rx.quality_notes,
        "conditions": rx.conditions,
        "allergies": rx.allergies,
        "items": items,
        "safety": {
            "interactions": interactions,
            "patient_warnings": safety_data["patient_warnings"],
            "duplicates": safety_data["duplicates"],
        }
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def api_scan(request):
    """Mobile prescription scan & upload endpoint."""
    user = request.user if request.user.is_authenticated else User.objects.first()
    image = request.FILES.get("image")
    manual_text = request.data.get("manual_text", "").strip()
    age_group = request.data.get("age_group", "")
    conditions = request.data.get("conditions", "").strip()
    allergies = request.data.get("allergies", "").strip()

    if not image and not manual_text:
        return Response({"success": False, "error": "Please provide either an image file or manual_text"}, status=status.HTTP_400_BAD_REQUEST)

    if not image and manual_text:
        image = _generate_prescription_graphic(manual_text)

    rx = Prescription.objects.create(
        user=user,
        image=image,
        age_group=age_group,
        conditions=conditions,
        allergies=allergies
    )

    try:
        pipeline.process_prescription(rx, manual_text)
    except Exception as exc:
        rx.status, rx.status_note = "unreadable", f"Processing failed: {exc}"
        rx.save()

    return Response({
        "success": True,
        "prescription": _serialize_prescription(rx)
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def api_prescriptions(request):
    """List recent prescriptions."""
    user = request.user if request.user.is_authenticated else None
    qs = Prescription.objects.all() if not user else user.prescriptions.all()
    return Response({
        "success": True,
        "count": qs.count(),
        "prescriptions": [_serialize_prescription(rx) for rx in qs[:20]]
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def api_prescription_detail(request, pk):
    """Get single prescription result."""
    rx = get_object_or_404(Prescription, pk=pk)
    return Response({
        "success": True,
        "prescription": _serialize_prescription(rx)
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def api_medicines(request):
    """Search and browse medicine database."""
    q = request.GET.get("q", "").strip()
    qs = Medicine.objects.all()
    if q:
        qs = qs.filter(Q(generic_name__icontains=q) | Q(brand_names__icontains=q) | Q(therapeutic_class__icontains=q))
    return Response({
        "success": True,
        "count": qs.count(),
        "medicines": [{
            "id": m.id,
            "code": m.code,
            "generic_name": m.generic_name,
            "brand_names": m.brand_names,
            "therapeutic_class": m.therapeutic_class,
            "strengths": m.strengths,
            "uses": m.uses_list,
            "side_effects": m.side_effects_list,
            "contraindications": m.contraindications_list,
        } for m in qs[:50]]
    })
