import threading
import queue
import tkinter as tk
from tkinter import ttk
from Simulation import Simulation
from constants import *

class BoidSimulationController:
    """
    Controller class for the simulation of a flock of boids.

    Description:
    The controller initializes a gui to manage the arguments and events of a simulation.
    When a simulation has started the controller can pause, update ir stop it.
    """

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Boid Simulation Configuration")
        self.root.geometry("300x670")
        self.simulation = None
        self.simulation_thread = None
        
        # Thread Events for control
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.update_event = threading.Event()
        
        # Queue for update parameters
        self.update_queue = queue.Queue()
        
        # Simulation save and duration variables
        self.save_var = tk.BooleanVar(value=False)
        self.duration_entry = None

        # Slider and parameter tracking variables
        self.params = {
            'num_boids': tk.IntVar(value=100),
            'boid_size': tk.IntVar(value=10),
            'separation_radius': tk.IntVar(value=10),
            'cohesion_radius': tk.IntVar(value=16),
            'alignment_radius': tk.IntVar(value=20),
            'max_speed': tk.IntVar(value=5),
            'max_force': tk.IntVar(value=1)
        }
        
    def _simulation_runner(self) -> None:
        """
        Starts and runs the simulation. Used in a Thread.
        """
        self.simulation.init_sim()
        self.simulation.run()
    
    def _start_simulation(self) -> None:
        """
        Retrieves arguments and launches a simulation in a thread.
        """
        if self.simulation_thread and self.simulation_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.pause_event.clear()
        self.update_event.clear()
        
        sim_params = {
            'num_boids': self.params['num_boids'].get(),
            'boid_size': self.params['boid_size'].get(),
            'separation_radius': self.params['separation_radius'].get(),
            'cohesion_radius': self.params['cohesion_radius'].get(),
            'alignment_radius': self.params['alignment_radius'].get(),
            'max_speed': self.params['max_speed'].get(),
            'max_force': self.params['max_force'].get()
        }
        
        num_frames = None
        if self.save_var.get():
            try:
                duration_seconds = int(self.duration_entry.get())
                num_frames = FPS * duration_seconds
            except (ValueError, TypeError):
                # Default to 60 seconds if invalid input
                num_frames = FPS * 60
        
        self.simulation = Simulation(
            self.pause_event, self.stop_event, self.update_event,
            sim_params['num_boids'], 
            num_frames,  # Use calculated frames or None 
            sim_params['boid_size'], 
            sim_params['separation_radius'], 
            sim_params['cohesion_radius'], 
            sim_params['alignment_radius'], 
            sim_params['max_speed'], 
            sim_params['max_force']
        )
        
        # Start simulation in a separate thread
        self.simulation_thread = threading.Thread(target=self._simulation_runner)
        self.simulation_thread.start()
            
    def _pause_simulation(self) -> None:
        """
        """
        if not self.pause_event.is_set():
            self.pause_event.set()
    
    def _resume_simulation(self) ->  None:
        """
        """
        if self.pause_event.is_set():
            self.pause_event.clear()
    
    def _toggle_pause(self) ->  None:
        """
        """
        if self.pause_event.is_set():
            self._resume_simulation()
        else:
            self._pause_simulation()
    
    def _stop_simulation(self) -> None:
        """
        """
        self.stop_event.set()
        self.pause_event.clear()
        if self.simulation_thread:
            self.simulation_thread.join()
        self.simulation = None
        self.simulation_thread = None
    
    def _update_params(self) -> None:
        """
        Updates the parameters for the Simulation and all the Boids.
        """
        self.update_event.set()
        
        sim_params = [
            self.params['num_boids'].get(),
            self.params['boid_size'].get(),
            self.params['separation_radius'].get(),
            self.params['cohesion_radius'].get(),
            self.params['alignment_radius'].get(),
            self.params['max_speed'].get(),
            self.params['max_force'].get()
        ]
        self.simulation._update_args(*sim_params)
        for boid in self.simulation.boids:
            boid._update_args(*sim_params[1:])
        # for key, value in sim_params.items():
        #     if hasattr(self.simulation, key):
        #         if key in ['separation_radius', 'cohesion_radius', 'alignment_radius']:
        #             setattr(self.simulation, key, self.simulation.boid_size * value)
        #         else:
        #             setattr(self.simulation, key, value)
        #     for boid in self.simulation.boids:
        #         if hasattr(self.simulation, key):
        #             if key in ['separation_radius', 'cohesion_radius', 'alignment_radius']:
        #                 setattr(boid, key, self.simulation.boid_size * self.simulation.boid_size * value)
        #             else:
        #                 setattr(boid, key, value)

    def _create_slider(self, label_text:str, var:any, from_:int|float, to:int|float, 
                       default:int|float, step:int|float = 1) -> None:
        """
        Create a slider with customizable step value
        
        Args:
            label_text (str): Text for the slider label
            var (tk.IntVar): Variable to track slider value
            from_ (int): Minimum slider value
            to (int): Maximum slider value
            default (int): Default slider value
            step (int, optional): Step increment for slider. Defaults to 1.
        """
        label = ttk.Label(self.root, text=f"{label_text}:")
        label.pack(pady=5)
        
        value_label = ttk.Label(self.root, textvariable=var)
        value_label.pack(pady=0)
        
        def update_slider_value(event):
            # Round to nearest step
            current_value = var.get()
            rounded_value = round(current_value / step) * step
            var.set(rounded_value)
        
        slider = ttk.Scale(
            self.root, 
            from_=from_, 
            to=to, 
            orient='horizontal', 
            length=250, 
            variable=var,
            command=update_slider_value
        )
        slider.set(default)
        slider.pack(pady=0)
        
    def _create_gui(self) -> None:       
        # Create sliders for each parameter
        self._create_slider(
            "Number of Boids", self.params['num_boids'], 
            from_=10, to=1000, default=100, step=10
        )
        
        self._create_slider(
            "Boid Size", self.params['boid_size'], 
            from_=1, to=30, default=10, step=1
        )
        
        self._create_slider(
            "Separation Radius", self.params['separation_radius'], 
            from_=5, to=25, default=10, step=5
        )
        
        self._create_slider(
            "Cohesion Radius", self.params['cohesion_radius'], 
            from_=8, to=64, default=16, step=4
        )
        
        self._create_slider(
            "Alignment Radius", self.params['alignment_radius'], 
            from_=10, to=50, default=20, step=5
        )
        
        self._create_slider(
            "Max Speed", self.params['max_speed'], 
            from_=1, to=10, default=5, step=1
        )
        
        self._create_slider(
            "Max Force", self.params['max_force'], 
            from_=1, to=5, default=1, step=1
        )
        
        # Sim controls
        save_check = ttk.Checkbutton(
            self.root, 
            text="Save Simulation", 
            variable=self.save_var, 
            command=self._toggle_duration_state
        )
        save_check.pack(pady=5)
        
        duration_frame = ttk.Frame(self.root)
        duration_frame.pack(pady=5)
        duration_label = ttk.Label(duration_frame, text="Duration (seconds):")
        duration_label.pack(side=tk.LEFT)
        
        self.duration_entry = ttk.Entry(duration_frame, width=10)
        self.duration_entry.insert(0, "60")  # Default value
        self.duration_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        self._toggle_duration_state()
                
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10)
        
        run_button = ttk.Button(control_frame, text="Start", command=self._start_simulation)
        run_button.pack(side=tk.LEFT, padx=5)
        
        pause_button = ttk.Button(control_frame, text="Pause/Resume", command=self._toggle_pause)
        pause_button.pack(side=tk.LEFT, padx=5)
        
        control_frame_down = ttk.Frame(self.root)
        control_frame_down.pack(pady=2)

        stop_button = ttk.Button(control_frame_down, text="Stop", command=self._stop_simulation)
        stop_button.pack(side=tk.LEFT, padx=5)
        
        stop_button = ttk.Button(control_frame_down, text="Update", command=self._update_params)
        stop_button.pack(side=tk.LEFT, padx=5)
        
        self.root.mainloop()
    
    def _toggle_duration_state(self) -> None:
        """
        Toggle duration
        """
        state = "normal" if self.save_var.get() else "disabled"
        self.duration_entry.config(state=state)

    def run(self) -> None:
        self._create_gui()
