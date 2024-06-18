import pygame

from pygame.locals import *

from OpenGL import GL
from OpenGL import GLU

verticies = (
   (1, -1, -1),
   (1, 1, -1),
   (-1, 1, -1),
   (-1, -1, -1),
   (1, -1, 1),
   (1, 1, 1),
   (-1, -1, 1),
   (-1, 1, 1)
)
edges = (
   (0,1),
   (0,3),
   (0,4),
   (2,1),
   (2,3),
   (2,7),
   (6,3),
   (6,4),
   (6,7),
   (5,1),
   (5,4),
   (5,7)
)
def Cube():
   GL.glBegin(GL.GL_LINES)
   for edge in edges:
      for vertex in edge:
         GL.glVertex3fv(verticies[vertex])
   GL.glEnd()

def main():
   pygame.init()
   display = (800,600)
   pygame.display.set_mode(display, pygame.DOUBLEBUF|pygame.OPENGL)

   GLU.gluPerspective(45, (display[0]/display[1]), 0.1, 50.0)

   GL.glTranslatef(0.0,0.0, -5)

   while True:
      for event in pygame.event.get():
         if event.type == pygame.QUIT:
            pygame.quit()
            quit()
      GL.glRotatef(1, 3, 1, 1)
      GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
      Cube()
      pygame.display.flip()
      pygame.time.wait(10)

main()