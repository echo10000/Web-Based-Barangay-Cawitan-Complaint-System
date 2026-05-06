import requests
from django.conf import settings


def send_sms(number, message):
    """
    Sends SMS using Semaphore API.
    Returns a dictionary with status and response.
    """

    if not settings.SEMAPHORE_API_KEY:
        return {
            "success": False,
            "status": "Not Configured",
            "response": "SEMAPHORE_API_KEY is missing.",
        }

    payload = {
        "apikey": settings.SEMAPHORE_API_KEY,
        "number": number,
        "message": message,
        "sendername": settings.SEMAPHORE_SENDER_NAME,
    }

    try:
        response = requests.post(
            settings.SEMAPHORE_API_URL,
            data=payload,
            timeout=10,
        )

        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text

        if response.status_code == 200:
            sms_status = "Sent"

            if isinstance(response_data, list) and len(response_data) > 0:
                sms_status = response_data[0].get("status", "Sent")

            return {
                "success": True,
                "status": sms_status,
                "response": response_data,
            }

        return {
            "success": False,
            "status": "Failed",
            "response": response_data,
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "status": "Failed",
            "response": str(e),
        }


def send_complaint_submission_sms(complaint):
    """
    Sends SMS when a complaint is submitted.
    Includes resident name, complaint title, reference number, and location.
    """
    resident_name = complaint.resident.get_full_name() or complaint.resident.username
    phone_number = complaint.resident.resident_profile.phone_number
    
    if not phone_number:
        return {
            "success": False,
            "status": "Failed",
            "response": f"No phone number for {resident_name}",
        }
    
    message = (
        f"Hi {resident_name},\n\n"
        f"Your complaint has been received!\n"
        f"Ref #: {complaint.id}\n"
        f"Title: {complaint.title}\n"
        f"Location: {complaint.incident_location}\n"
        f"Priority: {complaint.get_priority_display()}\n\n"
        f"We will review your complaint shortly. Thank you!"
    )
    
    return send_sms(phone_number, message)


def send_complaint_status_update_sms(complaint):
    """
    Sends SMS when complaint status changes.
    Includes resident name, reference number, new status, and assigned staff if available.
    """
    resident_name = complaint.resident.get_full_name() or complaint.resident.username
    phone_number = complaint.resident.resident_profile.phone_number
    
    if not phone_number:
        return {
            "success": False,
            "status": "Failed",
            "response": f"No phone number for {resident_name}",
        }
    
    assigned_staff = ""
    if complaint.assigned_to:
        staff_name = complaint.assigned_to.get_full_name() or complaint.assigned_to.username
        assigned_staff = f"\nAssigned to: {staff_name}"
    
    message = (
        f"Hi {resident_name},\n\n"
        f"Your complaint has been updated!\n"
        f"Ref #: {complaint.id}\n"
        f"Title: {complaint.title}\n"
        f"New Status: {complaint.get_status_display()}{assigned_staff}\n\n"
        f"We appreciate your patience."
    )
    
    return send_sms(phone_number, message)


def send_complaint_resolved_sms(complaint):
    """
    Sends SMS when complaint is resolved.
    Includes resident name, reference number, and resolution status.
    """
    resident_name = complaint.resident.get_full_name() or complaint.resident.username
    phone_number = complaint.resident.resident_profile.phone_number
    
    if not phone_number:
        return {
            "success": False,
            "status": "Failed",
            "response": f"No phone number for {resident_name}",
        }
    
    message = (
        f"Hi {resident_name},\n\n"
        f"Good news! Your complaint has been resolved.\n"
        f"Ref #: {complaint.id}\n"
        f"Title: {complaint.title}\n"
        f"Status: {complaint.get_status_display()}\n\n"
        f"Thank you for reporting this issue. We value your feedback!"
    )
    
    return send_sms(phone_number, message)
