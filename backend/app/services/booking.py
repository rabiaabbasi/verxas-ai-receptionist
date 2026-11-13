
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.database import supabase


def parse_time(value):
    """Convert a Supabase TIME value into a Python time object."""
    if isinstance(value, time):
        return value.replace(tzinfo=None)

    if not value:
        raise ValueError("Doctor schedule contains an empty time.")

    return time.fromisoformat(str(value))


def get_business_timezone(business_id):
    """Get the clinic's configured timezone."""
    response = (
        supabase.table("businesses")
        .select("timezone")
        .eq("id", business_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise ValueError("Clinic not found.")

    timezone_name = response.data[0].get("timezone")

    if not timezone_name:
        raise ValueError("Clinic timezone is not configured.")

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise ValueError(
            f"Invalid or unavailable clinic timezone: {timezone_name}"
        )


def get_active_doctor(doctor_id, business_id):
    """Confirm that the doctor belongs to this clinic and is active."""
    response = (
        supabase.table("doctors")
        .select("id, name")
        .eq("id", doctor_id)
        .eq("business_id", business_id)
        .eq("active", True)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise ValueError("Doctor not found or inactive.")

    return response.data[0]


def get_active_service(service_id, business_id):
    """Get the real service duration from the database."""
    response = (
        supabase.table("services")
        .select("id, name, duration_minutes")
        .eq("id", service_id)
        .eq("business_id", business_id)
        .eq("active", True)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise ValueError("Service not found or inactive.")

    return response.data[0]


def check_availability(
    business_id,
    doctor_id,
    service_id,
    start_at,
    exclude_appointment_id=None
):
    """Check doctor, service, schedule and existing appointments."""

    # Validate doctor and service
    get_active_doctor(doctor_id, business_id)
    service = get_active_service(service_id, business_id)

    duration_minutes = int(service["duration_minutes"])

    if duration_minutes <= 0:
        raise ValueError("Invalid service duration.")

    # Parse appointment date and time
    if not isinstance(start_at, str) or not start_at.strip():
        raise ValueError("Appointment date and time are required.")

    start = datetime.fromisoformat(
        start_at.strip().replace("Z", "+00:00")
    )

    if start.tzinfo is None:
        raise ValueError(
            "Please provide appointment time with a timezone."
        )

    # Get clinic timezone
    clinic_timezone = get_business_timezone(business_id)

    # Convert to clinic local time
    local_start = start.astimezone(clinic_timezone)
    end = start + timedelta(minutes=duration_minutes)
    local_end = end.astimezone(clinic_timezone)

    # Appointment must fit within one local working day
    if local_start.date() != local_end.date():
        return {
            "available": False,
            "message": "Appointment must fit within one working day."
        }

    # Python: Monday=0, Sunday=6
    # Database: Sunday=0, Monday=1 ... Saturday=6
    day_of_week = (local_start.weekday() + 1) % 7

    # Get doctor's working hours
    schedule_response = (
        supabase.table("doctor_schedules")
        .select("start_time, end_time")
        .eq("business_id", business_id)
        .eq("doctor_id", doctor_id)
        .eq("day_of_week", day_of_week)
        .eq("is_available", True)
        .execute()
    )

    requested_start_time = local_start.time().replace(tzinfo=None)
    requested_end_time = local_end.time().replace(tzinfo=None)

    within_schedule = False

    for schedule in schedule_response.data:
        schedule_start = parse_time(schedule["start_time"])
        schedule_end = parse_time(schedule["end_time"])

        if (
            requested_start_time >= schedule_start
            and requested_end_time <= schedule_end
        ):
            within_schedule = True
            break

    if not within_schedule:
        return {
            "available": False,
            "message": "The doctor is not available during this time."
        }

    # Check overlapping active appointments
    appointment_query = (
        supabase.table("appointments")
        .select("id")
        .eq("business_id", business_id)
        .eq("doctor_id", doctor_id)
        .in_("status", ["pending", "confirmed"])
        .lt("start_at", end.isoformat())
        .gt("end_at", start.isoformat())
    )

    if exclude_appointment_id:
        appointment_query = appointment_query.neq(
            "id",
            exclude_appointment_id
        )

    appointment_response = appointment_query.execute()   

    if appointment_response.data:
        return {
            "available": False,
            "message": "This time slot is already booked."
        }

    return {
        "available": True,
        "message": "The doctor is available.",
        "start_at": start.isoformat(),
        "end_at": end.isoformat(),
        "duration_minutes": duration_minutes,
        "service_name": service["name"]
    }


def book_appointment(
    business_id,
    doctor_id,
    service_id,
    customer_name,
    customer_phone,
    start_at
):
    """Check availability and create an appointment."""

    try:
        # Validate customer details
        if not isinstance(customer_name, str) or not customer_name.strip():
            return {
                "success": False,
                "message": "Customer name is required."
            }

        if not isinstance(customer_phone, str) or not customer_phone.strip():
            return {
                "success": False,
                "message": "Customer phone is required."
            }

        # Check availability
        availability = check_availability(
            business_id=business_id,
            doctor_id=doctor_id,
            service_id=service_id,
            start_at=start_at
        )

        if not availability["available"]:
            return {
                "success": False,
                "message": availability["message"]
            }

        # Save appointment
        response = (
            supabase.table("appointments")
            .insert({
                "business_id": business_id,
                "doctor_id": doctor_id,
                "service_id": service_id,
                "customer_name": customer_name.strip(),
                "customer_phone": customer_phone.strip(),
                "start_at": availability["start_at"],
                "end_at": availability["end_at"],
                "status": "confirmed"
            })
            .execute()
        )

        if not response.data:
            raise ValueError(
                "Database returned no appointment after insert."
            )

        return {
            "success": True,
            "message": "Appointment successfully booked.",
            "appointment": response.data[0]
        }

    except Exception as error:
        # Print the actual error in the Uvicorn terminal
        print("\n========== BOOKING ERROR DETAILS ==========")
        print(repr(error))
        print("===========================================\n")

        error_text = str(error).lower()

        if "23p01" in error_text or "exclusion" in error_text:
            return {
                "success": False,
                "message": (
                    "This time slot was just booked. "
                    "Please choose another time."
                )
            }

        if "23505" in error_text:
            return {
                "success": False,
                "message": "A duplicate booking was detected."
            }

        return {
            "success": False,
            "message": (
                "Booking failed. Check the backend terminal "
                "for the detailed error."
            )
        }


def cancel_appointment(business_id, appointment_id, customer_phone):
    """Cancel an existing appointment after verifying customer ownership."""

    if not appointment_id or not customer_phone:
        return {
            "success": False,
            "message": "Appointment ID and customer phone are required."
        }

    try:
        # Find the appointment belonging to this clinic and customer.
        response = (
            supabase.table("appointments")
            .select("*")
            .eq("id", appointment_id)
            .eq("business_id", business_id)
            .eq("customer_phone", customer_phone)
            .limit(1)
            .execute()
        )

        if not response.data:
            return {
                "success": False,
                "message": "No appointment was found with those details."
            }

        appointment = response.data[0]

        if appointment.get("status") == "cancelled":
            return {
                "success": False,
                "message": "This appointment is already cancelled."
            }

        if appointment.get("status") not in ["pending", "confirmed"]:
            return {
                "success": False,
                "message": "This appointment cannot be cancelled."
            }

        # Update the status instead of deleting the record.
        update_response = (
            supabase.table("appointments")
            .update({"status": "cancelled"})
            .eq("id", appointment_id)
            .eq("business_id", business_id)
            .eq("customer_phone", customer_phone)
            .in_("status", ["pending", "confirmed"])
            .execute()
        )

        if not update_response.data:
            return {
                "success": False,
                "message": "The appointment could not be cancelled. Please try again."
            }

        return {
            "success": True,
            "message": "Appointment successfully cancelled.",
            "appointment_id": appointment_id,
            "status": "cancelled"
        }

    except Exception as error:
        print("\n========== CANCELLATION ERROR ==========")
        print(repr(error))
        print("========================================\n")

        return {
            "success": False,
            "message": "Cancellation failed. Check the backend terminal."
        }


def reschedule_appointment(
    business_id,
    appointment_id,
    customer_phone,
    new_start_at
):
    """Move an existing appointment to a new date/time."""

    if not appointment_id or not customer_phone or not new_start_at:
        return {
            "success": False,
            "message": "Appointment ID, customer phone and new appointment time are required."
        }

    try:
        # 1. Find the existing appointment and verify ownership.
        response = (
            supabase.table("appointments")
            .select("*")
            .eq("id", appointment_id)
            .eq("business_id", business_id)
            .eq("customer_phone", customer_phone)
            .limit(1)
            .execute()
        )

        if not response.data:
            return {
                "success": False,
                "message": "No appointment was found with those details."
            }

        appointment = response.data[0]

        # 2. Only active appointments can be rescheduled.
        if appointment.get("status") not in ["pending", "confirmed"]:
            return {
                "success": False,
                "message": "This appointment cannot be rescheduled."
            }

        # 3. Check the new time, excluding the current appointment.
        availability = check_availability(
            business_id=business_id,
            doctor_id=appointment["doctor_id"],
            service_id=appointment["service_id"],
            start_at=new_start_at,
            exclude_appointment_id=appointment_id
        )

        if not availability["available"]:
            return {
                "success": False,
                "message": availability["message"]
            }

        # 4. Update the existing appointment instead of creating a new one.
        update_response = (
            supabase.table("appointments")
            .update({
                "start_at": availability["start_at"],
                "end_at": availability["end_at"]
            })
            .eq("id", appointment_id)
            .eq("business_id", business_id)
            .eq("customer_phone", customer_phone)
            .in_("status", ["pending", "confirmed"])
            .execute()
        )

        if not update_response.data:
            return {
                "success": False,
                "message": "The appointment could not be rescheduled. Please try again."
            }

        return {
            "success": True,
            "message": "Appointment successfully rescheduled.",
            "appointment": update_response.data[0]
        }

    except Exception as error:
        print("\n========== RESCHEDULING ERROR ==========")
        print(repr(error))
        print("========================================\n")

        error_text = str(error).lower()

        if "23p01" in error_text or "exclusion" in error_text:
            return {
                "success": False,
                "message": "This new time slot has just been booked. Please choose another time."
            }

        return {
            "success": False,
            "message": "Rescheduling failed. Check the backend terminal."
        }

