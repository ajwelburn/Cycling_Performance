# Import necessary libraries for widgets, math, and plotting
import math
import matplotlib.pyplot as plt
from ipywidgets import interactive, IntSlider, FloatSlider, fixed
from IPython.display import display

# Set a clean and professional plot style
plt.style.use('seaborn-v0_8-whitegrid')


def get_user_input():
    """
    Prompts the user to enter the session and athlete parameters.
    Uses a loop with error handling to ensure valid integer inputs.
    """
    print("Please enter the session and athlete parameters:")
    while True:
        try:
            reps = int(input("Number of repetitions (e.g., 5): "))
            duration = int(input("Work interval duration in seconds (e.g., 40): "))
            recovery = int(input("Recovery interval duration in seconds (e.g., 80): "))
            work_power = int(input("Work interval power in watts (e.g., 400): "))
            recovery_power = int(input("Recovery interval power in watts (e.g., 259): "))
            CP = int(input("Critical Power (CP) in watts (e.g., 260): "))
            WP = int(input("W' (W prime) in joules (e.g., 28000): "))
            print("-" * 30) # Separator for clarity
            return reps, duration, recovery, work_power, recovery_power, CP, WP
        except ValueError:
            print("\nInvalid input. Please enter whole numbers only. Let's try again.\n")


def run_simulation_and_plot(A, B, reps, duration, recovery, work_power, recovery_power, CP, WP):
    """
    Simulates and plots the W' balance for an interval session.
    This function is called by the interactive widget whenever a slider is moved.
    """
    # --- 1. W' Balance Calculation ---
    Wexp = 0
    Wbal = WP
    time = [0]
    W_bal = [WP]
    current_time = 0

    for i in range(reps):
        # --- Work Interval ---
        for t in range(1, duration + 1):
            if work_power > CP:
                Wbal -= (work_power - CP)
            Wbal = max(0, Wbal) # Ensure W' doesn't go below zero
            current_time += 1
            time.append(current_time)
            W_bal.append(Wbal)

        # --- Recovery Interval ---
        Wexp = WP - Wbal
        for t in range(1, recovery + 1):
            if recovery_power < CP:
                DCP = CP - recovery_power
                # This calculation can fail if DCP is negative, which shouldn't happen here.
                # We add a small value to avoid math domain errors if DCP is zero.
                Tau = A * ((DCP + 1e-9) ** B)
                Wbal = WP - (Wexp * math.exp(-t / Tau))
            
            Wbal = min(WP, Wbal) # Ensure W' doesn't exceed its maximum
            current_time += 1
            time.append(current_time)
            W_bal.append(Wbal)
        
        Wexp = WP - Wbal

    # --- 2. Plotting the Results ---
    plt.figure(figsize=(12, 7))
    plt.plot(time, W_bal, label="W' Balance", color='#2980b9', linewidth=2)
    plt.xlabel('Time (s)', fontsize=12)
    plt.ylabel("W' Balance (J)", fontsize=12)
    plt.title("W' Balance During Interval Training", fontsize=16, weight='bold')
    plt.ylim(0, WP * 1.05)
    plt.xlim(0, current_time)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.legend()
    plt.show()


# --- Main Execution ---
# First, get the fixed parameters from the user
reps, duration, recovery, work_power, recovery_power, CP, WP = get_user_input()

# Then, create the interactive widget with sliders for A and B
interactive_plot = interactive(
    run_simulation_and_plot,
    A=IntSlider(min=0, max=10000, step=100, value=5184, description='A:', continuous_update=False),
    B=FloatSlider(min=-0.2, max=1.4, step=0.01, value=-0.60, description='B:', continuous_update=False),
    # Pass the user-inputted values as fixed arguments that don't change
    reps=fixed(reps),
    duration=fixed(duration),
    recovery=fixed(recovery),
    work_power=fixed(work_power),
    recovery_power=fixed(recovery_power),
    CP=fixed(CP),
    WP=fixed(WP)
)

# Display the interactive controls and the plot
print("Adjust the sliders for the recovery parameters A and B to update the plot.")
display(interactive_plot)
