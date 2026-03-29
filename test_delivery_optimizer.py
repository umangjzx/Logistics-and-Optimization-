import unittest
from delivery_optimizer import (
    load_deliveries,
    sort_deliveries,
    assign_deliveries,
    classify_zone,
    compute_analytics
)

class TestDeliveryOptimizer(unittest.TestCase):
    def test_classify_zone(self):
        # Delhi should be North based on bounding box
        self.assertEqual(classify_zone(28.61, 77.21), "North")
        # Chennai should be South
        self.assertEqual(classify_zone(13.08, 80.27), "South")
        # Invalid coordinates
        self.assertEqual(classify_zone(0, 0), "Unknown")

    def test_sort_deliveries(self):
        deliveries = [
            {"Location_ID": "A", "Priority": "Low", "Distance_km": 100},
            {"Location_ID": "B", "Priority": "High", "Distance_km": 50},
            {"Location_ID": "C", "Priority": "High", "Distance_km": 200},
            {"Location_ID": "D", "Priority": "Medium", "Distance_km": 150},
        ]
        sorted_dels = sort_deliveries(deliveries)
        
        # Expected priorities order: High, Medium, Low.
        # Within High: C (200) before B (50) due to LPT descending sort.
        self.assertEqual(sorted_dels[0]["Location_ID"], "C") # High, 200
        self.assertEqual(sorted_dels[1]["Location_ID"], "B") # High, 50
        self.assertEqual(sorted_dels[2]["Location_ID"], "D") # Medium, 150
        self.assertEqual(sorted_dels[3]["Location_ID"], "A") # Low, 100

    def test_assign_deliveries(self):
        # Evenly matching deliveries for 3 agents
        deliveries = [
            {"Location_ID": "A", "Distance_km": 100, "Priority": "High"},
            {"Location_ID": "B", "Distance_km": 100, "Priority": "High"},
            {"Location_ID": "C", "Distance_km": 100, "Priority": "High"},
            {"Location_ID": "D", "Distance_km": 50, "Priority": "Medium"},
            {"Location_ID": "E", "Distance_km": 50, "Priority": "Medium"},
            {"Location_ID": "F", "Distance_km": 50, "Priority": "Medium"},
        ]
        
        assignments, totals = assign_deliveries(deliveries, 3)
        self.assertEqual(len(assignments[1]), 2)
        self.assertEqual(len(assignments[2]), 2)
        self.assertEqual(len(assignments[3]), 2)
        
        self.assertEqual(totals[1], 150)
        self.assertEqual(totals[2], 150)
        self.assertEqual(totals[3], 150)

if __name__ == '__main__':
    unittest.main()
