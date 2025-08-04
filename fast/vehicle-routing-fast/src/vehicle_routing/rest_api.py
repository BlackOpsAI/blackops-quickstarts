from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
from typing import Dict
from dataclasses import asdict

from .domain import VehicleRoutePlan
from .converters import plan_to_model, model_to_plan
from .domain import VehicleRoutePlanModel, VehicleModel, VisitModel
from .score_analysis import ConstraintAnalysisDTO, MatchAnalysisDTO
from .demo_data import generate_demo_data, DemoData
from .solver import solver_manager, solution_manager

app = FastAPI(docs_url='/q/swagger-ui')

data_sets: Dict[str, VehicleRoutePlan] = {}

@app.get("/demo-data", response_model=VehicleRoutePlanModel)
async def get_demo_data() -> VehicleRoutePlanModel:
    """Get a single demo data set (always the same for simplicity)."""
    domain_plan = generate_demo_data(DemoData.PHILADELPHIA)
    return plan_to_model(domain_plan)

@app.get("/route-plans/{problem_id}", response_model=VehicleRoutePlanModel, response_model_exclude_none=True)
async def get_route(problem_id: str) -> VehicleRoutePlanModel:
    route = data_sets.get(problem_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route plan not found")
    route.solver_status = solver_manager.get_solver_status(problem_id)
    return plan_to_model(route)

@app.post("/route-plans")
async def solve_route(request: Request) -> str:
    json_data = await request.json()
    job_id = str(uuid4())
    # Parse the incoming JSON using Pydantic models
    plan_model = VehicleRoutePlanModel.model_validate(json_data)
    # Convert to domain model for solver
    domain_plan = model_to_plan(plan_model)
    data_sets[job_id] = domain_plan
    solver_manager.solve_and_listen(
        job_id,
        domain_plan,
        lambda solution: data_sets.update({job_id: solution})
    )
    return job_id

@app.put("/route-plans/analyze")
async def analyze_route(request: Request) -> dict:
    json_data = await request.json()
    plan_model = VehicleRoutePlanModel.model_validate(json_data)
    domain_plan = model_to_plan(plan_model)
    analysis = solution_manager.analyze(domain_plan)
    constraints = []
    for constraint in getattr(analysis, 'constraint_analyses', []) or []:
        matches = [
            MatchAnalysisDTO(
                name=str(getattr(getattr(match, 'constraint_ref', None), 'constraint_name', "")),
                score=str(getattr(match, 'score', "0hard/0soft")),
                justification=str(getattr(match, 'justification', ""))
            )
            for match in getattr(constraint, 'matches', []) or []
        ]
        constraints.append(ConstraintAnalysisDTO(
            name=str(getattr(constraint, 'constraint_name', "")),
            weight=str(getattr(constraint, 'weight', "0hard/0soft")),
            score=str(getattr(constraint, 'score', "0hard/0soft")),
            matches=matches
        ))
    return {"constraints": [asdict(constraint) for constraint in constraints]}

@app.delete("/route-plans/{problem_id}")
async def stop_solving(problem_id: str) -> None:
    solver_manager.terminate_early(problem_id)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
