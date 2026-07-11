import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import os

# ── Formula E Car Parameters ──
MASS = 900          # kg (including driver)
MAX_REGEN_POWER = 350  # kW (Gen3 max regen)
BATTERY_CAPACITY = 52  # kWh
EFFICIENCY = 0.85   # Drivetrain efficiency

# ── Monaco Street Circuit Corner Data ──
# Simplified corner sequence with entry/exit speeds
corners = [
    {'name': 'Sainte Devote',  'entry': 230, 'exit': 80,  'length': 180},
    {'name': 'Massenet',       'entry': 180, 'exit': 110, 'length': 150},
    {'name': 'Casino',         'entry': 160, 'exit': 95,  'length': 120},
    {'name': 'Mirabeau',       'entry': 150, 'exit': 65,  'length': 100},
    {'name': 'Grand Hotel',    'entry': 130, 'exit': 45,  'length': 90},
    {'name': 'Portier',        'entry': 140, 'exit': 75,  'length': 110},
    {'name': 'Nouvelle Chic.', 'entry': 165, 'exit': 55,  'length': 130},
    {'name': 'Tabac',          'entry': 175, 'exit': 105, 'length': 140},
    {'name': 'Piscine 1',      'entry': 155, 'exit': 80,  'length': 115},
    {'name': 'Piscine 2',      'entry': 145, 'exit': 85,  'length': 105},
    {'name': 'La Rascasse',    'entry': 120, 'exit': 50,  'length': 95},
    {'name': 'Anthony Noghes', 'entry': 135, 'exit': 70,  'length': 100},
]

# ── Regen Settings (0-100%) ──
regen_settings = [25, 50, 75, 100]
setting_colors = ['#0067FF', '#00AA44', '#FFF200', '#FF3333']

# ── Calculate energy recovery per corner per setting ──
results = []

for corner in corners:
    v_entry = corner['entry'] / 3.6  # Convert to m/s
    v_exit = corner['exit'] / 3.6

    # Kinetic energy available for recovery
    ke_available = 0.5 * MASS * (v_entry**2 - v_exit**2) / 1000  # kJ

    if ke_available <= 0:
        ke_available = 0

    corner_results = {'Corner': corner['name']}

    for setting in regen_settings:
        # Regen efficiency scales with setting
        regen_efficiency = EFFICIENCY * (setting / 100)

        # Power limited recovery
        braking_distance = corner['length']
        braking_time = braking_distance / ((v_entry + v_exit) / 2)

        # Max recoverable energy (power limited)
        max_power_recovery = MAX_REGEN_POWER * braking_time / 1000  # kJ

        # Actual recovery
        recovery = min(ke_available * regen_efficiency,
                      max_power_recovery * (setting / 100))
        recovery_kwh = recovery / 3600  # Convert kJ to kWh

        corner_results[f'Regen_{setting}'] = recovery_kwh * 1000  # Wh

    results.append(corner_results)

df = pd.DataFrame(results)

# ── Lap totals ──
lap_totals = {}
for setting in regen_settings:
    lap_totals[setting] = df[f'Regen_{setting}'].sum() / 1000  # kWh per lap

# ── Lap time penalty (higher regen = more braking drag = slightly slower) ──
base_lap_time = 75.0  # seconds (Monaco qualifying)
lap_time_penalty = {
    25: 0.0,    # No penalty
    50: 0.15,   # 0.15s slower
    75: 0.35,   # 0.35s slower
    100: 0.65   # 0.65s slower
}

lap_times = {s: base_lap_time + lap_time_penalty[s] for s in regen_settings}

# ── Race simulation (78 laps Monaco) ──
RACE_LAPS = 78
race_energy_recovered = {s: lap_totals[s] * RACE_LAPS for s in regen_settings}
race_soc_boost = {s: (race_energy_recovered[s] / BATTERY_CAPACITY) * 100
                  for s in regen_settings}
race_time_cost = {s: lap_time_penalty[s] * RACE_LAPS for s in regen_settings}

# ── Plotting ──
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('Formula E Regenerative Braking Simulator\nMonaco Street Circuit',
             fontsize=14, fontweight='bold')

# --- Plot 1: Energy recovery per corner ---
ax1 = axes[0, 0]
x = np.arange(len(corners))
width = 0.2

for i, (setting, color) in enumerate(zip(regen_settings, setting_colors)):
    values = df[f'Regen_{setting}'].values
    ax1.bar(x + i * width, values, width,
            label=f'{setting}% Regen',
            color=color, edgecolor='none', alpha=0.85)

ax1.set_xticks(x + width * 1.5)
ax1.set_xticklabels([c['name'][:8] for c in corners],
                     rotation=45, ha='right', fontsize=8)
ax1.set_ylabel('Energy Recovered (Wh)', fontsize=10)
ax1.set_title('Energy Recovery Per Corner\nby Regen Setting', fontsize=11)
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3, axis='y')

# --- Plot 2: Total energy per lap ---
ax2 = axes[0, 1]
colors_bar = setting_colors
bars = ax2.bar([f'{s}%' for s in regen_settings],
               [lap_totals[s] * 1000 for s in regen_settings],
               color=colors_bar, edgecolor='none', alpha=0.85)
ax2.set_xlabel('Regen Setting', fontsize=10)
ax2.set_ylabel('Energy Recovered (Wh/lap)', fontsize=10)
ax2.set_title('Total Energy Recovery Per Lap\nby Regen Setting', fontsize=11)
ax2.grid(True, alpha=0.3, axis='y')
for bar, setting in zip(bars, regen_settings):
    ax2.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 5,
             f'{lap_totals[setting]*1000:.0f} Wh',
             ha='center', fontsize=10, color='white')

# --- Plot 3: Lap time vs energy trade-off ---
ax3 = axes[0, 2]
energy_values = [lap_totals[s] * 1000 for s in regen_settings]
time_values = [lap_times[s] for s in regen_settings]

ax3.plot(energy_values, time_values, 'o-',
         color='#00D2BE', linewidth=2.5, markersize=10)

for i, setting in enumerate(regen_settings):
    ax3.annotate(f'{setting}% Regen',
                 (energy_values[i], time_values[i]),
                 textcoords='offset points',
                 xytext=(10, 5), fontsize=9, color='white')

ax3.set_xlabel('Energy Recovered per Lap (Wh)', fontsize=10)
ax3.set_ylabel('Lap Time (seconds)', fontsize=10)
ax3.set_title('Lap Time vs Energy Recovery Trade-off\n(Optimisation Curve)', fontsize=11)
ax3.grid(True, alpha=0.3)

# --- Plot 4: Race energy recovered ---
ax4 = axes[1, 0]
bars4 = ax4.bar([f'{s}%' for s in regen_settings],
                [race_energy_recovered[s] for s in regen_settings],
                color=colors_bar, edgecolor='none', alpha=0.85)
ax4.set_xlabel('Regen Setting', fontsize=10)
ax4.set_ylabel('Total Energy Recovered (kWh)', fontsize=10)
ax4.set_title('Total Race Energy Recovery\n(78 laps)', fontsize=11)
ax4.grid(True, alpha=0.3, axis='y')
for bar, setting in zip(bars4, regen_settings):
    ax4.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.1,
             f'{race_energy_recovered[setting]:.1f} kWh',
             ha='center', fontsize=10, color='white')

# --- Plot 5: SoC boost from regen ---
ax5 = axes[1, 1]
bars5 = ax5.bar([f'{s}%' for s in regen_settings],
                [race_soc_boost[s] for s in regen_settings],
                color=colors_bar, edgecolor='none', alpha=0.85)
ax5.set_xlabel('Regen Setting', fontsize=10)
ax5.set_ylabel('SoC Boost (%)', fontsize=10)
ax5.set_title('Battery SoC Boost from Regeneration\nOver Full Race Distance', fontsize=11)
ax5.grid(True, alpha=0.3, axis='y')
for bar, setting in zip(bars5, regen_settings):
    ax5.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.2,
             f'+{race_soc_boost[setting]:.1f}%',
             ha='center', fontsize=10, color='white')

# --- Plot 6: Optimal strategy recommendation ---
ax6 = axes[1, 2]
# Score = energy recovered - time cost normalised
energy_norm = np.array([race_energy_recovered[s] for s in regen_settings])
time_norm = np.array([race_time_cost[s] for s in regen_settings])
energy_score = (energy_norm - energy_norm.min()) / (energy_norm.max() - energy_norm.min())
time_score = 1 - (time_norm - time_norm.min()) / (time_norm.max() - time_norm.min())
overall_score = (energy_score * 0.6 + time_score * 0.4) * 100

bars6 = ax6.bar([f'{s}%' for s in regen_settings],
                overall_score,
                color=colors_bar, edgecolor='none', alpha=0.85)
ax6.set_xlabel('Regen Setting', fontsize=10)
ax6.set_ylabel('Strategy Score (0-100)', fontsize=10)
ax6.set_title('Optimal Regen Strategy Score\n(60% Energy + 40% Lap Time)',
              fontsize=11)
ax6.grid(True, alpha=0.3, axis='y')
for bar, score in zip(bars6, overall_score):
    ax6.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 1,
             f'{score:.0f}',
             ha='center', fontsize=10, color='white',
             fontweight='bold')

plt.tight_layout()
plt.savefig('regen_braking.png', dpi=150, bbox_inches='tight')
plt.show()

# Print summary
print("\n=== REGENERATIVE BRAKING STRATEGY REPORT ===")
print(f"Circuit: Monaco Street Circuit ({len(corners)} corners)")
print(f"Race Distance: {RACE_LAPS} laps")
print(f"\nPer Lap Analysis:")
for setting in regen_settings:
    print(f"  {setting}% Regen: {lap_totals[setting]*1000:.0f} Wh recovered | "
          f"Lap time: {lap_times[setting]:.2f}s")
print(f"\nRace Summary:")
optimal = regen_settings[np.argmax(overall_score)]
print(f"Optimal regen setting: {optimal}%")
print(f"Total energy recovered at {optimal}%: "
      f"{race_energy_recovered[optimal]:.1f} kWh")
print(f"SoC boost from regen: +{race_soc_boost[optimal]:.1f}%")
