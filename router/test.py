from .planner import Planner
from .model import Metadata, UserProfile


metadata = Metadata(
    intents=["explain", "check_eligibility"],
    tools_required=["SchemeExplainer", "EligibilityChecker"],
    entities={"scheme": "PMEGP"},
    user_profile=UserProfile(
        user_type="woman_entrepreneur",
        location="Karnataka"
    )
)
planner = Planner()
try:
    plan = planner.build_plan(metadata)
    print("Execution Plan:")
    print(plan)
except Exception as e:
    print("Error while planning:", str(e))
