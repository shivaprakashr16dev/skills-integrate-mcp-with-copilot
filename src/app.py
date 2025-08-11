"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel, Field, Session, create_engine, select
import os
from pathlib import Path
from typing import List, Optional, Dict

DB_PATH = os.environ.get("APP_DB_PATH", os.path.join(Path(__file__).parent.parent, "data", "app.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str
    schedule: str
    max_participants: int


class Enrollment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    activity_id: int = Field(foreign_key="activity.id")
    email: str = Field(index=True)


def init_db_and_seed():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        existing = session.exec(select(Activity)).first()
        if existing:
            return
        seed_data: Dict[str, Dict] = {
            "Chess Club": {
                "description": "Learn strategies and compete in chess tournaments",
                "schedule": "Fridays, 3:30 PM - 5:00 PM",
                "max_participants": 12,
                "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
            },
            "Programming Class": {
                "description": "Learn programming fundamentals and build software projects",
                "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
                "max_participants": 20,
                "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
            },
            "Gym Class": {
                "description": "Physical education and sports activities",
                "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
                "max_participants": 30,
                "participants": ["john@mergington.edu", "olivia@mergington.edu"],
            },
            "Soccer Team": {
                "description": "Join the school soccer team and compete in matches",
                "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
                "max_participants": 22,
                "participants": ["liam@mergington.edu", "noah@mergington.edu"],
            },
            "Basketball Team": {
                "description": "Practice and play basketball with the school team",
                "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["ava@mergington.edu", "mia@mergington.edu"],
            },
            "Art Club": {
                "description": "Explore your creativity through painting and drawing",
                "schedule": "Thursdays, 3:30 PM - 5:00 PM",
                "max_participants": 15,
                "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
            },
            "Drama Club": {
                "description": "Act, direct, and produce plays and performances",
                "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
                "max_participants": 20,
                "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
            },
            "Math Club": {
                "description": "Solve challenging problems and participate in math competitions",
                "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
                "max_participants": 10,
                "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
            },
            "Debate Team": {
                "description": "Develop public speaking and argumentation skills",
                "schedule": "Fridays, 4:00 PM - 5:30 PM",
                "max_participants": 12,
                "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
            },
        }
        for name, data in seed_data.items():
            act = Activity(name=name, description=data["description"], schedule=data["schedule"], max_participants=data["max_participants"])
            session.add(act)
            session.flush()  # get id
            for email in data["participants"]:
                session.add(Enrollment(activity_id=act.id, email=email))
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

@app.on_event("startup")
def on_startup():  # pragma: no cover - framework hook
    init_db_and_seed()

# Ensure DB exists when imported outside ASGI server (e.g., TestClient without startup events)
init_db_and_seed()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(session: Session = Depends(get_session)):
    activities_out = {}
    results = session.exec(select(Activity)).all()
    for act in results:
        emails = session.exec(select(Enrollment.email).where(Enrollment.activity_id == act.id)).all()
        activities_out[act.name] = {
            "description": act.description,
            "schedule": act.schedule,
            "max_participants": act.max_participants,
            "participants": list(emails),
        }
    return activities_out


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, session: Session = Depends(get_session)):
    activity = session.exec(select(Activity).where(Activity.name == activity_name)).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    already = session.exec(select(Enrollment).where(Enrollment.activity_id == activity.id, Enrollment.email == email)).first()
    if already:
        raise HTTPException(status_code=400, detail="Student is already signed up")
    enrollment = Enrollment(activity_id=activity.id, email=email)
    session.add(enrollment)
    session.commit()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, session: Session = Depends(get_session)):
    activity = session.exec(select(Activity).where(Activity.name == activity_name)).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    enrollment = session.exec(select(Enrollment).where(Enrollment.activity_id == activity.id, Enrollment.email == email)).first()
    if not enrollment:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")
    session.delete(enrollment)
    session.commit()
    return {"message": f"Unregistered {email} from {activity_name}"}
