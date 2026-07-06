from __future__ import annotations


class TimeEngine:
    def forecast_battery_health(
        self, current_health: float, months: int, monthly_degradation: float = 0.01
    ) -> dict:
        if not 0 <= current_health <= 1:
            raise ValueError("current_health must be between 0 and 1")
        if months < 0:
            raise ValueError("months must be >= 0")
        projected = max(0.0, current_health - (monthly_degradation * months))
        return {
            "current_health": current_health,
            "months": months,
            "monthly_degradation": monthly_degradation,
            "projected_health": projected,
        }
