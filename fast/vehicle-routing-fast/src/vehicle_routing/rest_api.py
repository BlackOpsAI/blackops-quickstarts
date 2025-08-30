from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
from typing import Dict
from dataclasses import asdict

from .domain import VehicleRoutePlan
from .converters import plan_to_model, model_to_plan
from .domain import VehicleRoutePlanModel
from .score_analysis import ConstraintAnalysisDTO, MatchAnalysisDTO
from .demo_data import generate_demo_data, DemoData
from .solver import solver_manager, solution_manager

app = FastAPI(docs_url='/q/swagger-ui')

data_sets: Dict[str, VehicleRoutePlan] = {}


def json_to_vehicle_route_plan(json_data: dict) -> VehicleRoutePlan:
    """Convert JSON data to VehicleRoutePlan using the model converters."""
    plan_model = VehicleRoutePlanModel.model_validate(json_data)
    return model_to_plan(plan_model)


@app.get("/demo-data")
async def get_demo_data():
    """Get available demo data sets."""
    return [demo.name for demo in DemoData]

@app.get("/demo-data/{demo_name}", response_model=VehicleRoutePlanModel)
async def get_demo_data_by_name(demo_name: str) -> VehicleRoutePlanModel:
    """Get a specific demo data set."""
    try:
        demo_data = DemoData[demo_name]
        domain_plan = generate_demo_data(demo_data)
        return plan_to_model(domain_plan)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Demo data '{demo_name}' not found")

@app.get("/route-plans/{problem_id}", response_model=VehicleRoutePlanModel, response_model_exclude_none=True)
async def get_route(problem_id: str) -> VehicleRoutePlanModel:
    route = data_sets.get(problem_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route plan not found")
    route.solver_status = solver_manager.get_solver_status(problem_id)
    return plan_to_model(route)

@app.post("/route-plans")
async def solve_route(plan_model: VehicleRoutePlanModel) -> str:
    job_id = str(uuid4())
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
async def analyze_route(plan_model: VehicleRoutePlanModel) -> dict:
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
