from .planner import Planner
from utility.model import Metadata, UserProfile, Location


metadata = Metadata(
    query="Can I claim both the Karnataka ESDM subsidy and the SPECS scheme for the same machinery?",
    intents=["explain", "check_eligibility"],
    tools_required=["SchemeExplainer", "EligibilityChecker"],
    entities={"scheme": ["Karnataka ESDM subsidy", "SPECS scheme"]},
    user_profile=UserProfile(
        user_type="woman_entrepreneur",
        location=Location(
            raw="Karnataka",
            city=None,
            state="Karnataka",
            country="India"
        )
    )
)

planner = Planner()
try:
    plan = planner.build_plan(metadata)
    print("Execution Plan:")
    print(plan)
except Exception as e:
    print("Error while planning:", str(e))
