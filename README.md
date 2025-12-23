# Workout Manager

## Behavioral Rules

### Time & Date
- **Timezone**: `America/New_York`
- **Week Definition**: Sunday to Saturday

### Rest Day Handling
- **Week Completion**: Rest days must be accounted for to achieve a perfect weekly consistency streak.
- **Completion Mode**: **Mode A (Auto-satisfied)**. Rest days are automatically considered "completed" without user intervention.

### Workout Execution
- **Actuals**: The system records the actual reps and weight performed for every set.
- **Editing Constraints**: Editing of actuals is allowed **only** while the session is active or paused. Editing is **disabled** once the session status is `COMPLETED`.
- **Concurrency**: There can be only **one ACTIVE session** per date.
