import math
import random
import pygame
from OpenGL.GL import glPushMatrix, glTranslatef, glRotatef, glColor3f, glBegin, glVertex3f, glEnd, glPopMatrix
from OpenGL.GL import GL_TRIANGLES

from constants import *


class Boid:
    """
    Class representing a single boid (bird-like object).

    Description:
    The Boid class defines the properties and behavior of individual boids.
    The key arguments are the position, velocity and acceleration which are
    used in the function flock to simulate a boid.

    Arguments:
    x, y, z (float): Initial random position coordinates of the boid.
    boid_size, separation_radius, cohesion_radius, 
    alignment_radius, max_speed, max_force (int): Boid parameters.
    """

    def __init__(self, x, y, z, boid_size = 10, separation_radius = 2, 
                 cohesion_radius = 7, alignment_radius = 5, max_speed = 5, max_force = 1):
        self.boid_size = boid_size
        self.separation_radius = boid_size*separation_radius/2
        self.cohesion_radius =  boid_size*cohesion_radius
        self.alignment_radius = boid_size*alignment_radius
        self.max_speed = max_speed
        self.max_force = max_force
        self.position = pygame.math.Vector3(x, y, z)
        self.velocity = pygame.math.Vector3(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        self.velocity.scale_to_length(self.max_speed/3)
        self.acceleration = pygame.math.Vector3()
        self.color = DEFAULT_BOID_COLOR
        self.group = None  

    def __str__(self):
        return f"Boid:({self.position})({self.velocity})({self.acceleration}), size={self.boid_size}, separation={self.separation_radius*2}, cohesion={self.cohesion_radius}, alignment={self.alignment_radius}, max speed={self.max_speed}, max force={self.max_force}"
    
    def _update_args(self, boid_size, separation_radius, cohesion_radius, alignment_radius, max_speed, max_force):
        self.boid_size = boid_size
        self.separation_radius = self.boid_size*separation_radius/2
        self.cohesion_radius =  self.boid_size*cohesion_radius
        self.alignment_radius = self.boid_size*alignment_radius
        self.max_speed = max_speed
        self.max_force = max_force


    def flock(self, boids):
        """
        Updates the boid's direction and speed (acceleration vector) according to other boid's position
        relative to itself.
        Occasionally updates a random force.
        """
        separation_force = self._separate(boids)
        alignment_force = self._align(boids)
        cohesion_force = self._cohesion(boids)
        cube_force = self._stay_in_cube()
        center_alignment_force = self._align_to_center()

        if random.random() < 0.1:
            random_direction = pygame.math.Vector3(
            random.uniform(-1, 1),
            random.uniform(-1, 1),
            random.uniform(-1, 1)
            ).normalize()
            random_force = random_direction * self.max_force * 4
            self._apply_force(random_force)
        else:
            self._apply_force(separation_force*2)  # separates
            self._apply_force(alignment_force*0.2)   # aligns towards avrg direction
            self._apply_force(cohesion_force)    # aligns towards center of flock
            self._apply_force(cube_force)
            # self._apply_force(center_alignment_force*0.1)    # this is not necessary but its nice to have the flock near the default center of the camera
  
    def update(self):
        """
        Update the boid's position and velocity based on its acceleration vector.
        """
        self.velocity += self.acceleration
        self.velocity.scale_to_length(self.max_speed)
        self.position += self.velocity
        self.acceleration *= 0

    def render(self):
        """
        Renders the boid as a 3D pyramid.
        """
        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)

        # Rotate the pyramid to point in the direction of velocity
        velocity_direction = self.velocity.normalize()
        up_vector = pygame.math.Vector3(0, 0, 1)
        rotation_axis = up_vector.cross(velocity_direction)
        rotation_angle = math.degrees(math.acos(velocity_direction.dot(up_vector)))
        glRotatef(rotation_angle, rotation_axis.x, rotation_axis.y, rotation_axis.z)

        glColor3f(*self.color)  
        glBegin(GL_TRIANGLES)

        # Draw the pyramid
        pyramid_height = self.boid_size * 3/5
        pyramid_base_radius = self.boid_size * 2/5

        # Base square vertices
        base_vertices = [
            pygame.math.Vector3(-pyramid_base_radius, -pyramid_base_radius, 0),
            pygame.math.Vector3(pyramid_base_radius, -pyramid_base_radius, 0),
            pygame.math.Vector3(pyramid_base_radius, pyramid_base_radius, 0),
            pygame.math.Vector3(-pyramid_base_radius, pyramid_base_radius, 0)
        ]

        # Apex vertex
        apex_vertex = pygame.math.Vector3(0, 0, pyramid_height)

        # Draw the triangular faces
        for i in range(4):
            glVertex3f(*base_vertices[i])
            glVertex3f(*base_vertices[(i + 1) % 4])
            glVertex3f(*apex_vertex)

        # Draw the base square
        glVertex3f(*base_vertices[0])
        glVertex3f(*base_vertices[1])
        glVertex3f(*base_vertices[2])
        glVertex3f(*base_vertices[3])

        glEnd()
        glPopMatrix()

    def _apply_force(self, force):
        """
        Apply a force to the boid's acceleration vector, essentially changing the speed and direction
        of the boid.
        """
        self.acceleration += force

    def _separate(self, boids):
        """
        Computes a force that steers the boid away from its neighbors.

        Arguments:
        boids (list): A list of all the boids in the simulation.

        Returns:
        pygame.math.Vector3: The separation force vector.
        """
        separation_force = pygame.math.Vector3()
        total = 0

        for boid in boids:
            if boid != self:
                distance = self.position.distance_to(boid.position)
                if distance == 0 : distance = 0.001
                if distance < self.separation_radius :
                    diff = self.position - boid.position
                    if diff.length() > 0:
                        diff.scale_to_length(1 / distance)
                        separation_force += diff
                    total += 1

        if total > 0:
            separation_force  /= total
            if separation_force.length() > 0:  
                separation_force.scale_to_length(self.max_speed)
                separation_force -= self.velocity
                separation_force.scale_to_length(self.max_force)

        return separation_force

    def _align(self, boids):
        """
        Computes a force that steers the boid towards the average direction of its neighbors.

        Arguments:
        boids (list): A list of all the boids in the simulation.

        Returns:
        pygame.math.Vector3: The alignment force vector.
        """
        alignment_force = pygame.math.Vector3()
        total = 0

        for boid in boids:
            if boid != self:
                distance = self.position.distance_to(boid.position)
                if distance < self.alignment_radius:
                    alignment_force += boid.velocity
                    total += 1

        if total > 0:
            alignment_force /= total    # average position of cluster
            if alignment_force.length() > 0:
                alignment_force.scale_to_length(self.max_speed)
                alignment_force -= self.velocity
                alignment_force.scale_to_length(self.max_force)

        return alignment_force

    def _cohesion(self, boids):
        """
        Computes a force that steers the boid towards the average position of its neighbors.

        Arguments:
        boids (list): A list of all the boids in the simulation.

        Returns:
        pygame.math.Vector3: The cohesion force vector.
        """
        cohesion_force = pygame.math.Vector3()
        total = 0

        for boid in boids:
            if boid != self:
                distance = self.position.distance_to(boid.position)
                if distance < self.cohesion_radius:
                    cohesion_force += boid.position - self.position
                    total += 1

        if total > 0:
            cohesion_force  /= total
            if cohesion_force.length() > 0:  
                cohesion_force.scale_to_length(self.max_speed)
                cohesion_force -= self.velocity
                cohesion_force.scale_to_length(self.max_force)
        return cohesion_force
    
    def _align_to_center(self):
        """
        Not necessary to the simulation
        Create an orbiting motion around the center point (0,0,0) at a fixed radius.
        """
        center = pygame.math.Vector3(0, 0, 0)
        distance_to_center = center - self.position
        current_distance = distance_to_center.length()
        if current_distance>0:
            # Pull towards center at a perpendicular angle
            if random.random() < 0.5: perpendicular_direction = distance_to_center.cross(pygame.math.Vector3(0, 0, 1))
            else : perpendicular_direction = distance_to_center.cross(pygame.math.Vector3(0, 0, -1))

            perpendicular_direction.normalize_ip()
            
            # Normalized direction towards center
            center_direction = distance_to_center.copy()
            center_direction.normalize_ip()
            
            # Combine perpendicular and center-seeking forces
            perpendicular_force = perpendicular_direction * (self.max_force  * 0.5)
            center_force = center_direction * (self.max_force * 0.5)
            
            # Combine the two forces
            total_force = perpendicular_force + center_force
            
            # Ensure we don't exceed 2.5 max force
            if total_force.length() > self.max_force:
                total_force.scale_to_length(self.max_force)
            
            # print(f"for {current_distance} : {0.2*(1.5*(current_distance-125)/(250-125)*(current_distance-1)/(250-1) + (current_distance-250)/(125-250)*(current_distance-1)/(125-1))}")
            total_force.scale_to_length(self.max_force*(1.5*(current_distance-125)/(250-125)*(current_distance-1)/(250-1) + (current_distance-250)/(125-250)*(current_distance-1)/(125-1)))
            return total_force

        return pygame.math.Vector3()
          
    def change_color(self, color=DEFAULT_BOID_COLOR):
        """
        Changes the color of the boid.
        """
        self.color = color

    def set_group(self, group):
        """
        Gives the boid a group, defined by the simulation.
        """
        self.group = group
        
    def _stay_in_cube(self):
        """
        Computes a force that steers the boid away from the edges of the observation cube.
        """
        border_force = pygame.math.Vector3()
        border_radius = self.boid_size*2
        max_force = self.max_force * 5   # you can reduce this force if you want to let some boids escape the cube

        # Check for proximity to the cube boundaries
        if self.position.x < -CUBE_SIZE/2 + border_radius:
            border_force.x = max_force
        elif self.position.x > CUBE_SIZE/2 - border_radius:
            border_force.x = -max_force

        if self.position.y < -CUBE_SIZE/2 + border_radius:
            border_force.y = max_force
        elif self.position.y > CUBE_SIZE/2 - border_radius:
            border_force.y = -max_force

        if self.position.z < -CUBE_SIZE/2 + border_radius:
            border_force.z = max_force
        elif self.position.z > CUBE_SIZE/2 - border_radius:
            border_force.z = -max_force

        return border_force
