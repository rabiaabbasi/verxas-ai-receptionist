
import os
import json

from fastapi import FastAPI, Request, HTTPException, Header
from dotenv import load_dotenv

from app.database import supabase
from app.services.booking import (
    check_availability,
    book_appointment,
    cancel_appointment,
    reschedule_appointment
)

# Load environment variables
load_dotenv()

app = FastAPI(title="Verxas AI Receptionist")

# Environment variables
BUSINESS_ID = os.getenv("BUSINESS_ID")
WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET")


# --------------------------------
# HOME ROUTE
# --------------------------------

@app.get("/")
def home():
    return {
        "message": "Verxas AI Receptionist API is running"
    }


# --------------------------------
# HEALTH CHECK
# --------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# --------------------------------
# GET CLINIC INFORMATION
# --------------------------------

@app.get("/clinic")
def get_clinic():
    try:
        if not BUSINESS_ID:
            raise HTTPException(
                status_code=500,
                detail="BUSINESS_ID is missing from app/.env"
            )

        response = (
            supabase.table("businesses")
            .select("*")
            .eq("id", BUSINESS_ID)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="No clinic found for this BUSINESS_ID"
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as error:
        print("CLINIC ERROR:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve clinic information"
        )


# --------------------------------
# GET ACTIVE DOCTORS
# --------------------------------

@app.get("/doctors")
def get_doctors():
    try:
        if not BUSINESS_ID:
            raise HTTPException(
                status_code=500,
                detail="BUSINESS_ID is missing from app/.env"
            )

        response = (
            supabase.table("doctors")
            .select("*")
            .eq("business_id", BUSINESS_ID)
            .eq("active", True)
            .execute()
        )

        return response.data

    except HTTPException:
        raise

    except Exception as error:
        print("DOCTORS ERROR:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve doctors"
        )


# --------------------------------
# GET ACTIVE SERVICES
# --------------------------------

@app.get("/services")
def get_services():
    try:
        if not BUSINESS_ID:
            raise HTTPException(
                status_code=500,
                detail="BUSINESS_ID is missing from app/.env"
            )

        response = (
            supabase.table("services")
            .select("*")
            .eq("business_id", BUSINESS_ID)
            .eq("active", True)
            .execute()
        )

        return response.data

    except HTTPException:
        raise

    except Exception as error:
        print("SERVICES ERROR:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve services"
        )


# --------------------------------
# VAPI TOOL WEBHOOK
# --------------------------------

@app.post("/vapi/tools")
async def vapi_tools(
    request: Request,
    x_verxas_token: str = Header(default=None)
):

    # Verify webhook security token
    if not WEBHOOK_SECRET:
        raise HTTPException(
            status_code=500,
            detail="VAPI_WEBHOOK_SECRET is missing from app/.env"
        )

    if x_verxas_token != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    # Read incoming Vapi request
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON request"
        )

    message = body.get("message", {})

    if message.get("type") != "tool-calls":
        return {"received": True}

    results = []

    # Process each tool call
    for tool_call in message.get("toolCallList", []):

        call_id = tool_call.get("id")

        try:
            function = tool_call.get("function", {})
            name = function.get("name")

            args = function.get("arguments", {})

            if isinstance(args, str):
                args = json.loads(args)

            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")

            # GET CLINIC INFORMATION
            if name == "get_clinic_information":
                result = get_clinic()

            # GET DOCTORS
            elif name == "get_doctors":
                result = get_doctors()

            # CHECK APPOINTMENT AVAILABILITY
            elif name == "check_availability":
                result = check_availability(
                    business_id=BUSINESS_ID,
                    doctor_id=args["doctor_id"],
                    service_id=args["service_id"],
                    start_at=args["start_at"]
                )

            # BOOK APPOINTMENT
            elif name == "book_appointment":
                if not BUSINESS_ID:
                    raise ValueError("BUSINESS_ID is not configured")

                result = book_appointment(
                    business_id=BUSINESS_ID,
                    doctor_id=args["doctor_id"],
                    service_id=args["service_id"],
                    customer_name=args["customer_name"],
                    customer_phone=args["customer_phone"],
                    start_at=args["start_at"]
                )

            # CANCEL APPOINTMENT
            elif name == "cancel_appointment":
                if not BUSINESS_ID:
                    raise ValueError("BUSINESS_ID is not configured")

                result = cancel_appointment(
                    business_id=BUSINESS_ID,
                    appointment_id=args["appointment_id"],
                    customer_phone=args["customer_phone"]
                )
                        # RESCHEDULE APPOINTMENT
            elif name == "reschedule_appointment":
                if not BUSINESS_ID:
                    raise ValueError("BUSINESS_ID is not configured")

                result = reschedule_appointment(
                    business_id=BUSINESS_ID,
                    appointment_id=args["appointment_id"],
                    customer_phone=args["customer_phone"],
                    new_start_at=args["new_start_at"]
                )

            # UNKNOWN TOOL
            else:
                result = {
                    "success": False,
                    "message": "Unknown tool: " + str(name)
                }

        except Exception as error:
            print("VAPI TOOL ERROR:", repr(error))

            result = {
                "success": False,
                "message": "Unable to process this request. Please try again or contact reception."
            }

        results.append({
            "toolCallId": call_id,
            "result": json.dumps(result, default=str)
        })

    return {
        "results": results
    }
