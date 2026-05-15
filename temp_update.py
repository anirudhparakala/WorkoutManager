from services.planner_service import assign_workout
from services.templates_service import get_all_templates
import datetime

# Find template IDs
templates = get_all_templates()
upper_mixed_id = None
accessory_day_id = None

for t in templates:
    name = t['name'].lower()
    if 'upper' in name and 'mixed' in name:
        upper_mixed_id = t['id']
    if 'accessory' in name:
        accessory_day_id = t['id']

if upper_mixed_id:
    print(f"Assigning Upper Mixed (ID: {upper_mixed_id}) to Thursday (2025-12-25)")
    assign_workout('2025-12-25', upper_mixed_id)
else:
    print("Upper Mixed template not found")

if accessory_day_id:
    print(f"Assigning Accessory Day (ID: {accessory_day_id}) to Friday (2025-12-26)")
    assign_workout('2025-12-26', accessory_day_id)
else:
    print("Accessory Day template not found")

# Now run bulk schedule
from bulk_schedule import bulk_schedule
bulk_schedule()
