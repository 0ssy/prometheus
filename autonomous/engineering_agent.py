"""
Engineering Agent (RFC 0004)
-----------------------------------------
Implements the pipeline: propose -> simulate -> test -> report.
NEVER deploys — a hard stop by design. Extends Phase Alpha's
PrometheusAgent, dispatched through the existing
/agents/{agent_name}/dispatch route — no new API surface needed.
"""
from agents.base import PrometheusAgent
from reasoning.graph import assert_fact
from delta.twin import build_twin
from .proposals import Proposal
from .simulator import simulate_proposal
from .tester import run_tests
from .reporter import build_report


class EngineeringAgent(PrometheusAgent):
    name = "engineering_agent"

    def perform(self, task: dict, context: dict) -> dict:
        db = context["db"]

        proposal = Proposal(
            name=task["name"],
            description=task.get("description", ""),
            change_type=task["change_type"],
            payload=task.get("payload", {}),
        )
        proposal.validate()

        device_id = task.get("device_id", "epsilon_demo_device")
        base_twin = build_twin(db, device_id).to_dict()

        simulated_twin = simulate_proposal(proposal, base_twin)
        test_results = run_tests(base_twin, simulated_twin, proposal)
        report = build_report(proposal, test_results)

        assert_fact(
            db, subject=proposal.name, predicate="event",
            obj=f"engineering_proposal_evaluated:{'pass' if report.all_tests_passed else 'fail'}",
        )

        return {
            "agent": self.name,
            "proposal": proposal.to_dict(),
            "simulated_twin": simulated_twin,
            "report": report.to_dict(),
        }
