# --- STEP 1: AUTH & IMPORTS ---
from google.colab import auth
auth.authenticate_user()
import gspread
from google.auth import default
import pandas as pd
from datetime import datetime

creds, _ = default()
gc = gspread.authorize(creds)

# --- STEP 2: DATA CONNECTION ---
# Double-check this ID matches your spreadsheet URL
SHEET_ID = '1nOIQoEMEQz2SeKmWem_knjPb4KfwPgi6iPNwel2RSx4'
spreadsheet = gc.open_by_key(SHEET_ID)

def load_data():
    # We use get_all_records() but wrap it in a cleaner way to avoid header issues
    missions = pd.DataFrame(spreadsheet.worksheet("missions").get_all_records())
    pilots = pd.DataFrame(spreadsheet.worksheet("pilot_roster").get_all_records())
    drones = pd.DataFrame(spreadsheet.worksheet("drone_fleet").get_all_records())
    return missions, pilots, drones

# --- STEP 3: LOGIC ENGINE ---
def check_conflicts(mission, pilot, drone):
    reasons = []

    # 1. Weather Logic (Standardize to string to prevent errors)
    weather = str(mission.get('weather_forecast', '')).strip()
    resistance = str(drone.get('weather_resistance', '')).strip()
    if weather == "Rainy" and "IP43" not in resistance:
        reasons.append(f"Drone {drone['drone_id']} not waterproof")

    # 2. Certification Logic
    req_certs = set([c.strip() for c in str(mission['required_certs']).split(',') if c.strip()])
    pilot_certs = set([c.strip() for c in str(pilot['certifications']).split(',') if c.strip()])
    if not req_certs.issubset(pilot_certs):
        reasons.append(f"Pilot lacks certs: {req_certs - pilot_certs}")

    # 3. Budget Logic
    try:
        fmt = '%Y-%m-%d'
        start = datetime.strptime(str(mission['start_date']), fmt)
        end = datetime.strptime(str(mission['end_date']), fmt)
        duration = (end - start).days + 1
        total_cost = duration * int(pilot['daily_rate_inr'])

        if total_cost > int(mission['mission_budget_inr']):
            reasons.append(f"Budget exceeded ({total_cost} > {mission['mission_budget_inr']})")
    except Exception as e:
        reasons.append(f"Date/Cost formatting error: {e}")

    return reasons

# --- STEP 4: URGENT REASSIGNMENT ---
def handle_urgent_reassignment(mission, pilots_df):
    print("\n🚨 [SYSTEM ALERT] Initiating Urgent Reassignment Protocol...")
    req_certs = set([c.strip() for c in str(mission['required_certs']).split(',') if c.strip()])
    solutions_found = False

    for _, pilot in pilots_df.iterrows():
        pilot_certs = set([c.strip() for c in str(pilot['certifications']).split(',') if c.strip()])
        if req_certs.issubset(pilot_certs) and pilot['status'] != 'On Leave':

            start = datetime.strptime(str(mission['start_date']), '%Y-%m-%d')
            end = datetime.strptime(str(mission['end_date']), '%Y-%m-%d')
            duration = (end - start).days + 1
            relocation_cost = (duration * int(pilot['daily_rate_inr'])) + 2000

            if relocation_cost <= int(mission['mission_budget_inr']):
                solutions_found = True
                print(f"💡 RECOMMENDATION: Relocate {pilot['name']} ({pilot['pilot_id']}) from {pilot['location']} to {mission['location']}.")
                print(f"   Estimated Cost: {relocation_cost} INR (Within Budget)")
                if pilot['status'] == 'Assigned':
                    print(f"   ⚠️ WARNING: Requires pulling pilot from current assignment.")

    if not solutions_found:
        print("❌ CRITICAL: No pilots found globally meeting criteria.")

# --- STEP 5: SYNC & INTERFACE ---
def sync_assignment(pilot_id, drone_id, project_id):
    print(f"Syncing {project_id} to cloud...")
    try:
        # Update Pilot
        p_ws = spreadsheet.worksheet("pilot_roster")
        p_cell = p_ws.find(str(pilot_id))
        p_ws.update_cell(p_cell.row, 6, "Assigned")
        p_ws.update_cell(p_cell.row, 7, project_id)

        # Update Drone
        d_ws = spreadsheet.worksheet("drone_fleet")
        d_cell = d_ws.find(str(drone_id))
        d_ws.update_cell(d_cell.row, 4, "Assigned")
        d_ws.update_cell(d_cell.row, 6, project_id)
        print(f"✅ SUCCESS: Google Sheets updated for {project_id}!")
    except Exception as e:
        print(f"❌ Sync Error: Ensure IDs exist in sheets. {e}")

def find_matches(project_id):
    missions_df, pilots_df, drones_df = load_data()

    mission = missions_df[missions_df['project_id'] == project_id]
    if mission.empty:
        print(f"❌ Project {project_id} not found.")
        return
    mission = mission.iloc[0]

    print(f"\n--- Analyzing {project_id} | Priority: {mission['priority']} | Location: {mission['location']} ---")
    valid_pairings = []

    for _, pilot in pilots_df.iterrows():
        # Clean data for comparison
        p_status = str(pilot['status']).strip()
        p_loc = str(pilot['location']).strip()
        m_loc = str(mission['location']).strip()

        if p_status == 'Available' and p_loc == m_loc:
            for _, drone in drones_df.iterrows():
                d_status = str(drone['status']).strip()
                d_loc = str(drone['location']).strip()

                if d_status == 'Available' and d_loc == m_loc:
                    conflicts = check_conflicts(mission, pilot, drone)
                    if not conflicts:
                        valid_pairings.append((pilot['name'], pilot['pilot_id'], drone['drone_id']))

    if valid_pairings:
        print(f"✅ Viable local pairings found:")
        for p_name, p_id, d_id in valid_pairings:
            print(f"   - Pilot: {p_name} ({p_id}) | Drone: {d_id}")
    elif str(mission['priority']) == 'Urgent':
        handle_urgent_reassignment(mission, pilots_df)
    else:
        print("❌ No local matches found. No urgent protocol triggered for standard mission.")

def run_agent():
    print("Skylark AI Drone Coordinator Active.")
    print("Commands: 'check [ProjectID]', 'assign [ProjectID] [PilotID] [DroneID]', 'exit'")
    while True:
        cmd = input("\nYou: ").strip()
        if not cmd: continue
        if cmd.lower() == 'exit': break

        parts = cmd.split()
        if "check" in cmd.lower() and len(parts) > 1:
            find_matches(parts[1].upper())
        elif "assign" in cmd.lower() and len(parts) == 4:
            sync_assignment(parts[2].upper(), parts[3].upper(), parts[1].upper())
        else:
            print("Unknown command. Try: 'check PRJ001' or 'assign PRJ001 P001 D001'")

# Launch
run_agent()
