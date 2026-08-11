#!/usr/bin/env python3
"""
Spacebar Fleet Manager — Core Council Always-On + On-Demand Team Activation

Architecture:
  Core Council (9 bots) run 24/7: CoS + 8 domain leads
  Specialist teams (35 bots) remain on STANDBY until activated by their council lead
  
Team Ownership:
  technology-lead → development-lead, dev-lead, docs-lead, docs-lead-dev, qa-lead, skills-lead, integration-lead, automation-lead
  intelligence-lead → history-lead, pulse, security-lead, cyber-osint, threat-lead, media-lead, creative-lead, writing-lead, nova, notes, lane
  portfolio-lead → odds-lead, data-lead, verifier, assistant, product-lead, admin, people, analyst, scout
  growth-lead → manufacturing-lead, ai-agency
  operations-lead → wellbeing-lead, health-performance, market-lead, outreach-lead
  counsel-lead → legal-case-support
  treasury-lead → (standalone)
  compliance-lead → (standalone)

Usage:
  python manage-fleet.py deploy     # Kill all, start only core 9
  python manage-fleet.py activate <team>   # Start a standby team
  python manage-fleet.py deactivate <team> # Stop a team
  python manage-fleet.py status     # Show all bot states
  python manage-fleet.py start <bot>  # Start one bot
  python manage-fleet.py kill <bot>   # Kill one bot
"""
import subprocess, os, sys, time, ctypes, json, signal

profiles_dir = os.path.expanduser('~/AppData/Local/hermes/profiles')
hermes_venv = os.path.expanduser('~/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe')
gateway_script = '${MY_REPOS}/Documents/github/agent-fleet/scripts/spacebar-gateway.py'
CREATE_NO_WINDOW = 0x08000000

# Team definitions — map council leads to their specialist teams
TEAMS = {
    'technology': ['development-lead', 'dev-lead', 'docs-lead', 'docs-lead-dev', 'qa-lead', 'skills-lead', 'integration-lead', 'automation-lead'],
    'intelligence': ['history-lead', 'pulse', 'security-lead', 'cyber-osint', 'threat-lead', 'media-lead', 'creative-lead', 'writing-lead', 'nova', 'notes', 'lane'],
    'investment': ['odds-lead', 'data-lead', 'verifier', 'assistant', 'product-lead', 'admin', 'people', 'analyst', 'scout'],
    'revenue': ['manufacturing-lead', 'ai-agency'],
    'operations': ['wellbeing-lead', 'health-performance', 'market-lead', 'outreach-lead'],
    'legal': ['legal-case-support'],
    'finance': [],
    'tax': [],
}

CORE_COUNCIL = ['chief-of-staff', 'technology-lead', 'growth-lead', 'intelligence-lead',
                'treasury-lead', 'counsel-lead', 'compliance-lead', 'portfolio-lead', 'operations-lead']

kernel32 = ctypes.windll.kernel32

def pid_alive(pid):
    if not pid: return False
    h = kernel32.OpenProcess(0x400, False, pid)
    if not h: return False
    kernel32.CloseHandle(h)
    return True

def kill_bot(profile_name):
    sf = os.path.join(profiles_dir, profile_name, 'gateway_state.json')
    if os.path.exists(sf):
        try:
            with open(sf) as f:
                state = json.load(f)
            pid = state.get('pid', 0)
            if pid and pid_alive(pid):
                os.kill(pid, signal.SIGTERM)
                print(f"  Killed {profile_name} (PID {pid})")
                return True
        except:
            pass
    return False

def start_bot(profile_name):
    env_sb = os.path.join(profiles_dir, profile_name, '.env.spacebar')
    if not os.path.exists(env_sb):
        print(f"  SKIP {profile_name}: no .env.spacebar")
        return False

    config = {
        'SPACEBAR_API_URL': 'http://localhost:3100/api/v9',
        'SPACEBAR_GATEWAY_URL': 'ws://localhost:3100/',
        'DISCORD_AUTO_THREAD': 'false',
        'DISCORD_REQUIRE_MENTION': 'false',
        'DISCORD_ALLOWED_USERS': '*',
        'GATEWAY_ALLOW_ALL_USERS': 'true',
    }
    with open(env_sb) as f:
        for line in f:
            line = line.strip()
            if line.startswith('export SPACEBAR_BOT_TOKEN'):
                raw = line.split('=', 1)[1].strip().strip("'\" \t\r\n")
                config['SPACEBAR_BOT_TOKEN'] = raw
                config['DISCORD_BOT_TOKEN'] = raw
            elif line.startswith('export SPACEBAR_GATEWAY_URL'):
                config['SPACEBAR_GATEWAY_URL'] = line.split('=', 1)[1].strip().strip("'\" \t\r\n")
            elif line.startswith('export SPACEBAR_GUILD_ID'):
                config['SPACEBAR_GUILD_ID'] = line.split('=', 1)[1].strip().strip("'\" \t\r\n")
            elif line.startswith('export SPACEBAR_API_URL'):
                config['SPACEBAR_API_URL'] = line.split('=', 1)[1].strip().strip("'\" \t\r\n")

    env = os.environ.copy()
    env.update(config)
    try:
        proc = subprocess.Popen(
            [hermes_venv, gateway_script, profile_name],
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print(f"  Started {profile_name} (PID {proc.pid})")
        return True
    except Exception as e:
        print(f"  FAILED {profile_name}: {e}")
        return False

def activate_team(team_name):
    if team_name not in TEAMS:
        print(f"Unknown team '{team_name}'. Available: {', '.join(TEAMS.keys())}")
        return
    bots = TEAMS[team_name]
    print(f"Activating team '{team_name}' ({len(bots)} bots)...")
    for bot in bots:
        start_bot(bot)
        time.sleep(0.3)
    print(f"Team '{team_name}' activated.")

def deactivate_team(team_name):
    if team_name not in TEAMS:
        print(f"Unknown team '{team_name}'.")
        return
    bots = TEAMS[team_name]
    print(f"Deactivating team '{team_name}' ({len(bots)} bots)...")
    for bot in bots:
        kill_bot(bot)
    print(f"Team '{team_name}' deactivated.")

def list_status():
    all_profiles = sorted(os.listdir(profiles_dir))
    print(f"\n{'='*60}")
    print(f"CORE COUNCIL (Always On)")
    print(f"{'='*60}")
    for name in all_profiles:
        if name in CORE_COUNCIL:
            alive = False
            sf = os.path.join(profiles_dir, name, 'gateway_state.json')
            if os.path.exists(sf):
                try:
                    with open(sf) as f:
                        state = json.load(f)
                    pid = state.get('pid', 0)
                    alive = pid_alive(pid) if pid else False
                except:
                    pass
            print(f"  {'✅' if alive else '❌'} {name}")
    print(f"\n{'='*60}")
    print(f"STANDBY TEAMS")
    print(f"{'='*60}")
    for team, bots in TEAMS.items():
        if not bots:
            continue
        members = []
        for b in bots:
            alive = False
            sf = os.path.join(profiles_dir, b, 'gateway_state.json')
            if os.path.exists(sf):
                try:
                    with open(sf) as f:
                        state = json.load(f)
                    pid = state.get('pid', 0)
                    alive = pid_alive(pid) if pid else False
                except:
                    pass
            members.append(f"{'✅' if alive else '💤'} {b}")
        print(f"\n  {team} ({len(bots)} bots):")
        for m in members:
            print(f"    {m}")

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if action == 'deploy':
        all_profiles = sorted(os.listdir(profiles_dir))
        killed = sum(1 for name in all_profiles if kill_bot(name))
        print(f"Killed {killed} processes")
        time.sleep(2)
        print("\nStarting Core Council...")
        for name in CORE_COUNCIL:
            start_bot(name)
            time.sleep(0.5)
        print(f"\n✅ Core Council deployed: {len(CORE_COUNCIL)}/44 bots online")
    elif action == 'activate' and len(sys.argv) > 2:
        activate_team(sys.argv[2])
    elif action == 'deactivate' and len(sys.argv) > 2:
        deactivate_team(sys.argv[2])
    elif action == 'start' and len(sys.argv) > 2:
        start_bot(sys.argv[2])
    elif action == 'kill' and len(sys.argv) > 2:
        kill_bot(sys.argv[2])
    else:
        list_status()
