"""
Profit calculation engine for crop recommendations
"""
from typing import Dict, List
from ..utils.crop_database import get_crops_by_season


def calculate_expected_profit(payload: Dict, recommendations: Dict) -> Dict:
    """
    Calculate expected profit for each recommended crop in each section
    
    Args:
        payload: Original request payload with budget and sections
        recommendations: Crop recommendations from recommendation_engine
    
    Returns:
        Dictionary with expected profit for each crop in each section
    """
    total_budget = payload.get("budget", 100000)
    sections = payload.get("sections", [])
    season = payload.get("season", "kharif")
    
    num_sections = len(sections)
    if num_sections == 0:
        return {}
    
    # Distribute budget equally across sections
    section_budget = total_budget / num_sections
    
    # Get crop database for reference
    all_crops = get_crops_by_season(season)
    crop_lookup = {crop["name"]: crop for crop in all_crops}
    
    profit_data = {}
    
    for section, crops in recommendations.items():
        section_profits = []
        
        for crop_rec in crops:
            crop_name = crop_rec["crop"]
            crop_risk = crop_rec["risk"]
            crop_budget = crop_rec["budget"]
            
            # Get full crop data
            crop_data = crop_lookup.get(crop_name)
            
            if not crop_data:
                continue
            
            # Calculate profit
            # Profit = (Yield * Market Price) - Cost
            # Adjusted for risk: higher risk reduces expected yield
            
            base_yield = crop_data["base_yield_per_acre"]
            market_price = crop_data["market_price_per_quintal"]
            base_cost = crop_data["base_cost_per_acre"]
            
            # Risk adjustment: reduce expected yield based on risk
            risk_factor = 1 - (crop_risk * 0.5)  # Max 50% reduction for highest risk
            adjusted_yield = base_yield * risk_factor
            
            # Revenue
            revenue = adjusted_yield * market_price
            
            # Cost (use actual budget if it fits, otherwise use base cost)
            actual_cost = min(section_budget, base_cost)
            
            # Expected profit
            expected_profit = revenue - actual_cost
            
            section_profits.append({
                "crop": crop_name,
                "expected_profit": round(expected_profit, 2),
                "sectionBudget": round(section_budget, 2),
                "risk": crop_risk,
                "cost": round(actual_cost, 2),
            })
        
        profit_data[section] = section_profits
    
    return profit_data