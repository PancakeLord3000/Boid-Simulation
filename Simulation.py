import math
import os
import shutil
import subprocess
import random
import time
import hashlib
import pygame
from pygame.event import Event as PygameEvent
from pygame.locals import DOUBLEBUF, OPENGL, QUIT, MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION
from OpenGL.GL import glPushMatrix, glRotatef, glColor3f, glBegin, glEnd, glPopMatrix, glEnable, glMatrixMode, glLoadIdentity, glLineWidth, glVertex3fv, glClearColor, glClear, glReadPixels
from OpenGL.GL import GL_DEPTH_TEST, GL_PROJECTION, GL_MODELVIEW, GL_LINES, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_RGB, GL_UNSIGNED_BYTE
from OpenGL.GLU import gluPerspective, gluLookAt
from threading import Event

from Boid import Boid
from constants import *


class Simulation:
    """
    Class representing the simulation of a flock of boids.

    Description:
    The Simulation class manages the initialization, running, and rendering of the boid simulation.
    It handles the creation of boids, the simulation loop, and the saving of frames as PNG images
    and as a video file.

    Arguments:
    pause_event, stop_event, update_event (threading.Event): Events controlled by the simulation controller.
    num_boids (int): The number of boids to create in the simulation.
    num_frames (int): The number of frames to simulate.
    boid_size, separation_radius, cohesion_radius, 
    alignment_radius, max_speed, max_force (int): Boid parameters.
    file_name (str): File name for the .mp4 if the class saves a file.
    """

    def __init__(self, pause_event:Event = None, stop_event:Event = None, update_event:Event = None, 
                 num_boids:int = 100, num_frames:int = None, boid_size:int = 10, separation_radius:int = 2, 
                 cohesion_radius:int = 7, alignment_radius:int = 5, max_speed:int = 5, max_force:int = 1, file_name:str = None) -> None:
        self.pause_event = pause_event
        self.stop_event = stop_event
        self.update_event = update_event

        self.boid_size = boid_size
        self.separation_radius = separation_radius
        self.cohesion_radius = cohesion_radius
        self.alignment_radius = alignment_radius

        self.max_speed = max_speed
        self.max_force = max_force

        self.num_boids = num_boids
        self.boids = []

        if num_frames:
            self.num_frames = num_frames
            if not file_name: self.file_name = f"Boid_Simulation_{self.num_boids}b_{int(self.num_frames/FPS)}s.mp4"
            else: self.file_name = file_name
        else: self.num_frames = None

        self.camera_angle_x = 0
        self.camera_angle_y = 0
        self.camera_distance = CAMERA_DISTANCE
        self.panning = False
        self.camera_pan_x = 0
        self.camera_pan_y = 0  
        self.dragging = False
        self.last_mouse_pos = None

        self.group_colors = {}

    def __str__(self) -> str:
        frames = ""
        if self.num_frames: frames = f"saving {self.file_name}, {self.num_frames/30}s"
        return f"Boid Simulation: boids={self.num_boids}, {frames}\n{self.boids[0]}"

    def _update_args(self, num_boids:int, boid_size:int = 10, separation_radius:int = 2, 
                 cohesion_radius:int = 7, alignment_radius:int = 5, max_speed:int = 5, max_force:int = 1) -> None:
        self.num_boids = num_boids
        self.boid_size = boid_size
        self.separation_radius = self.boid_size*separation_radius/2
        self.cohesion_radius = self.boid_size*cohesion_radius
        self.alignment_radius = self.boid_size*alignment_radius
        self.max_speed = max_speed
        self.max_force = max_force

    def init_sim(self) -> None:
        """
        Initializes the simulation window and boids.
        """
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Boids Simulation")

        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        gluPerspective(90, WINDOW_WIDTH / WINDOW_HEIGHT, 0.1, 2000.0)
        glMatrixMode(GL_MODELVIEW)

        self._init_boids()
        self.last_camera_move_time = time.time()

    def _init_boids(self) -> None:
        """
        Populates the simulation with boids.
        """
        self.boids = []
        for _ in range(self.num_boids):
            x = random.uniform(-CUBE_SIZE/2, CUBE_SIZE/2)
            y = random.uniform(-CUBE_SIZE/2, CUBE_SIZE/2)
            z = random.uniform(-CUBE_SIZE/2, CUBE_SIZE/2)
            boid = Boid(x, y, z, self.boid_size, self.separation_radius, 
                 self.cohesion_radius, self.alignment_radius, self.max_speed, self.max_force)
            self.boids.append(boid)

    def _pre_simulation_interaction(self) -> bool:
        """
        Renders the initial position of the cube and exits after 4s.
        """
        clock = pygame.time.Clock()
            
        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    return False
                self._handle_camera_controls(event)

            self._update_camera()
            
            glClearColor(*(1.0,1.0,1.0), 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            self._draw_cube((0.0, 0.0, 0.0))
            
            pygame.display.flip()
            clock.tick(FPS)

            if time.time() - self.last_camera_move_time > 4:
                return True
            time.sleep(0.1)

    def _modify_simulation_parameters(self, **kwargs) -> None:
        """
        not necessary i think
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key in ['separation_radius', 'cohesion_radius', 'alignment_radius']:
                    setattr(self, key, self.boid_size * value)
                else:
                    setattr(self, key, value)
            for boid in self.boids:
                if hasattr(boid, key):
                    setattr(boid, key, value)
    
    def _add_boids(self, num_new_boids: int) -> None:
        """
        Adds randomly positioned new boids
        """
        for _ in range(num_new_boids):
            x = random.uniform(-CUBE_SIZE/2, CUBE_SIZE/2)
            y = random.uniform(-CUBE_SIZE/2, CUBE_SIZE/2)
            z = random.uniform(-CUBE_SIZE/2, CUBE_SIZE/2)
            boid = Boid(x, y, z, self.boid_size, self.separation_radius, 
                        self.cohesion_radius, self.alignment_radius, 
                        self.max_speed, self.max_force)
            self.boids.append(boid)
        self.num_boids = len(self.boids)
    
    def _remove_random_boids(self, num_boids_to_remove: int) -> None:
        """
        Removes random boids from the simulation
        """
        for _ in range(num_boids_to_remove):
            if self.boids:
                boid_to_remove = random.choice(self.boids)
                # this is enough because the sim clears all the boids every frame to re-render them the next
                self.boids.remove(boid_to_remove)
        self.num_boids = len(self.boids)

    def _save(self) -> None:
        """
        Create a video file from the saved frames using ffmpeg.
        """
        input_pattern = "frames/frame_%04d.png"
        output_video = self.file_name
        frames_dir = './frames'
        print(output_video)
        fps = FPS

        # Run ffmpeg command
        ffmpeg_command = [
            "ffmpeg",
            "-framerate", str(fps),
            "-y",   # overwrite swithout asking (careful)
            "-i", input_pattern,
            "-vf", "vflip",     # since pygame.image.frombuffer stores the image flipped we have to use the image flipped to make the video
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_video
        ]

        subprocess.run(ffmpeg_command)
        print(f"Video '{output_video}' created successfully.")

    def _draw_cube(self, color:tuple[float, float, float] = (0.5, 0.5, 0.5), width:float = 3.0) -> None:
        """
        Draws the observation cube.
        """
        glPushMatrix()
        glRotatef(0, 1, 1, 1)
        
        glLineWidth(width)
        glBegin(GL_LINES)
        glColor3f(*color)

        # Define the vertices of the cube
        vertices = [
            (-CUBE_SIZE/2, -CUBE_SIZE/2, -CUBE_SIZE/2),
            (CUBE_SIZE/2, -CUBE_SIZE/2, -CUBE_SIZE/2),
            (CUBE_SIZE/2, CUBE_SIZE/2, -CUBE_SIZE/2),
            (-CUBE_SIZE/2, CUBE_SIZE/2, -CUBE_SIZE/2),
            (-CUBE_SIZE/2, -CUBE_SIZE/2, CUBE_SIZE/2),
            (CUBE_SIZE/2, -CUBE_SIZE/2, CUBE_SIZE/2),
            (CUBE_SIZE/2, CUBE_SIZE/2, CUBE_SIZE/2),
            (-CUBE_SIZE/2, CUBE_SIZE/2, CUBE_SIZE/2)
        ]

        # Define the edges of the cube
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom face
            (4, 5), (5, 6), (6, 7), (7, 4),  # Top face
            (0, 4), (1, 5), (2, 6), (3, 7)   # Connecting edges
        ]

        # Draw the edges
        for edge in edges:
            for vertex in edge:
                glVertex3fv(vertices[vertex])

        glEnd()
        glPopMatrix()

    def _handle_camera_controls(self, event:PygameEvent) -> None:
        """
        Camera controls.
        """
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                self.dragging = True
                self.last_mouse_pos = pygame.mouse.get_pos()
            elif event.button == 3:  # Right mouse button
                self.panning = True
                self.last_mouse_pos = pygame.mouse.get_pos()
            elif event.button == 4:  # Scroll up
                self.camera_distance -= ZOOM_SPEED
            elif event.button == 5:  # Scroll down
                self.camera_distance += ZOOM_SPEED
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:  # Left mouse button
                self.dragging = False
            elif event.button == 3:  # Right mouse button
                self.panning = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mouse_pos = pygame.mouse.get_pos()
                dx = mouse_pos[0] - self.last_mouse_pos[0]
                dy = mouse_pos[1] - self.last_mouse_pos[1]
                self.camera_angle_x += dy * CAMERA_SPEED
                self.camera_angle_y += dx * CAMERA_SPEED
                
                # Limit the camera_angle_x to avoid gimbal lock
                self.camera_angle_x = max(-89.9, min(89.9, self.camera_angle_x))
                
                self.last_mouse_pos = mouse_pos
            elif self.panning:
                mouse_pos = pygame.mouse.get_pos()
                dx = mouse_pos[0] - self.last_mouse_pos[0]
                dy = mouse_pos[1] - self.last_mouse_pos[1]
                self.camera_pan_x += dx * PAN_SPEED
                self.camera_pan_y -= dy * PAN_SPEED
                self.last_mouse_pos = mouse_pos

    def _update_camera(self) -> None:
        """"
        """
        glLoadIdentity()
        
        # Convert angles to radians
        angle_x_rad = math.radians(self.camera_angle_x)
        angle_y_rad = math.radians(self.camera_angle_y)
        
        # Calculate the camera position
        camera_x = self.camera_distance * math.sin(angle_y_rad) * math.cos(angle_x_rad)
        camera_y = self.camera_distance * math.cos(angle_y_rad) * math.cos(angle_x_rad)
        camera_z = self.camera_distance * math.sin(angle_x_rad)
        
        # Calculate the right and up vectors
        right_x = math.cos(angle_y_rad)
        right_y = -math.sin(angle_y_rad)
        up_x = -math.sin(angle_x_rad) * math.sin(angle_y_rad)
        up_y = -math.sin(angle_x_rad) * math.cos(angle_y_rad)
        up_z = -math.cos(angle_x_rad)
        
        # Apply panning
        camera_x += self.camera_pan_x * right_x + self.camera_pan_y * up_x
        camera_y += self.camera_pan_x * right_y + self.camera_pan_y * up_y
        camera_z += self.camera_pan_y * up_z
        
        # Calculate the look-at point
        look_x = camera_x - self.camera_distance * math.sin(angle_y_rad) * math.cos(angle_x_rad)
        look_y = camera_y - self.camera_distance * math.cos(angle_y_rad) * math.cos(angle_x_rad)
        look_z = camera_z - self.camera_distance * math.sin(angle_x_rad)
        
        gluLookAt(
            camera_x, camera_y, camera_z,
            look_x, look_y, look_z,
            0, 0, 1
        )
            
    def _get_group_color(self, group_id:int) -> tuple[float, float, float]:
        """
        Returns a color based on an integer.
        """
        if group_id not in self.group_colors:
            # Generate a unique color based on the group_id
            hash_object = hashlib.md5(str(group_id).encode())
            hash_hex = hash_object.hexdigest()
            r = int(hash_hex[:2], 16) / 318.75 + 0.15     # 0.15 < r < 0.95 that way its not black(default) or white(background)
            g = int(hash_hex[2:4], 16) / 318.75 + 0.15
            b = int(hash_hex[4:6], 16) / 318.75 + 0.15
            self.group_colors[group_id] = (r, g, b)
        return self.group_colors[group_id]
    
    def _get_boid_groups(self) -> list[list[Boid]]:
        """
        Defines the boid groups based on cohesion and distance.
        """
        initial_groups = []
        for boid in self.boids:
            group = set([boid])
            for other in self.boids:
                if boid != other and boid.position.distance_to(other.position) < self.boid_size+self.cohesion_radius*2:
                    group.add(other)
            if len(group) >= 2:  # At least 2 boids to form a group
                initial_groups.append(group)

        merged_groups = []
        while initial_groups:
            current_group = initial_groups.pop(0)
            i = 0
            while i < len(initial_groups):
                if current_group & initial_groups[i]:
                    current_group |= initial_groups.pop(i) # or so that we don't join the same boids from two groups
                else:
                    i += 1
            merged_groups.append(current_group)
        return merged_groups

    def _update_boid_colors(self) -> None:
        """
        Updates the boid colors based on groups.
        """
        merged_groups = self._get_boid_groups()
        for group_id, group in enumerate(merged_groups):
            group_color = self._get_group_color(group_id)
            for boid in group:
                boid.set_group(group_id)
                boid.change_color(group_color)


        ungrouped_boids = set(self.boids) - set().union(*merged_groups)
        for boid in ungrouped_boids:
            boid.set_group(None)
            boid.change_color(DEFAULT_BOID_COLOR)

    def _create_folder(self, folder_path:str) -> None:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{folder_path}' created successfully.")
        else:
            print(f"Folder '{folder_path}' already exists.")

    def _delete_folder(self, folder_path:str) -> int:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            print(f"Folder '{folder_path}' and its contents deleted successfully.")
            return 0
        else:
            print(f"Folder '{folder_path}' does not exist.")
            return -1

    def run(self) -> None:
        """
        Runs the boid simulation.
        """
        if not self._pre_simulation_interaction():
            return

        clock = pygame.time.Clock()
        if self.num_frames is not None:
            self._delete_folder("frames")
            self._create_folder("frames")
        
        # Main simulation loop
        frame = 0
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                self._handle_camera_controls(event)
            if self.stop_event.is_set():
                running = False
            if self.update_event.is_set():
                if self.num_boids > len(self.boids):self._add_boids(self.num_boids-len(self.boids))
                elif self.num_boids < len(self.boids):self._remove_random_boids(len(self.boids)-self.num_boids)
                self.update_event.clear()
                pass

            glClearColor(*LIGHT_GRAY, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            self._update_camera()
            self._draw_cube()
            self._update_boid_colors()
            
            if not self.pause_event.is_set():
                for boid in self.boids:
                    boid.flock(self.boids)
                    boid.update()

            for boid in self.boids:
                boid.render()
            pygame.display.flip()
            clock.tick(FPS)
            
            if self.num_frames is not None:
                data = glReadPixels(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, GL_RGB, GL_UNSIGNED_BYTE)
                image = pygame.image.frombuffer(data, (WINDOW_WIDTH, WINDOW_HEIGHT), "RGB")
                image = pygame.transform.flip(image, False, False)
                filename = f"frames/frame_{frame:04d}.png"
                pygame.image.save(image, filename)

                frame += 1
                if self.pause_event.is_set():
                    self.num_frames += 1
                if frame >= self.num_frames:
                    running = False

        if self.num_frames: self._save()
        pygame.quit()
        self.stop_event.clear()
        self.pause_event.clear()
        self.update_event.clear()

