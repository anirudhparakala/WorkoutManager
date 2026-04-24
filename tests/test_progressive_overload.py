"""
Test Progressive Overload System

Tests the rotating cursor algorithm:
1. Cursor initialization (set 3 or last set)
2. Suggestion computation (last_actual + 1)
3. Cursor advancement on exact target match
4. Cursor stays on mismatch
5. Wrap-around (last set -> set 1)

Run: streamlit run tests/test_progressive_overload.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(page_title="Test: Progressive Overload", page_icon="🧪")

from repos.runner_repo import (
    create_session_from_template, get_active_session, get_workout_set,
    get_last_completed_workout_for_template, get_overload_cursor, set_overload_cursor,
    complete_workout_session
)
from repos.templates_repo import create_template, add_exercise, add_set
from repos.exercises_repo import create_exercise, get_all_exercises
from db.conn import execute, query_one
from services.runner_service import complete_set, get_progressive_overload_targets
from db.migrations import migrate
import datetime

migrate()

passed = 0
failed = 0

def check(label, condition):
    global passed, failed
    if condition:
        st.success(f"✅ {label}")
        passed += 1
    else:
        st.error(f"❌ {label}")
        failed += 1


st.title("🧪 Progressive Overload Tests")

# --- SETUP ---
st.header("Setup")
test_id = datetime.datetime.now().strftime('%H%M%S')
date_week1 = f"2099-01-{10 + int(test_id[-1])}"  # Unique test dates
date_week2 = f"2099-02-{10 + int(test_id[-1])}"

# Cleanup test data
execute("DELETE FROM workouts WHERE date LIKE '2099-%'")
execute("DELETE FROM overload_tracking WHERE template_id IN (SELECT id FROM templates WHERE name LIKE 'OL Test%')")
execute("DELETE FROM templates WHERE name LIKE 'OL Test%'")

# Create test template with exercises
template_name = f"OL Test {test_id}"
tid = create_template(template_name)
st.write(f"Created template: {template_name} (id={tid})")

# Ensure test exercises exist
exercises = get_all_exercises()
ex_names = [e['name'] for e in exercises]
if "Test Bench Press" not in ex_names:
    create_exercise("Test Bench Press")
if "Test Curl" not in ex_names:
    create_exercise("Test Curl")

exercises = get_all_exercises()
bench_id = next(e['id'] for e in exercises if e['name'] == "Test Bench Press")
curl_id = next(e['id'] for e in exercises if e['name'] == "Test Curl")

# Bench Press: 3 sets (cursor should start at set 3)
te_bench = add_exercise(tid, bench_id)
add_set(te_bench, 10, 100)  # Set 1: 10 reps @ 100
add_set(te_bench, 10, 100)  # Set 2: 10 reps @ 100
add_set(te_bench, 8, 100)   # Set 3: 8 reps @ 100

# Curl: 2 sets (cursor should start at set 2)
te_curl = add_exercise(tid, curl_id)
add_set(te_curl, 12, 25)    # Set 1: 12 reps @ 25
add_set(te_curl, 10, 25)    # Set 2: 10 reps @ 25

st.write(f"Bench Press: 3 sets, Curl: 2 sets")

st.divider()

# ===========================
# TEST 1: No prior workout -> no suggestions
# ===========================
st.header("Test 1: No Prior Workout")

wid1 = create_session_from_template(date_week1, tid)
targets = get_progressive_overload_targets(wid1)
check("No suggestions when no prior workout exists", len(targets) == 0)

st.divider()

# ===========================
# TEST 2: Complete Week 1, check suggestions for Week 2
# ===========================
st.header("Test 2: Complete Week 1 → Check Week 2 Suggestions")

# Complete all sets for week 1
# Bench: order_index=1, sets 1-3
complete_set(wid1, 1, 1, 10, 100)  # Set 1: 10 reps
complete_set(wid1, 1, 2, 10, 100)  # Set 2: 10 reps
complete_set(wid1, 1, 3, 8, 100)   # Set 3: 8 reps
# Curl: order_index=2, sets 1-2
complete_set(wid1, 2, 1, 12, 25)   # Set 1: 12 reps
complete_set(wid1, 2, 2, 10, 25)   # Set 2: 10 reps

# Mark session complete
complete_workout_session(wid1)
st.write("Week 1 completed. Bench: 10/10/8, Curl: 12/10")

# Start week 2
wid2 = create_session_from_template(date_week2, tid)
targets2 = get_progressive_overload_targets(wid2)
st.write(f"Week 2 targets: {targets2}")

# Bench cursor should be at set 3 (min(3, 3) = 3), suggest 8+1=9
bench_target = targets2.get((bench_id, 3))
check("Bench: cursor initialized at set 3", bench_target is not None)
check("Bench: suggests 9 reps (was 8+1)", bench_target and bench_target['suggested_reps'] == 9)
check("Bench: last_reps = 8", bench_target and bench_target['last_reps'] == 8)

# Curl cursor should be at set 2 (min(3, 2) = 2), suggest 10+1=11
curl_target = targets2.get((curl_id, 2))
check("Curl: cursor initialized at set 2", curl_target is not None)
check("Curl: suggests 11 reps (was 10+1)", curl_target and curl_target['suggested_reps'] == 11)

st.divider()

# ===========================
# TEST 3: Cursor stays on miss
# ===========================
st.header("Test 3: Miss Target → Cursor Stays")

# Complete bench set 3 with 8 reps (target was 9) — miss
complete_set(wid2, 1, 3, 8, 100)

# Check cursor didn't move
cursor_bench = get_overload_cursor(tid, bench_id)
check("Bench: cursor stays at set 3 after miss", cursor_bench == 3)

st.divider()

# ===========================
# TEST 4: Cursor advances on hit
# ===========================
st.header("Test 4: Hit Target → Cursor Advances")

# We need a clean week 2 for this test, but set 3 is already completed
# Let's test with curl instead — complete set 2 with 11 reps (target is 11)
complete_set(wid2, 2, 2, 11, 25)

cursor_curl = get_overload_cursor(tid, curl_id)
check("Curl: cursor advances from set 2 → set 1 (wrap-around with 2 sets)", cursor_curl == 1)

st.divider()

# ===========================
# TEST 5: Cursor wrap-around with 3 sets
# ===========================
st.header("Test 5: Wrap-Around Behavior (3 sets)")

# Manually set bench cursor to set 3 and simulate hit
set_overload_cursor(tid, bench_id, 3)
cursor_before = get_overload_cursor(tid, bench_id)
st.write(f"Bench cursor before: set {cursor_before}")

# Simulate: cursor at 3, last workout had 8 reps on set 3
# If we complete with 9 (8+1), it should advance to set 1
# But wid2 set 3 is already completed with 8 reps (miss), so the check already ran
# Let's verify the advancement logic directly
from services.runner_service import check_and_advance_overload

# Reset and test directly with wid1 as "last workout"
# Create a fresh session for this test
date_test5 = "2099-03-15"
execute("DELETE FROM workouts WHERE date = ?", (date_test5,))
wid_test5 = create_session_from_template(date_test5, tid)

# Set cursor to 3, last workout (wid1) had 8 on set 3
set_overload_cursor(tid, bench_id, 3)

# Complete set 3 with 9 (= 8 + 1 = target hit!)
complete_set(wid_test5, 1, 3, 9, 100)

cursor_after = get_overload_cursor(tid, bench_id)
check(f"Bench: cursor wraps from 3 → 1 (got {cursor_after})", cursor_after == 1)

st.divider()

# ===========================
# TEST 6: get_last_completed_workout excludes current
# ===========================
st.header("Test 6: Last Workout Lookup Excludes Current")

last_ex = get_last_completed_workout_for_template(tid, exclude_workout_id=wid1)
# wid1 is COMPLETED, but excluded → should return None (no other completed workouts yet)
# Actually wid2 is still ACTIVE... let's check
check("Excluding wid1 returns None (only completed workout)", last_ex is None)

# Including wid1 (not excluding)
last_ex_inc = get_last_completed_workout_for_template(tid)
check("Not excluding returns wid1 data", last_ex_inc is not None)

st.divider()

# ===========================
# SUMMARY
# ===========================
st.header("Results")
total = passed + failed
st.metric("Passed", f"{passed}/{total}")
if failed > 0:
    st.error(f"❌ {failed} test(s) failed")
else:
    st.success("✅ All tests passed!")

# Cleanup
st.divider()
if st.button("🧹 Cleanup Test Data"):
    execute("DELETE FROM workouts WHERE date LIKE '2099-%'")
    execute("DELETE FROM overload_tracking WHERE template_id = ?", (tid,))
    execute("DELETE FROM templates WHERE id = ?", (tid,))
    st.success("Cleaned up.")
    st.rerun()
