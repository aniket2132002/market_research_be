from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.company_info import get_company_info

router = APIRouter()

# Request body model directly here
class CompanyRequest(BaseModel):
    company_name: str

@router.post("/company-info/")
async def company_info(request: CompanyRequest):
    company_name = request.company_name
    try:
        report = get_company_info(company_name)
        return {"company_name": company_name, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
