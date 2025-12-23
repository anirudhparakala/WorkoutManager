-- Schema Version Control
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Exercises Library
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    notes TEXT
);

-- Workout Templates
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Exercises within a Template
CREATE TABLE IF NOT EXISTS template_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    order_index INTEGER NOT NULL,
    sets INTEGER DEFAULT 3,
    reps INTEGER DEFAULT 10,
    weight REAL,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id),
    UNIQUE (template_id, order_index)
);

-- Sets for Template Exercises (Detailed planning)
CREATE TABLE IF NOT EXISTS template_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    reps INTEGER,
    weight REAL,
    FOREIGN KEY (template_exercise_id) REFERENCES template_exercises(id) ON DELETE CASCADE,
    UNIQUE (template_exercise_id, set_number)
);

-- Scheduled/Actual Workouts
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    name TEXT,
    status TEXT CHECK(status IN ('PLANNED', 'ACTIVE', 'COMPLETED')) DEFAULT 'PLANNED',
    plan_type TEXT CHECK(plan_type IN ('WORKOUT', 'REST')) DEFAULT 'WORKOUT',
    template_id INTEGER,
    started_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date);
CREATE INDEX IF NOT EXISTS idx_workouts_status ON workouts(status);

-- Exercises within a Workout (Snapshot of template or ad-hoc)
CREATE TABLE IF NOT EXISTS workout_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    order_index INTEGER NOT NULL,
    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id),
    UNIQUE (workout_id, order_index)
);

-- Sets for each Workout Exercise
CREATE TABLE IF NOT EXISTS sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    planned_reps INTEGER,
    planned_weight REAL,
    actual_reps INTEGER,
    actual_weight REAL,
    completed BOOLEAN DEFAULT 0,
    FOREIGN KEY (workout_exercise_id) REFERENCES workout_exercises(id) ON DELETE CASCADE,
    UNIQUE (workout_exercise_id, set_number)
);
