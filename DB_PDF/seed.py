import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_creation import init_db, create_call, update_call, add_transcript_entry, add_dispatch

init_db()

# C001
create_call('C001', '+1 (213) 555-0182')
update_call('C001',
    caller_name='Maria Gonzalez',
    location_raw='1247 Maple Ave, Los Angeles, CA',
    latitude=34.0522,
    longitude=-118.2437,
    priority=1,
    emergency_type='Structural Collapse',
    status='active',
    injuries_reported=True,
    hazards_present='Debris',
    num_people_affected=1,
)
add_transcript_entry('C001', 'caller', 'Hello? Please help me, my ceiling collapsed!')
add_transcript_entry('C001', 'ai', "I'm here with you. You're going to be okay. Can you breathe normally right now?")
add_transcript_entry('C001', 'caller', 'Yes I can breathe but my leg is stuck under something heavy')
add_transcript_entry('C001', 'ai', "Good — breathing is the most important thing. Do NOT try to move the debris. Help is already on its way.")
add_dispatch('C001', 'ambulance')
add_dispatch('C001', 'rescue')

# C002
create_call('C002', '+1 (323) 555-0247')
update_call('C002',
    location_raw='589 W 6th St, Los Angeles, CA',
    latitude=34.0625,
    longitude=-118.3087,
    priority=2,
    emergency_type='Gas Leak',
    status='active',
    injuries_reported=False,
    hazards_present='Gas leak',
    num_people_affected=None,
)
add_transcript_entry('C002', 'caller', "There's a really strong gas smell in my building")
add_transcript_entry('C002', 'ai', "Leave the building right now. Do not turn any lights or switches on or off.")
add_dispatch('C002', 'fire')

# C003
create_call('C003', '+1 (310) 555-0391')
update_call('C003',
    caller_name='James Park',
    location_raw='3301 Ocean Park Blvd, Santa Monica, CA',
    latitude=34.0195,
    longitude=-118.4912,
    priority=2,
    emergency_type='Cardiac Event',
    status='dispatched',
    injuries_reported=True,
    hazards_present=None,
    num_people_affected=1,
)
add_transcript_entry('C003', 'caller', "My dad collapsed, he's not responding")
add_transcript_entry('C003', 'ai', "I'm sending help right now. Is he breathing? Put your ear next to his mouth.")
add_dispatch('C003', 'ambulance')
add_dispatch('C003', 'police')

# C004
create_call('C004', '+1 (818) 555-0156')
update_call('C004',
    location_raw='742 N Lake Ave, Pasadena, CA',
    latitude=34.1478,
    longitude=-118.1445,
    priority=3,
    emergency_type='Structural Damage',
    status='pending',
    injuries_reported=False,
    hazards_present='Structural instability',
    num_people_affected=1,
)
add_transcript_entry('C004', 'caller', "The earthquake cracked my walls and I can't get out, my door is jammed")

# C005
create_call('C005', '+1 (562) 555-0088')
update_call('C005',
    caller_name='Aisha Thompson',
    location_raw='1820 E Florence Ave, Compton, CA',
    latitude=33.9731,
    longitude=-118.1788,
    priority=4,
    emergency_type='Minor Injuries',
    status='resolved',
    injuries_reported=True,
    hazards_present=None,
    num_people_affected=1,
)
add_dispatch('C005', 'ambulance')

print("Database seeded successfully.")