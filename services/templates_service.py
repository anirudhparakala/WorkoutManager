from repos import templates_repo

class ValidationError(Exception):
    pass

def validate_template_name(name):
    if not name or not name.strip():
        raise ValidationError("Template name cannot be empty.")

def validate_set_data(reps, weight):
    if reps is not None and reps < 1:
        raise ValidationError("Reps must be at least 1.")
    if weight is not None and weight < 0:
        raise ValidationError("Weight cannot be negative.")

def create_template(name):
    validate_template_name(name)
    return templates_repo.create_template(name.strip())

def update_template(template_id, name):
    validate_template_name(name)
    templates_repo.update_template(template_id, name.strip())

def add_set(template_exercise_id, reps, weight):
    validate_set_data(reps, weight)
    templates_repo.add_set(template_exercise_id, reps, weight)

def update_set(set_id, reps, weight):
    validate_set_data(reps, weight)
    templates_repo.update_set(set_id, reps, weight)

# Pass-through methods
def get_all_templates():
    return templates_repo.get_all_templates()

def get_template(template_id):
    return templates_repo.get_template(template_id)

def delete_template(template_id):
    return templates_repo.delete_template(template_id)

def add_exercise(template_id, exercise_id):
    return templates_repo.add_exercise(template_id, exercise_id)

def remove_exercise(template_exercise_id):
    return templates_repo.remove_exercise(template_exercise_id)

def reorder_exercises(template_id, new_order_ids):
    return templates_repo.reorder_exercises(template_id, new_order_ids)

def delete_set(set_id):
    return templates_repo.delete_set(set_id)
